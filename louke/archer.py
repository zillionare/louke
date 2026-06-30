"""Archer commands - test-plan + architecture/interfaces 编写.

Archer 职责: 阶段一（test-plan.md）+ 阶段二（architecture.md + interfaces.md）。
"""
import argparse
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('archer', help='test-plan + 架构设计 (Archer)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # ci-scan: AC 引用 + 反模式校验
    p = sub.add_parser('ci-scan', help='CI 扫描（AC 引用闭合 + 反模式）')
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--spec')
    g.add_argument('--acceptance')
    p.add_argument('--tests', default='tests/')
    p.add_argument('--json', action='store_true')

    # check-acs: AC 覆盖率检查
    p = sub.add_parser('check-acs', help='AC 引用闭合检查')
    p.add_argument('--spec', required=True)

    # commit-test-plan: 提交 test-plan + architecture + interfaces
    p = sub.add_parser('commit-design', help='提交 test-plan + architecture + interfaces (git add + commit + push)')
    p.add_argument('--spec', required=True)
    p.add_argument('--message', required=True)

    # validate-test-plan: FR-0700 M-TESTPLAN holdpoint (structure check)
    p = sub.add_parser('validate-test-plan', help='校验 test-plan.md 结构 (M-TESTPLAN holdpoint)')
    p.add_argument('--spec', required=True)

    # validate-arch: FR-0700 M-ARCH holdpoint (structure check)
    p = sub.add_parser('validate-arch', help='校验 architecture.md 结构 (M-ARCH holdpoint)')
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
    """调用 louke._tools.ci_scan."""
    cmd = [sys.executable, '-m', 'louke._tools.ci_scan', '--tests', args.tests]
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


def cmd_check_acs(args):
    """调用 louke._tools.check_acs."""
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
    """FR-0700 M-TESTPLAN holdpoint: 校验 test-plan.md 结构."""
    tp = Path(f".louke/project/specs/{args.spec}/test-plan.md")
    if not tp.exists():
        print(f'test-plan.md not found: {tp}', file=sys.stderr)
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
        return 1
    print('test-plan OK')
    return 0


def cmd_validate_arch(args):
    """FR-0700 M-ARCH holdpoint: 校验 architecture.md 结构."""
    arch = Path(f".louke/project/specs/{args.spec}/architecture.md")
    if not arch.exists():
        print(f'architecture.md not found: {arch}', file=sys.stderr)
        return 1
    text = arch.read_text(encoding='utf-8')
    failures = []
    if '## 模块划分' not in text and '## Module' not in text.lower():
        failures.append('missing module breakdown section (## 模块划分 or ## Modules)')
    if 'FR-' not in text:
        failures.append('missing FR reference table')
    if failures:
        for f in failures:
            print(f'[fail] {f}', file=sys.stderr)
        return 1
    print('architecture OK')
    return 0