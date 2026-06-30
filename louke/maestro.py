"""Maestro commands - 流程推进控制.

Maestro 职责: 协调所有 agent, 监控退出条件, 决策推进/退回/上报。
lk 提供: status 查询 + advance/regress/escalate 操作。
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ._common import git, raw_path


STAGES = [
    ('M-FULL', '全程', None, None),
    ('M-FOUND', '项目奠基', 'Scout', 'Warden'),
    ('M-SPEC', '定需求', 'Sage', 'Lex'),
    ('M-TESTPLAN', '定测试计划', 'Archer', 'Sage'),
    ('M-ARCH', '架构设计', 'Archer', 'Prism'),
    ('M-LOCK', '需求锁定', 'Maestro', '人类'),
    ('M-DEV', '开发执行', 'Devon', 'Prism → Keeper'),
    ('M-E2E', 'e2e 开发', 'Shield', 'Prism → Keeper'),
    ('M-BUGFIX', 'Bug 修复', 'Devon', 'Keeper'),
    ('M-SECURITY', '安全审计', 'Judge (S级)', '用户'),
    ('M-MILESTONE', 'milestone 结束', 'Librarian', 'Maestro'),
]


def register(subparsers):
    parser = subparsers.add_parser('maestro', help='流程推进控制 (Maestro)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('status', help='查看当前 spec/milestone 阶段进度')
    p.add_argument('--spec', default='', help='spec-id (留空看全表)')

    p = sub.add_parser('advance', help='推进到下一阶段 (FR-0700 自动 holdpoint)')
    p.add_argument('--stage', required=True, help='当前阶段代码, 例 M-DEV')
    p.add_argument('--spec-id', default='', help='目标 spec-id (某些阶段需要)')
    p.add_argument('--commit-range', default='HEAD~1..HEAD', help='M-DEV / M-E2E gate 使用')
    p.add_argument('--release', default='releases/v0.1', help='M-SECURITY 使用')
    p.add_argument('--confirm', action='store_true', help='M-LOCK 用户确认')
    p.add_argument('--force', action='store_true', help='跳过退出条件自动检查 (手动确认场景)')

    p = sub.add_parser('regress', help='退回当前阶段')
    p.add_argument('--stage', required=True)
    p.add_argument('--reason', required=True)
    p.add_argument('--spec-id', default='')

    p = sub.add_parser('escalate', help='上报用户 (连续失响应 / 需求根本矛盾)')
    p.add_argument('--reason', required=True)
    p.add_argument('--agent', default='', help='哪个 agent 触发上报')


def run(args):
    handlers = {
        'status': cmd_status,
        'advance': cmd_advance,
        'regress': cmd_regress,
        'escalate': cmd_escalate,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def _read_project_info(label):
    path = Path('.louke/project/project-info.md')
    if not path.exists():
        return ''
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        prefix = f'- **{label}**:'
        if line.startswith(prefix):
            return line.split(':', 1)[1].strip().strip('`')
    return ''


def _set_project_info_current_stage(stage):
    path = Path('.louke/project/project-info.md')
    if not path.exists():
        return
    text = path.read_text(encoding='utf-8')
    if '- **Current Stage**' in text:
        text = '\n'.join(
            line if not line.startswith('- **Current Stage**:') else f'- **Current Stage**: {stage}'
            for line in text.splitlines()
        )
    path.write_text(text, encoding='utf-8')


def _run_lk(*args):
    return subprocess.run([sys.executable, '-m', 'louke.__main__', *args],
                          cwd=Path.cwd()).returncode


def _record_raw_event(stage, event, status='open', extra=None):
    raw_dir = Path(raw_path(date=datetime.now().strftime('%Y-%m-%d'),
                            session_id=f'maestro-stage-{stage.lower()}-{datetime.now().strftime("%H%M%S")}')).parent
    raw_dir.mkdir(parents=True, exist_ok=True)
    fp = raw_path(date=datetime.now().strftime('%Y-%m-%d'),
                  session_id=f'maestro-stage-{stage.lower()}-{datetime.now().strftime("%H%M%S")}')
    fm = (
        '---\n'
        f'date: {datetime.now().strftime("%Y-%m-%d")}\n'
        f'session: maestro-{event}-{stage}\n'
        'agents: [Maestro]\n'
        f'status: {status}\n'
        'supersedes: []\n'
        '---\n\n'
        f'## 议题\nMaestro {event} {stage}\n\n'
        f'## 决定\n{extra or ""}\n'
    )
    fp.write_text(fm, encoding='utf-8')


def cmd_status(args):
    """Show stage table + current progress."""
    cwd = Path.cwd()
    print(f"=== Maestro Status ===")
    info_path = cwd / '.louke/project/project-info.md'
    if info_path.exists():
        print(f"\n--- project-info.md ---")
        print(info_path.read_text(encoding='utf-8'))
    print(f"\n--- Stage Table ---")
    print(f"{'Code':<14} {'Stage':<14} {'Implementer':<14} {'Reviewer':<20}")
    for code, name, impl, rev in STAGES:
        print(f"{code:<14} {name:<14} {str(impl or '-'):<14} {str(rev or '-'):<20}")
    rc, branch, _ = git('branch', '--show-current', cwd=cwd)
    if rc == 0 and branch.strip():
        print(f"\nCurrent branch: {branch.strip()}")
    return 0


# ---- FR-0700 holdpoint dispatch ----

def _holdpoint(stage, args):
    """Return (ok, message)."""
    spec = args.spec_id or _read_current_spec()
    if stage == 'M-FOUND':
        if not Path('.louke/project/project-info.md').exists():
            return False, 'project-info.md missing; run lk scout foundation first'
        return True, 'project-info.md exists'
    if stage == 'M-SPEC':
        if not spec:
            return False, 'spec-id required (--spec-id)'
        rc = _run_lk('sage', 'quote-check', '--spec', spec)
        if rc != 0:
            return False, f'sage quote-check failed (rc={rc})'
        return True, 'quote-check exit 0'
    if stage == 'M-TESTPLAN':
        # FR-0700: lk archer validate-test-plan
        if not spec:
            return False, 'spec-id required (--spec-id)'
        rc = _run_lk('archer', 'validate-test-plan', '--spec', spec)
        if rc != 0:
            return False, f'archer validate-test-plan failed (rc={rc})'
        return True, f'test-plan validated ({spec})'
    if stage == 'M-ARCH':
        # FR-0700: lk archer validate-arch
        if not spec:
            return False, 'spec-id required (--spec-id)'
        rc = _run_lk('archer', 'validate-arch', '--spec', spec)
        if rc != 0:
            return False, f'archer validate-arch failed (rc={rc})'
        return True, f'architecture validated ({spec})'
    if stage == 'M-LOCK':
        if not spec:
            return False, 'spec-id required'
        if not args.confirm:
            return False, 'User signal missing: pass --confirm (Maestro via IDE)'
        rc = _run_lk('sage', 'record-lock', '--spec', spec, '--confirm')
        if rc != 0:
            return False, f'sage record-lock failed (rc={rc})'
        return True, 'record-lock exit 0 (Sage+Lex+User signals)'
    if stage == 'M-DEV':
        rc = _run_lk('keeper', 'gate', '--commit-range', args.commit_range)
        if rc != 0:
            return False, f'keeper gate failed (rc={rc})'
        return True, 'keeper gate exit 0'
    if stage == 'M-E2E':
        rc = _run_lk('shield', 'run-e2e', '--spec', spec or '')
        if rc != 0:
            return False, f'shield run-e2e failed (rc={rc})'
        rc = _run_lk('keeper', 'gate', '--commit-range', args.commit_range, '--tests')
        if rc != 0:
            return False, f'keeper gate --tests failed (rc={rc})'
        return True, 'shield run-e2e + keeper gate exit 0'
    if stage == 'M-BUGFIX':
        rc = _run_lk('keeper', 'regression', '--baseline', 'main', '--current', 'HEAD')
        if rc != 0:
            return False, f'keeper regression failed (rc={rc})'
        return True, 'keeper regression exit 0'
    if stage == 'M-SECURITY':
        # FR-0720: skip if Security Audit disabled
        sec = _read_project_info('Security Audit').strip().lower()
        if sec == 'disabled':
            return True, 'Security Audit disabled in DoD; skip'
        rc = _run_lk('judge', 'security-audit', '--release', args.release)
        if rc == 1:
            return False, 'judge security-audit fail'
        if rc == 2:
            return False, 'judge security-audit needs-human-review (treat as blocked)'
        return True, 'judge security-audit pass'
    if stage == 'M-MILESTONE':
        # FR-0730
        rc, out, _ = git('status', '--porcelain')
        if rc == 0 and out.strip():
            return False, 'git working tree not clean; commit/stash before milestone'
        # check release merge (best-effort)
        rc, out, _ = git('rev-parse', '--verify', f'refs/tags/{args.release.lstrip("releases/")}')
        if rc != 0:
            return False, f'git tag v{args.release} missing; run: git tag {args.release.lstrip("releases/")}'
        return True, 'working tree clean + tag present'
    return True, 'no automated holdpoint'


def _read_current_spec():
    return _read_project_info('Spec ID')


def cmd_advance(args):
    """推进到下一阶段 (FR-0700 自动 holdpoint + FR-0710 state update)."""
    cwd = Path.cwd()
    print(f"=== Advance ===")
    print(f"From: {args.stage}")
    idx = next((i for i, t in enumerate(STAGES) if t[0] == args.stage), None)
    if idx is None:
        print(f'未知阶段: {args.stage}', file=sys.stderr)
        return 1

    if args.stage == 'M-MILESTONE':
        print('M-MILESTONE is the final stage; advance marks milestone close.')
        _set_project_info_current_stage('M-MILESTONE')
        _record_raw_event(args.stage, 'closed', status='resolved', extra='milestone closed')
        print('→ milestone closed')
        return 0
    if idx + 1 >= len(STAGES):
        print(f'unknown tail stage {args.stage}', file=sys.stderr)
        return 1
    next_code = STAGES[idx + 1][0]
    print(f'To:   {next_code}')

    if args.force:
        print(f'[--force] skipping automated checks')
        _set_project_info_current_stage(next_code)
        _record_raw_event(args.stage, 'advance-force', extra=f'forced advance to {next_code}')
        print(f'→ forced advance to {next_code}')
        return 0

    ok, msg = _holdpoint(args.stage, args)
    print(f'[{ "ok" if ok else "high" }] {msg}')
    if not ok:
        print(f'\n→ 拒绝 ({msg})')
        print(f'  提示: 人工核对后用 "lk maestro advance --stage {args.stage} --force" 强制推进')
        return 1
    _set_project_info_current_stage(next_code)
    _record_raw_event(args.stage, 'advance', extra=f'advanced to {next_code}')
    print(f'→ 推进到 {next_code}')
    return 0


def cmd_regress(args):
    """退回当前阶段."""
    cwd = Path.cwd()
    print(f"=== Regress ===")
    print(f"Stage: {args.stage}")
    print(f"Reason: {args.reason}")
    raw_dir = Path(raw_path(date=datetime.now().strftime('%Y-%m-%d'),
                            session_id=f'maestro-regress-{args.stage.lower()}-{datetime.now().strftime("%H%M%S")}')).parent
    raw_dir.mkdir(parents=True, exist_ok=True)
    fp = raw_path(date=datetime.now().strftime('%Y-%m-%d'),
                  session_id=f'maestro-regress-{args.stage.lower()}-{datetime.now().strftime("%H%M%S")}')
    fm = (
        '---\n'
        f'date: {datetime.now().strftime("%Y-%m-%d")}\n'
        f'session: maestro-regress-{args.stage}\n'
        'agents: [Maestro]\n'
        'related_issues: []\n'
        'status: open\n'
        'supersedes: []\n'
        '---\n\n'
        '## 议题\n'
        f'阶段 {args.stage} 被退回\n\n'
        '## 决定\n'
        f'退回原因: {args.reason}\n\n'
        '## 开放问题\n'
        f'{args.stage} 阶段的实施者需修复, 然后重新申请 advance\n'
    )
    fp.write_text(fm, encoding='utf-8')
    print(f'✓ Recorded in {fp}')
    return 0


def cmd_escalate(args):
    """上报用户 - 生成给用户的告警."""
    print(f"=== Escalate to User ===")
    print(f"Reason: {args.reason}")
    print(f"Agent: {args.agent or '(not specified)'}")
    alert = (
        '@user **需要人工介入**\n\n'
        f'Agent: {args.agent or "(unknown)"}\n'
        f'Reason: {args.reason}\n\n'
        '请介入处理。\n'
    )
    print(alert)
    print(f'→ 在 chat 中发送上述告警给用户')
    return 0