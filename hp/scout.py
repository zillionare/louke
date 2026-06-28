"""Scout commands - 项目奠基.

Scout 职责: 收集项目信息、创建 repo、创建 project、验证权限。
所有命令通过本模块暴露。
"""
import argparse
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('scout', help='项目奠基 (Scout)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # identity-check: 验证 gh 与 git 账号一致 (Step 4a, 防止 PR push 成功但 issue create 403)
    p = sub.add_parser('identity-check', help='验证 gh/git 账号一致 (Step 4a)')
    p.add_argument('--repo', required=True, help='owner/repo 格式')

    # foundation: 完整奠基流程 (Steps 1-8, 含权限验证)
    p = sub.add_parser('foundation', help='完整奠基流程 (Steps 1-8, 交互式)')
    p.add_argument('--repo', required=True)
    p.add_argument('--version', required=True)
    p.add_argument('--spec-id', required=True)
    p.add_argument('--upstream', default='main')

    # commit-foundation: Step 8 多步 git 操作封装
    p = sub.add_parser('commit-foundation', help='提交奠基产物 (Step 8: git add + commit + push)')
    p.add_argument('--spec-id', required=True)
    p.add_argument('--message', required=True, help='commit message')
    p.add_argument('--version', required=True, help='release 分支名, 例 v0.1')


def run(args):
    handlers = {
        'identity-check': cmd_identity_check,
        'foundation': cmd_foundation,
        'commit-foundation': cmd_commit_foundation,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_identity_check(args):
    """Wrap tools/check_identity.py."""
    result = subprocess.run(
        ['python3', 'tools/check_identity.py', '--repo', args.repo],
        cwd=Path.cwd(),
    )
    return result.returncode


def cmd_foundation(args):
    """完整奠基流程 (Steps 1-8) — 占位，需要交互式实现."""
    print(f"Scout foundation: repo={args.repo}, version={args.version}, spec={args.spec_id}")
    print("此命令需交互式收集 Story/版本号/Repo 名/DoD — 当前为占位实现")
    return 1


def cmd_commit_foundation(args):
    """Step 8 多步 git 操作封装.

    执行顺序:
    1. git add .quanti-forge/project/specs/{spec-id}/*.md
    2. git add .quanti-forge/project/project-info.md
    3. git commit -m {message}
    4. git push -u origin releases/{version}

    失败时: 任一命令 exit 非 0 → 中止后续，返回非 0 退出码。
    """
    spec_path = f".quanti-forge/project/specs/{args.spec_id}"
    cmds = [
        ['git', 'add', f"{spec_path}/*.md",
         '.quanti-forge/project/project-info.md'],
        ['git', 'commit', '-m', args.message],
        ['git', 'push', '-u', 'origin', f'releases/{args.version}'],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=Path.cwd())
        if result.returncode != 0:
            print(f"failed: {' '.join(cmd)}", file=sys.stderr)
            return result.returncode
    return 0