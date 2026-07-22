"""Agent subcommand router + lk agent lint.

Usage:
    lk agent <name> <subcommand> [options]   # per-agent commands
    lk agent lint [options]                   # v0.6-009 FR-0040: validate agent frontmatter
    lk agent set-model <name> <abstract>      # v0.6-006: change model + bind + probe

All agent commands are dispatched through this module.
`lk agent lint` and `lk agent set-model` are special commands (not agents) for cross-agent operations.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

from . import (
    MIN_OPENCODE_VERSION,
    sage,
    warden,
    lex,
    archer,
    keeper,
    judge,
    prism,
    devon,
    shield,
    librarian,
    maestro,
)


CANONICAL_SEMANTIC_AGENTS = frozenset(
    {
        "sage",
        "lex",
        "archer",
        "judge",
        "prism",
        "devon",
        "shield",
        "librarian",
        "maestro",
        "scribe",
    }
)

AGENTS = {
    "sage": sage,
    "lex": lex,
    "archer": archer,
    "judge": judge,
    "prism": prism,
    "devon": devon,
    "shield": shield,
    "librarian": librarian,
    "maestro": maestro,
}

COMPATIBILITY_ADAPTERS = {
    "warden": warden,
    "keeper": keeper,
}

from ._common import git_root  # noqa: E402

# v0.6-009 FR-0010.5: OpenCode permission key allowlist
# (Qwen A-003-3 calibration: todowrite not included; external_directory + doom_loop added)
PERMISSION_KEYS = {
    "read",
    "edit",
    "glob",
    "grep",
    "bash",
    "task",
    "skill",
    "lsp",
    "question",
    "webfetch",
    "websearch",
    "external_directory",
    "doom_loop",
}

# v0.6-009 FR-0010: 5 agents require a permission block
PERMISSION_REQUIRED = {
    "judge",
    "archer",
    "librarian",
    "maestro",
}

VALID_MODES = {"primary", "subagent", "all"}

# v0.6-009 NFR-0050: single primary agent allowlist
SINGLE_PRIMARY = {"maestro"}

# v0.6-009 NFR-0040: minimum OpenCode version (Qwen A-8.4 calibration)
# The constant is defined in louke/__init__.py as MIN_OPENCODE_VERSION;
# re-exported here for convenient internal reference


def register(parser):
    """Register agent subcommands + special 'lint' / 'set-model' commands."""
    sub = parser.add_subparsers(
        dest="agent_command", required=True, metavar="<command>"
    )

    # v0.6-009 FR-0040: lk agent lint
    p = sub.add_parser(
        "lint", help="validate frontmatter of source agents/*.md for compliance"
    )
    p.add_argument(
        "--check-opencode-version",
        action="store_true",
        help="also check that opencode --version >= MIN_OPENCODE_VERSION",
    )
    p.add_argument(
        "--strict",
        action="store_true",
        help="strict mode: error on fields outside the allowlist (default: warning only)",
    )

    # v0.6-009: lk agent set-model <name> <abstract>
    # Temporarily edits the model: field of .opencode/agents/<name>.md; not persistent
    p = sub.add_parser(
        "set-model",
        help="temporarily change the model field of <name>.md (output). Takes effect "
        "immediately; the next lk board opencode will overwrite it. Use when a model "
        "is temporarily unavailable (cost/busy).",
    )
    p.add_argument("name", help="agent name (e.g. archer)")
    p.add_argument("model", help="abstract model name (e.g. glm-5.2)")
    p.add_argument("--no-probe", action="store_true", help="skip probe check")
    p.add_argument("--root", help="project root directory (default: current git repo)")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="only print what would be done; do not modify",
    )

    # v0.6-007: lk agent list-models
    p = sub.add_parser(
        "list-models",
        help="list the models: chain and current resolved value for every agent",
    )
    p.add_argument("--root", help="project root directory (default: current git repo)")
    p.add_argument(
        "--unbound-only",
        action="store_true",
        help="only show agents that currently fail to resolve (i.e. have an unresolved abstract)",
    )

    # Canonical semantic Agent subcommands.
    for name, module in AGENTS.items():
        if hasattr(module, "register"):
            module.register(sub)
    # Retained CLI names are adapters only; they are not part of AGENTS.
    for name, module in COMPATIBILITY_ADAPTERS.items():
        if hasattr(module, "register"):
            module.register(sub)


def run(args):
    if args.agent_command == "lint":
        return cmd_lint(args)
    if args.agent_command == "set-model":
        return cmd_set_model(args)
    if args.agent_command == "list-models":
        return cmd_list_models(args)
    module = AGENTS.get(args.agent_command)
    if module is None:
        module = COMPATIBILITY_ADAPTERS.get(args.agent_command)
        if module is not None:
            print(
                f"deprecated compatibility adapter: lk agent {args.agent_command}",
                file=sys.stderr,
            )
    if not module or not hasattr(module, "run"):
        print(f"lk agent: '{args.agent_command}' not found", flush=True)
        return 1
    return module.run(args) or 0


def agent_source(root: Path | None = None) -> Path:
    """Canonical agent source directory (the installed louke package).

    Same contract as `louke.board.agent_source`. Kept as a thin wrapper here so
    `lk agent lint` works whether invoked via `board.py` or directly.
    `root` is accepted but ignored.
    """
    from .board import agent_source as _board_agent_source

    return _board_agent_source(root)


def _check_permission_block(name: str, perm, errors: list[str]) -> None:
    """v0.6-009 FR-0040 AC-2: validate permission contents."""
    if not isinstance(perm, dict):
        errors.append(
            f"{name}: permission must be a YAML dict, got {type(perm).__name__}"
        )
        return
    bad_keys = set(perm.keys()) - PERMISSION_KEYS
    if bad_keys:
        errors.append(
            f"{name}: permission has unknown keys: {sorted(bad_keys)}; "
            f"allowed = {sorted(PERMISSION_KEYS)}"
        )
    for key, value in perm.items():
        if key not in PERMISSION_KEYS:
            continue
        if not isinstance(value, str):
            errors.append(
                f"{name}: permission.{key} must be string, got {type(value).__name__}"
            )
            continue
        if (
            value not in ("allow", "deny", "ask")
            and "*" not in value
            and "?" not in value
        ):
            errors.append(
                f"{name}: permission.{key} value {value!r} not in "
                f"{{allow, deny, ask, glob-pattern}}"
            )


def _check_mode_uniqueness(agents_fm: dict, errors: list[str]) -> None:
    """v0.6-009 NFR-0050: count of mode: primary must be 1 (allowlist = maestro)."""
    primaries = [n for n, fm in agents_fm.items() if fm.get("mode") == "primary"]
    if len(primaries) != 1:
        errors.append(
            f"only maestro can be primary; found {len(primaries)} "
            f"agents with mode: primary ({primaries})"
        )
    elif primaries[0] not in SINGLE_PRIMARY:
        errors.append(
            f"mode: primary is reserved for {SINGLE_PRIMARY}, got {primaries[0]}"
        )
    all_modes = [n for n, fm in agents_fm.items() if fm.get("mode") == "all"]
    if all_modes:
        errors.append(
            f"mode: all is deprecated; use primary or subagent. found in: {all_modes}"
        )


def _check_subagent_task_deny(agents_fm: dict, warnings: list[str]) -> None:
    """v0.6.14 (GLM review): all subagents must explicitly set task: deny.

    OpenCode defaults task: allow (unspecified = allow). If a subagent omits
    task: deny, small models like M3 will get confused between task/question
    tools / hallucinate "no question tool".

    See .louke/review-sage-question-tool.md §6.2.
    """
    for name, fm in agents_fm.items():
        if (
            name == "maestro"
        ):  # maestro is the primary, the only one that should have task: allow
            continue
        if fm.get("mode") != "subagent":
            continue
        perm = fm.get("permission") or {}
        if not isinstance(perm, dict):
            continue
        if perm.get("task") != "deny":
            warnings.append(
                f"{name}: subagent missing task: deny (OpenCode defaults task: allow, "
                f"which would let the subagent call the task tool, violating the "
                f'"Maestro is the sole orchestrator" design. Add task: deny to force '
                f"the subagent to use only direct tools such as question)"
            )


def _get_opencode_version() -> str | None:
    """Read `opencode --version`, return None if opencode unavailable."""
    try:
        out = subprocess.check_output(
            ["opencode", "--version"], text=True, stderr=subprocess.DEVNULL
        )
        m = re.search(r"(\d+\.\d+\.\d+)", out)
        return m.group(1) if m else None
    except Exception:
        return None


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split("."))


def cmd_lint(args):
    root = git_root() or Path.cwd()
    src = agent_source(root)
    if not src.exists():
        print(f"[!] agent source dir not found: {src}", flush=True)
        return 1

    from .board import parse_frontmatter

    agents_fm: dict[str, dict] = {}
    errors: list[str] = []

    for fp in sorted(src.glob("*.md")):
        if fp.name in {"README.md", "ROSTER.md"}:
            continue
        text = fp.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(text)
        name = fm.get("name") or fp.stem
        agents_fm[name] = fm

        # Required agents must declare permissions; every declared block must
        # still be validated so newly added agents cannot bypass the allowlist.
        if "permission" in fm:
            _check_permission_block(name, fm["permission"], errors)
        elif name in PERMISSION_REQUIRED:
            errors.append(f"missing permission block for {name}")
            continue

        # FR-0040 AC-2: mode field is required and must be valid
        mode = fm.get("mode")
        if not mode:
            errors.append(f"{name}: missing mode field")
        elif mode not in VALID_MODES:
            errors.append(f"{name}: mode {mode!r} not in {sorted(VALID_MODES)}")

    # NFR-0050: single primary constraint
    _check_mode_uniqueness(agents_fm, errors)

    # v0.6.14 GLM review: subagents must have task: deny
    from ._color import yellow

    warnings: list[str] = []
    _check_subagent_task_deny(agents_fm, warnings)
    for w in warnings:
        print(f"  {yellow('⚠')} {w}", flush=True)

    # NFR-0040: OpenCode version check (optional)
    if args.check_opencode_version:
        actual = _get_opencode_version()
        if actual is None:
            print("[!] opencode --version unavailable, skip version check", flush=True)
        elif _version_tuple(actual) < _version_tuple(MIN_OPENCODE_VERSION):
            print(
                f"[!] opencode {actual} < MIN_OPENCODE_VERSION "
                f"{MIN_OPENCODE_VERSION}; permission object format may not work",
                flush=True,
            )
        else:
            print(
                f"[ok] opencode {actual} >= MIN_OPENCODE_VERSION "
                f"{MIN_OPENCODE_VERSION}",
                flush=True,
            )

    if errors:
        from ._color import fail, red

        print(f"{fail(f'{len(errors)} errors:')}", flush=True)
        for e in errors:
            print(f"  {red('-')} {e}", flush=True)
        return 1
    from ._color import ok, cyan, dim

    print(
        f"{ok()} {len(agents_fm)} agents pass lint "
        f"{dim('(')}{cyan(str(sum(1 for fm in agents_fm.values() if 'permission' in fm)))}{dim(' with permission)')}",
        flush=True,
    )
    return 0


def _resolve_root(args) -> Path | None:
    """Resolve project root for set-model: --root > git_root() > error."""
    from ._color import red, cyan

    explicit = getattr(args, "root", None)
    if explicit:
        root = Path(explicit).resolve()
    else:
        root = git_root()
    if root is None:
        print(
            f"{red('error:')} lk agent set-model requires a git repo (or explicit --root).",
            file=sys.stderr,
        )
        print(
            f"  {cyan('hint:')} run from the louke project root (the one with .git/), or pass --root <path>",
            file=sys.stderr,
        )
        return None
    return Path(root)


def cmd_set_model(args):
    """v0.6-009: lk agent set-model <name> <abstract>

    Temporarily edits the model: field of .opencode/agents/<name>.md (not persistent, takes effect immediately).

    Use case: a model is temporarily unavailable (cost/busy); switch to another model for one run.
    Note: the next `lk board opencode` regenerates from source and overwrites this change.

    Flow:
    1. Find .opencode/agents/<name>.md (the output, not the source)
    2. resolve abstract -> real model (alias / interactive bind)
    3. probe validation (v0.6.5 flow)
    4. regex-replace the model: line of the output file
    """
    from ._color import ok, fail, warn, info, cyan, red
    from .models import (
        resolve_model,
        _interactive_bind_one,
        _probe_or_skip,
    )

    name: str = args.name
    abstract: str = args.model

    # 1. Resolve project root
    explicit = getattr(args, "root", None)
    if explicit:
        root = Path(explicit).resolve()
    else:
        root = git_root()
    if root is None:
        print(
            f"{red('error:')} lk agent set-model requires a git repo (or explicit --root).",
            file=sys.stderr,
        )
        return 1

    # 2. Find OUTPUT file (.opencode/agents/<name>.md)
    out_dir = root / ".opencode/agents"
    out_file = out_dir / f"{name}.md"
    if not out_file.exists():
        candidates = [f for f in out_dir.glob("*.md") if f.stem.lower() == name.lower()]
        if not candidates:
            print(f"{fail(f'output file not found: {out_file}')}", file=sys.stderr)
            print(
                f"  {cyan('hint:')} run lk board opencode first to generate the output",
                file=sys.stderr,
            )
            return 1
        if len(candidates) > 1:
            names = ", ".join(c.name for c in candidates)
            print(f"{fail(f'multiple matches for {name!r}: {names}')}", file=sys.stderr)
            return 1
        out_file = candidates[0]

    # 3. Resolve abstract
    resolved = resolve_model(abstract)
    if not args.dry_run and resolved == abstract:
        # Unbound -> interactive
        print(f"{warn(f'{abstract} unbound, entering interactive mode...')}")
        if args.no_probe:
            print(
                f"{info('hint: run lk models bind <abstract> <full> to set an alias')}"
            )
            return 0
        result = _interactive_bind_one(abstract, False)
        if result != 0:
            return result
        resolved = resolve_model(abstract)
    elif not args.dry_run and not args.no_probe:
        # Bound -> probe validation
        probed = _probe_or_skip(resolved, False, allow_skip=True)
        if not probed:
            print(
                f"{warn(f'{resolved} probe failed but already bound, continuing (may fail at runtime)')}"
            )

    if args.dry_run:
        print(f"{info(f'[dry-run] {out_file.name}: model -> {resolved} (temporary)')}")
        return 0

    # 4. Update output file's model: line (regex replace)
    text = out_file.read_text(encoding="utf-8")
    pattern = re.compile(r"(^model:\s*)\S+", re.MULTILINE)
    new_text, n = pattern.subn(rf"\g<1>{resolved}", text, count=1)
    if n == 0:
        # No model: line (anomaly). Try to insert on the second frontmatter line.
        print(f"{warn(f'{out_file.name} has no model: line, attempting to insert...')}")
        new_text = re.sub(
            r"^(---.*?\n)", rf"\1model: {resolved}\n", text, count=1, flags=re.DOTALL
        )
    out_file.write_text(new_text, encoding="utf-8")
    print(
        f"{ok(f'{out_file.name}: model -> {resolved} (temporary; the next lk board opencode will overwrite it)')}"
    )
    return 0


def cmd_list_models(args):
    """v0.6-007: lk agent list-models -- show each agent's models: chain and current resolved value."""
    from ._color import cyan, yellow as y, red, green, bold
    from .board import agent_source, parse_frontmatter
    from .models import frontmatter_binding
    from .models import resolve_model

    # 1. Resolve project root
    explicit = getattr(args, "root", None)
    if explicit:
        root = Path(explicit).resolve()
    else:
        root = git_root()
    if root is None:
        print(
            f"{red('error:')} lk agent list-models requires a git repo (or explicit --root).",
            file=sys.stderr,
        )
        return 1

    src = agent_source(root)
    if not src.exists():
        print(f"{red(f'agent source not found: {src}')}", file=sys.stderr)
        return 1

    # 2. Collect each agent's models: chain
    rows = []  # [(name, models_chain, resolved_or_None)]
    for fp in sorted(src.glob("*.md")):
        if fp.name in {"README.md", "ROSTER.md"}:
            continue
        text = fp.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(text)
        name = str(fm.get("name") or fp.stem)
        binding = frontmatter_binding(fm)
        # Current resolved = the first entry in the chain that resolves
        resolved = None
        if binding:
            r_real = resolve_model(binding)
            if (
                r_real != binding
            ):  # not equal to the abstract (means resolution succeeded)
                resolved = r_real
        rows.append((name, [binding] if binding else [], resolved))

    # 3. Filter
    if getattr(args, "unbound_only", False):
        rows = [r for r in rows if r[2] is None]

    if not rows:
        print(f"{green('✓')} all agents are resolved")
        return 0

    # 4. Print the table
    name_w = max(len(r[0]) for r in rows)
    print(
        f"{bold('agent')}      | {bold('models: chain')}"
        f"{' ' * max(0, 30 - 12)} | {bold('current resolved')}"
    )
    print(f"{'-' * (name_w + 4)}-+-{'-' * 32}-+-{'-' * 30}")
    for name, models, resolved in rows:
        chain = ", ".join(models)
        if len(chain) > 30:
            chain = chain[:27] + "..."
        if resolved:
            res_str = f"{cyan(resolved)}"
        else:
            res_str = f"{y('(unbound)')} <- run lk models bind"
        print(f"{name:<{name_w}} | {chain:<32} | {res_str}")
    return 0
