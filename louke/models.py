"""Model alias commands."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

from ._common import git_root

SCHEMA = 'louke://models-config'


def register(parser):
    """Register models subcommands on the given parser."""
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')
    sub.add_parser('list', help='列出模型解析结果')
    p = sub.add_parser('doctor', help='检查模型解析 (auth+match+可选 probe)')
    p.add_argument('--fix-auto', action='store_true',
                   help='把 auth+strong match 的结果自动写入 ~/.louke/models.json (偏好 free)')
    p.add_argument('--ide', default='opencode')
    p.add_argument('--probe', action='store_true',
                   help='对 ✓ 候选调 opencode run 做最小请求验证 (慢、耗 token)')
    p = sub.add_parser('bind', help='绑定抽象名')
    p.add_argument('abstract')
    p.add_argument('full')
    p.add_argument('--project', action='store_true')
    p = sub.add_parser('unbind', help='解绑抽象名')
    p.add_argument('abstract')
    p.add_argument('--project', action='store_true')


def run(args):
    return {
        'list': cmd_list,
        'doctor': cmd_doctor,
        'bind': cmd_bind,
        'unbind': cmd_unbind,
    }[args.command](args)


def config_path(project: bool = False, root=None) -> Path:
    if project:
        root = root or git_root() or Path.cwd()
        return root / '.louke/models.json'
    return Path.home() / '.louke/models.json'


def load_config(path: Path) -> dict:
    if not path.exists():
        return {'$schema': SCHEMA, 'version': 1, 'aliases': {}, 'assignments': {}}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        data = {}
    data.setdefault('$schema', SCHEMA)
    data.setdefault('version', 1)
    data.setdefault('aliases', {})
    data.setdefault('assignments', {})
    return data


def save_config(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    data['$schema'] = SCHEMA
    data.setdefault('version', 1)
    data.setdefault('aliases', {})
    data.setdefault('assignments', {})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def normalize(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', value.lower())


def opencode_models() -> list[str]:
    try:
        out = subprocess.check_output(['opencode', 'models'], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return []
    models = []
    for line in out.splitlines():
        token = line.strip().split()[0] if line.strip() else ''
        if '/' in token:
            models.append(token)
    return models


def auth_providers() -> set[str]:
    """Provider IDs with valid credentials, from `~/.local/share/opencode/auth.json`.

    The file is a JSON object whose keys are the same provider IDs that
    `opencode models` uses in the `<provider>/<model>` prefix. This is the
    source of truth; we don't parse the TUI box-drawing of `opencode auth list`
    because its display names (e.g. "MiniMax (minimaxi.com)") don't match
    the actual provider keys (e.g. "minimax-cn").
    """
    auth_file = Path(
        os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local' / 'share'))
    ) / 'opencode' / 'auth.json'
    if not auth_file.exists():
        return set()
    try:
        data = json.loads(auth_file.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError):
        return set()
    return {k for k, v in data.items() if isinstance(v, dict) and v.get('key')}


def model_costs() -> dict[str, tuple[float, float]]:
    """{full_id: (input_cost, output_cost)} from `opencode models --verbose`.

    Output is a sequence of `<provider>/<id>\n{...}\n` blocks. We walk the
    stream tracking brace depth to extract each JSON object. Returns {} on
    failure (opencode missing, parse error, etc.).
    """
    try:
        out = subprocess.check_output(['opencode', 'models', '--verbose'],
                                      text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return {}
    costs: dict[str, tuple[float, float]] = {}
    i = 0
    n = len(out)
    while i < n:
        if out[i] != '{':
            i += 1
            continue
        depth = 0
        j = i
        while j < n:
            ch = out[j]
            if ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    try:
                        data = json.loads(out[i:j + 1])
                        mid = data.get('id', '')
                        prov = data.get('providerID', '')
                        if mid and prov:
                            cost = data.get('cost') or {}
                            costs[f'{prov}/{mid}'] = (
                                float(cost.get('input', 0) or 0),
                                float(cost.get('output', 0) or 0),
                            )
                    except json.JSONDecodeError:
                        pass
                    i = j + 1
                    break
            j += 1
        else:
            break
    return costs


def is_free(model: str, costs: dict[str, tuple[float, float]]) -> bool:
    c = costs.get(model)
    return c is not None and c[0] == 0 and c[1] == 0


def probe_model(model: str, timeout: int = 30) -> bool:
    """Send a minimal request to verify the model is actually callable.

    Uses `opencode run --model <m> "ping"`. Best-effort: 30s timeout, exit 0
    counts as success. Consumes a small number of tokens.
    """
    try:
        result = subprocess.run(
            ['opencode', 'run', '--model', model, 'ping'],
            capture_output=True, text=True, timeout=timeout,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def used_models(root=None) -> list[str]:
    root = root or git_root() or Path.cwd()
    from .board import agent_source, parse_frontmatter
    result = []
    for fp in sorted(agent_source(root).glob('*.md')):
        if fp.name in {'README.md', 'ROSTER.md'}:
            continue
        fm, _ = parse_frontmatter(fp.read_text(encoding='utf-8'))
        models = fm.get('models') or []
        if isinstance(models, str):
            models = [models]
        result.extend(models)
    return sorted(set(result))


def _rank(candidates: list[str], costs: dict[str, tuple[float, float]]) -> str:
    """Pick best candidate: free > non-opencode > alphabetical."""
    return sorted(
        candidates,
        key=lambda m: (
            0 if is_free(m, costs) else 1,
            1 if m.startswith('opencode/') else 0,
            m,
        ),
    )[0]


def _filter_auth(candidates: list[str], auth: set[str] | None) -> list[str]:
    """If auth info is available, keep only candidates whose provider is auth'd.

    Returns candidates unchanged when auth is None (no auth info) or empty
    (caller signalled "auth discovery unavailable, don't filter").
    """
    if not auth:
        return candidates
    return [m for m in candidates if m.split('/', 1)[0] in auth]


def resolve_model(
    name: str, root=None, models=None,
    auth: set[str] | None = None, costs: dict | None = None,
) -> str:
    root = root or git_root() or Path.cwd()
    project_aliases = load_config(config_path(True, root)).get('aliases', {})
    user_aliases = load_config(config_path(False)).get('aliases', {})
    if name in project_aliases:
        return project_aliases[name]
    if name in user_aliases:
        return user_aliases[name]
    candidates = models if models is not None else opencode_models()
    target = normalize(name)
    strong = [m for m in candidates if normalize(m.split('/')[-1]) == target]
    authed_strong = _filter_auth(strong, auth)
    if authed_strong:
        return _rank(authed_strong, costs or {})
    if strong and not auth:
        return _rank(strong, costs or {})
    weak = [
        m for m in candidates
        if target in normalize(m.split('/')[-1])
        or normalize(m.split('/')[-1]) in target
    ]
    authed_weak = _filter_auth(weak, auth)
    if len(authed_weak) == 1:
        return authed_weak[0]
    if len(weak) == 1 and not auth:
        return weak[0]
    return name


def _classify(name: str, models: list[str], auth: set[str] | None,
              costs: dict) -> tuple[str, str, str]:
    """Return (status, resolved, note).

    status ∈ {alias, ok, candidate, unresolved}
    note  ∈ {'', 'weak', 'unauthenticated', 'weak+unauthenticated', 'probed_ok', 'probe_failed'}
    """
    project_aliases = load_config(config_path(True)).get('aliases', {})
    user_aliases = load_config(config_path(False)).get('aliases', {})
    if name in project_aliases:
        return 'alias', project_aliases[name], ''
    if name in user_aliases:
        return 'alias', user_aliases[name], ''
    target = normalize(name)
    strong = [m for m in models if normalize(m.split('/')[-1]) == target]
    if strong:
        authed = _filter_auth(strong, auth)
        if authed:
            return 'ok', _rank(authed, costs), ''
        if auth is not None:
            return 'candidate', _rank(strong, costs), 'unauthenticated'
        return 'ok', _rank(strong, costs), ''
    weak = [
        m for m in models
        if target in normalize(m.split('/')[-1])
        or normalize(m.split('/')[-1]) in target
    ]
    if weak:
        authed = _filter_auth(weak, auth)
        if len(authed) == 1:
            return 'ok', authed[0], 'weak'
        if auth is not None and weak and not authed:
            return 'candidate', _rank(weak, costs), 'weak+unauthenticated'
        if len(weak) == 1 and not auth:
            return 'ok', weak[0], 'weak'
    return 'unresolved', name, ''


def cmd_list(args):
    for name in used_models():
        resolved = resolve_model(name)
        print(f'{name}\t{resolved if resolved != name else "-"}')
    return 0


def cmd_doctor(args):
    models = opencode_models()
    costs = model_costs() if models else {}
    # auth_providers() reads auth.json directly, so it works even without
    # `opencode` on PATH. But if `opencode models` returned nothing, we
    # also can't match — treat as "no auth info" to keep ✓/✗ simple.
    auth = auth_providers() if models else None
    ok = True
    fixes: dict[str, str] = {}
    for name in used_models():
        status, resolved, note = _classify(name, models, auth, costs)
        if status == 'alias':
            print(f'✓ {name} -> {resolved} (alias)')
            continue
        if status == 'ok':
            tag = f' ({note})' if note else ''
            line = f'✓ {name} -> {resolved}{tag}'
            if args.probe:
                if probe_model(resolved):
                    line += ' (probed ok)'
                else:
                    line += ' (probe failed)'
                    ok = False
            print(line)
            fixes[name] = resolved
            continue
        if status == 'candidate':
            tag = f' ({note})' if note else ''
            print(f'~ {name} -> {resolved}{tag}; '
                  f'run: lk models bind {name} <provider>/<id> after opencode /connect')
            ok = False
            continue
        print(f'✗ {name} unresolved; run: lk models bind {name} provider/{name}')
        ok = False
    if args.fix_auto and fixes:
        path = config_path(False)
        data = load_config(path)
        data['aliases'].update(fixes)
        save_config(path, data)
        print(f'--fix-auto wrote {len(fixes)} aliases to {path}')
    return 0 if ok else 1


def cmd_bind(args):
    path = config_path(args.project)
    data = load_config(path)
    data['aliases'][args.abstract] = args.full
    save_config(path, data)
    return 0


def cmd_unbind(args):
    path = config_path(args.project)
    data = load_config(path)
    data['aliases'].pop(args.abstract, None)
    save_config(path, data)
    return 0
