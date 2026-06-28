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

from ._common import git


# 阶段表 (与 agents/Maestro.md 同步)
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

    p = sub.add_parser('advance', help='推进到下一阶段')
    p.add_argument('--stage', required=True, help='当前阶段代码, 例 M-DEV')
    p.add_argument('--force', action='store_true',
                   help='跳过退出条件自动检查 (手动确认场景)')

    p = sub.add_parser('regress', help='退回当前阶段')
    p.add_argument('--stage', required=True)
    p.add_argument('--reason', required=True)

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


def cmd_status(args):
    """Show stage table + current progress."""
    cwd = Path.cwd()
    print(f"=== Maestro Status ===")
    print()

    # 读 project-info.md
    info_path = cwd / '.louke/project/project-info.md'
    if info_path.exists():
        print(f"--- project-info.md ---")
        print(info_path.read_text(encoding='utf-8'))
        print()

    # Show stage table
    print(f"--- Stage Table ---")
    print(f"{'Code':<14} {'Stage':<14} {'Implementer':<14} {'Reviewer':<20}")
    for code, name, impl, rev in STAGES:
        print(f"{code:<14} {name:<14} {str(impl or '-'):<14} {str(rev or '-'):<20}")

    # Current branch
    rc, branch, _ = git('branch', '--show-current', cwd=cwd)
    if rc == 0 and branch.strip():
        print(f"\nCurrent branch: {branch.strip()}")

    return 0


def cmd_advance(args):
    """推进到下一阶段 - 检查当前阶段退出条件."""
    cwd = Path.cwd()
    print(f"=== Advance ===")
    print(f"From: {args.stage}")

    # 找当前阶段的索引
    idx = None
    for i, (code, _, _, _) in enumerate(STAGES):
        if code == args.stage:
            idx = i
            break
    if idx is None:
        print(f"未知阶段: {args.stage}")
        return 1

    # M-MILESTONE 是最后阶段: 从它 advance = milestone 收尾, 是 success
    if args.stage == 'M-MILESTONE':
        print(f"M-MILESTONE 是最终阶段; advance 视为 milestone 收尾。")
        print(f"  请执行: lk librarian distill + lint → 关闭 milestone")
        print(f"→ milestone 收尾指令已发出 (无后续阶段)")
        return 0

    if idx + 1 >= len(STAGES):
        print(f"未知状态: stage={args.stage} 在阶段表末尾之后")
        return 1

    next_code, next_name, next_impl, next_rev = STAGES[idx + 1]
    print(f"To:   {next_code} ({next_name})")
    print(f"     Implementer: {next_impl or '-'}")
    print(f"     Reviewer: {next_rev or '-'}")
    print()

    # 退出条件检查
    # 关键: hold point 机制要求未实现的自动检查 = 阻塞,
    # 防止"用 [todo] 占位就 advance 成功"导致流程失效。
    # --force 标志给手动确认场景 (人类已自行核对) 用。
    print(f"--- 退出条件检查 ({args.stage}) ---")
    if args.force:
        print(f"[--force] 跳过自动检查, 人类已确认")
        print(f"\n→ 推进到 {next_code}")
        return 0

    ok = True

    if args.stage == 'M-FOUND':
        # project-info.md 存在
        info = cwd / '.louke/project/project-info.md'
        if info.exists():
            print(f"[ok] project-info.md 存在")
        else:
            print(f"[high] project-info.md 不存在")
            ok = False
    elif args.stage == 'M-SPEC':
        # 所有 quote resolved
        rc, out, _ = git('rev-parse', '--show-toplevel', cwd=cwd)
        spec_root = Path(out.strip()) if rc == 0 else cwd
        specs = list((spec_root / '.louke/project/specs').glob('*/spec.md'))
        if not specs:
            print(f"[high] 无 spec.md — M-SPEC 必交付")
            ok = False
        else:
            for sp in specs:
                print(f"  spec: {sp.parent.name}")
                print(f"    [todo: 自动调 lk sage quote-check 验证 — 未实现]")
                # 未实现的自动检查 = 阻塞 (符合 hold point 语义)
                ok = False
    elif args.stage == 'M-TESTPLAN':
        # test-plan.md 存在 + Sage 评审通过
        print(f"  [todo: 调 lk archer validate-test-plan + lk sage review 验证]")
        ok = False
    elif args.stage == 'M-ARCH':
        # architecture.md + interfaces.md 存在 + Prism 评审通过
        print(f"  [todo: 调 lk archer validate-arch + lk prism review-arch 验证]")
        ok = False
    elif args.stage == 'M-LOCK':
        # 三信号齐: Sage + Lex + 用户确认
        print(f"  [todo: 调 lk lex verify-acceptance + lk sage quote-check + 等待用户 IDE 确认]")
        ok = False
    elif args.stage == 'M-DEV':
        # 测试通过 + lint 通过
        print(f"  [todo: 调 lk keeper gate --tests 验证]")
        ok = False
    elif args.stage == 'M-E2E':
        # e2e 通过
        print(f"  [todo: 调 lk shield run-e2e 验证]")
        ok = False
    elif args.stage == 'M-BUGFIX':
        # 回归通过
        print(f"  [todo: 调 lk keeper regression --tests 验证]")
        ok = False
    elif args.stage == 'M-SECURITY':
        # security audit 通过 (or user disabled)
        print(f"  [todo: 调 lk judge security-audit 验证, 或检查 DoD 是否关闭]")
        ok = False

    if ok:
        print(f"\n→ 推进到 {next_code}")
        # TODO: 更新 project-info.md 记录当前阶段
        return 0
    else:
        print(f"\n→ 拒绝推进 (退出条件未自动验证)")
        print(f"  提示: 人工核对后用 'lk maestro advance --stage {args.stage} --force' 强制推进")
        return 1


def cmd_regress(args):
    """退回当前阶段."""
    cwd = Path.cwd()
    print(f"=== Regress ===")
    print(f"Stage: {args.stage}")
    print(f"Reason: {args.reason}")
    print()

    # 记录到 raw
    raw_dir = cwd / '.louke/raw/'
    raw_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now().strftime('%Y-%m-%d')
    ts_file = raw_dir / f"{ts}-regress.md"
    content = f"""---
date: {ts}
session: maestro-regress-{args.stage}
agents: [Maestro]
related_issues: []
status: open
supersedes: []
---

## 议题
阶段 {args.stage} 被退回

## 决定
退回原因: {args.reason}

## 开放问题
{args.stage} 阶段的实施者需修复, 然后重新申请 advance
"""
    if ts_file.exists():
        content = ts_file.read_text() + '\n---\n' + content
    ts_file.write_text(content)
    print(f"✓ Recorded in {ts_file.relative_to(cwd)}")
    return 0


def cmd_escalate(args):
    """上报用户 - 生成给用户的告警."""
    cwd = Path.cwd()
    print(f"=== Escalate to User ===")
    print(f"Reason: {args.reason}")
    print(f"Agent: {args.agent or '(not specified)'}")
    print()

    alert = f"""@user **需要人工介入**

Agent: {args.agent or '(unknown)'}
Reason: {args.reason}

请介入处理。
"""
    print(alert)
    print(f"→ 在 chat 中发送上述告警给用户")
    return 0