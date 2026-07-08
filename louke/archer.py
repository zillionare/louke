"""Archer commands - test-plan + architecture/interfaces authoring.

Archer responsibilities: stage 1 (test-plan.md) + stage 2 (architecture.md
+ interfaces.md).
"""
import argparse
import subprocess
import sys
from pathlib import Path

from ._common import _toml_load, PROJECT_INFO_PATH
from .stage_results import write_stage_result


def register(subparsers):
    parser = subparsers.add_parser('archer', help='test-plan + architecture design (Archer)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # ci-scan: AC reference + anti-pattern validation
    p = sub.add_parser('ci-scan', help='CI scan (AC reference closure + anti-patterns)')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--spec')
    g.add_argument('--acceptance')
    p.add_argument('--tests', nargs='+', default=['tests/'])
    p.add_argument('--json', action='store_true')

    # check-acs: AC coverage check
    p = sub.add_parser('check-acs', help='AC reference closure check')
    p.add_argument('--spec', required=True)

    # commit-test-plan: commit test-plan + architecture + interfaces
    p = sub.add_parser('commit-design', help='commit test-plan + architecture + interfaces (git add + commit + push)')
    p.add_argument('--spec', required=True)
    p.add_argument('--message', required=True)

    # validate-test-plan: FR-0700 M-TESTPLAN holdpoint (structure check)
    p = sub.add_parser('validate-test-plan', help='validate test-plan.md structure (M-TESTPLAN holdpoint)')
    p.add_argument('--spec', required=True)

    # validate-arch: FR-0700 M-ARCH holdpoint (structure check)
    p = sub.add_parser('validate-arch', help='validate architecture.md structure (M-ARCH holdpoint)')
    p.add_argument('--spec', required=True)


def run(args):
    handlers = {
        'ci-scan': cmd_ci_scan,
        'check-acs': cmd_check_acs,
        'commit-design': cmd_commit_design,
        'validate-test-plan': cmd_validate_test_plan,
        'validate-arch': cmd_validate_arch,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_ci_scan(args):
    """Invoke louke._tools.ci_scan."""
    cmd = [sys.executable, '-m', 'louke._tools.ci_scan', '--tests', *args.tests]
    if args.acceptance:
        cmd.extend(['--acceptance', args.acceptance])
    else:
        cmd.extend(['--acceptance', f".louke/project/specs/{args.spec}/acceptance.md"])
    if args.json:
        cmd.append('--json')
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
    )
    return result.returncode


def _normalize_repo_relative_path(raw: str) -> str:
    path = Path(str(raw).strip())
    if not str(path):
        raise ValueError('empty path')
    if path.is_absolute():
        raise ValueError(f'absolute path not allowed: {raw}')
    if '..' in path.parts:
        raise ValueError(f'path escapes repo root: {raw}')
    if path.parts and path.parts[0] == '.louke':
        raise ValueError(f'host-project path cannot live under .louke/: {raw}')
    return path.as_posix()


def _validate_e2e_contract() -> list[str]:
    failures: list[str] = []
    data = _toml_load(PROJECT_INFO_PATH)
    if not data:
        return [f'project.toml not readable: {PROJECT_INFO_PATH}']
    meta = data.get('meta') or {}
    if not str(meta.get('test_framework', '')).strip():
        failures.append('missing [meta].test_framework in .louke/project/project.toml')

    e2e = data.get('e2e') or {}
    if not e2e:
        failures.append('missing [e2e] section in .louke/project/project.toml')
        return failures

    run_cmd = str(e2e.get('run', '')).strip()
    if not run_cmd:
        failures.append('missing [e2e].run')

    cwd_raw = str(e2e.get('cwd', '')).strip()
    if cwd_raw:
        try:
            cwd_rel = _normalize_repo_relative_path(cwd_raw)
        except ValueError as exc:
            failures.append(f'invalid [e2e].cwd: {exc}')
        else:
            if not (Path.cwd() / cwd_rel).is_dir():
                failures.append(f'[e2e].cwd does not exist: {cwd_rel}')

    raw_paths = e2e.get('paths')
    if isinstance(raw_paths, str):
        paths = [raw_paths]
    elif isinstance(raw_paths, list):
        paths = [str(item) for item in raw_paths]
    else:
        paths = []
    if not paths:
        failures.append('missing [e2e].paths (must point to host-project test roots)')
    else:
        for raw in paths:
            try:
                rel = _normalize_repo_relative_path(raw)
            except ValueError as exc:
                failures.append(f'invalid [e2e].paths entry: {exc}')
                continue
            if not (Path.cwd() / rel).exists():
                failures.append(f'[e2e].paths target does not exist: {rel}')

    return failures


def cmd_check_acs(args):
    """Invoke louke._tools.check_acs."""
    result = subprocess.run(
        [sys.executable, '-m', 'louke._tools.check_acs',
         '--acceptance', f".louke/project/specs/{args.spec}/acceptance.md"],
        cwd=Path.cwd(),
    )
    return result.returncode


def cmd_commit_design(args):
    """git add test-plan.md + architecture.md + interfaces.md + commit + push."""
    spec_path = f".louke/project/specs/{args.spec}"
    cmds = [
        ['git', 'add', f"{spec_path}/test-plan.md",
         f"{spec_path}/architecture.md", f"{spec_path}/interfaces.md"],
        ['git', 'commit', '-m', args.message],
        ['git', 'push'],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=Path.cwd())
        if result.returncode != 0:
            print(f"failed: {' '.join(cmd)}", file=sys.stderr)
            return result.returncode
    return 0


def cmd_validate_test_plan(args):
    """FR-0700 M-TESTPLAN holdpoint: validate test-plan.md structure."""
    tp = Path(f".louke/project/specs/{args.spec}/test-plan.md")
    if not tp.exists():
        print(f'test-plan.md not found: {tp}', file=sys.stderr)
        write_stage_result(
            spec_id=args.spec,
            stage='M-TESTPLAN',
            kind='author-result',
            role='Archer',
            verdict='fail',
            reviewed_targets=[str(tp)],
            blocking_findings=[f'test-plan.md not found: {tp}'],
        )
        return 1
    text = tp.read_text(encoding='utf-8')
    failures = []
    if '## 1. 立场与边界' not in text and '## 测试策略' not in text:
        failures.append('missing test strategy section (## 1. 立场与边界 or ## 测试策略)')
    for layer in ('unit', 'integration', 'e2e'):
        if layer not in text.lower():
            failures.append(f'missing test layer: {layer}')
            break
    if failures:
        for f in failures:
            print(f'[fail] {f}', file=sys.stderr)
        write_stage_result(
            spec_id=args.spec,
            stage='M-TESTPLAN',
            kind='author-result',
            role='Archer',
            verdict='fail',
            reviewed_targets=[str(tp)],
            blocking_findings=failures,
        )
        return 1
    print('test-plan OK')
    write_stage_result(
        spec_id=args.spec,
        stage='M-TESTPLAN',
        kind='author-result',
        role='Archer',
        verdict='pass',
        reviewed_targets=[str(tp)],
    )
    return 0


def cmd_validate_arch(args):
    """FR-0700 M-ARCH holdpoint: validate architecture.md structure."""
    arch = Path(f".louke/project/specs/{args.spec}/architecture.md")
    test_plan = Path(f".louke/project/specs/{args.spec}/test-plan.md")
    interfaces = Path(f".louke/project/specs/{args.spec}/interfaces.md")
    if not arch.exists():
        print(f'architecture.md not found: {arch}', file=sys.stderr)
        write_stage_result(
            spec_id=args.spec,
            stage='M-ARCH',
            kind='author-result',
            role='Archer',
            verdict='fail',
            reviewed_targets=[str(arch)],
            blocking_findings=[f'architecture.md not found: {arch}'],
        )
        return 1
    text = arch.read_text(encoding='utf-8')
    failures = []
    if not test_plan.exists():
        failures.append(f'test-plan.md not found: {test_plan}')
    if not interfaces.exists():
        failures.append(f'interfaces.md not found: {interfaces}')
    if '## 模块划分' not in text and '## Module' not in text.lower():
        failures.append('missing module breakdown section (## 模块划分 or ## Modules)')
    if 'FR-' not in text:
        failures.append('missing FR reference table')
    failures.extend(_validate_e2e_contract())
    if failures:
        for f in failures:
            print(f'[fail] {f}', file=sys.stderr)
        write_stage_result(
            spec_id=args.spec,
            stage='M-ARCH',
            kind='author-result',
            role='Archer',
            verdict='fail',
            reviewed_targets=[
                str(test_plan),
                str(arch),
                str(interfaces),
                '.louke/project/project.toml',
            ],
            blocking_findings=failures,
        )
        return 1
    print('architecture OK')
    write_stage_result(
        spec_id=args.spec,
        stage='M-ARCH',
        kind='author-result',
        role='Archer',
        verdict='pass',
        reviewed_targets=[
            str(test_plan),
            str(arch),
            str(interfaces),
            '.louke/project/project.toml',
        ],
    )
    return 0
