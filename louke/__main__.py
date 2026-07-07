"""lk CLI entry point.

Usage:
    lk <command> [options]               # user-facing commands
    lk agent <name> <subcommand> [options]  # agent commands

User-facing commands:
    lk init <name|path>         Initialize/adopt louke project skeleton
    lk models list|doctor|bind|unbind  Manage abstract model bindings
    lk board opencode|status    Generate IDE agent boards
    lk upgrade                  Upgrade louke via pip
    lk version                  Print version (also: lk --version, lk -v)
    lk help                     Print help (also: lk --help, lk -h)

Agent commands:
    lk agent scout identity-check --repo owner/repo
    lk agent sage quote-check --spec v0.1-001-init
    lk agent warden foundation-check --repo owner/repo --version v0.1 --spec-id v0.1-001-init
    lk agent lex verify-acceptance --spec v0.1-001-init
    lk agent archer ci-scan --spec v0.1-001-init

设计:
- 用户面命令走 argparse subparser，得到完整 Namespace 后调用模块 run()。
- agent 子命令 lk agent <name> <cmd> 通过 agent_main 路由。
- __main__ 预先拦截 --version/-v/--help/-h/version/help/upgrade，避免 argparse subparser required 冲突。
"""
import argparse
import sys
from pathlib import Path

from . import __version__
from . import init as init_cmd
from . import models as models_cmd
from . import board as board_cmd
from . import agent as agent_main


USER_COMMANDS = {
    'init': init_cmd,
    'models': models_cmd,
    'board': board_cmd,
}


def build_parser():
    parser = argparse.ArgumentParser(prog='lk', add_help=False)
    parser.add_argument('--help', '-h', action='store_true')
    parser.add_argument('--version', '-v', action='store_true')
    subparsers = parser.add_subparsers(dest='command', metavar='<command>')
    for name, module in USER_COMMANDS.items():
        sub = subparsers.add_parser(name, add_help=False)
        if hasattr(module, 'register'):
            module.register(sub)
    subparsers.add_parser('version', add_help=False)
    subparsers.add_parser('help', add_help=False)
    subparsers.add_parser('upgrade', add_help=False)
    agent_parser = subparsers.add_parser('agent', add_help=False)
    if hasattr(agent_main, 'register'):
        agent_main.register(agent_parser)
    return parser


def _do_upgrade(extra_args):
    """lk upgrade — find the venv that owns lk and pip install --upgrade louke there.

    支持的 louke-level 选项 (其余原样转发给 pip):
      --index URL        指定 PyPI 源 (e.g. https://test.pypi.org/simple/)
                         内部翻译为 pip 的 --index-url
      --pre              允许 pre-release / dev 版本
      --dry-run          显示将要执行的 pip 命令, 不实际执行
    """
    import subprocess, os

    # 0. 解析 louke-level 选项, 剩余原样转 pip
    parser = argparse.ArgumentParser(prog='lk upgrade', add_help=True)
    parser.add_argument('--index', metavar='URL',
                        help='指定 PyPI 源 URL (e.g. https://test.pypi.org/simple/)')
    parser.add_argument('--pre', action='store_true',
                        help='允许 pre-release / dev 版本')
    parser.add_argument('--dry-run', action='store_true',
                        help='显示将要执行的 pip 命令, 不实际执行')
    opts, rest = parser.parse_known_args(extra_args)

    # 1. Find the venv: lk 入口脚本 shebang 指向 venv python
    lk_bin = os.path.realpath(sys.argv[0])
    # /Users/.../.local/bin/lk -> symlink -> ~/.louke/venv/bin/lk
    venv_bin = os.path.dirname(lk_bin)  # ~/.louke/venv/bin
    venv_pip = os.path.join(venv_bin, 'pip')
    venv_python = os.path.join(venv_bin, 'python3')

    if not os.path.isfile(venv_pip):
        print(f'lk upgrade: cannot find venv pip at {venv_pip}', file=sys.stderr)
        print('hint: run install.sh again to recreate the venv', file=sys.stderr)
        return 1

    cmd = [venv_python, '-m', 'pip', 'install', '--upgrade', 'louke']
    if opts.index:
        cmd.extend(['--index-url', opts.index])
    if opts.pre:
        cmd.append('--pre')
    cmd.extend(rest)

    print(f'Running: {" ".join(cmd)}')
    if opts.dry_run:
        return 0
    result = subprocess.run(cmd)
    if result.returncode == 0:
        # Verify
        try:
            out = subprocess.check_output([venv_python, '-c', 'from louke import __version__; print(__version__)'], text=True).strip()
            print(f'✓ louke upgraded to {out}')
        except Exception:
            pass
    return result.returncode


def build_command_parser(module, prog):
    """Build a standalone parser for a user-facing command."""
    parser = argparse.ArgumentParser(prog=prog, add_help=True)
    if hasattr(module, 'register'):
        module.register(parser)
    return parser


def main(argv=None):
    raw = list(argv if argv is not None else sys.argv[1:])

    if not raw or raw[0] in ('--version', '-v', 'version'):
        print(f'lk {__version__}')
        return 0
    if raw[0] in ('--help', '-h', 'help'):
        print_help_text()
        return 0
    if raw[0] == 'upgrade':
        return _do_upgrade(raw[1:])
    if raw[0] == 'agent':
        # Re-parse with help parser so agent subparser handles 'agent scout xxx'
        parser = build_parser()
        try:
            args = parser.parse_args(raw)
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1
        return agent_main.run(args)
    if raw[0] == 'discuss':
        return _cmd_discuss(raw[1:])
    if raw[0] in USER_COMMANDS:
        module = USER_COMMANDS[raw[0]]
        parser = build_command_parser(module, f'lk {raw[0]}')
        try:
            args = parser.parse_args(raw[1:])
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1
        try:
            return module.run(args) or 0
        except Exception as e:
            print(f"lk {raw[0]}: {e}", file=sys.stderr)
            return 1

    parser = build_parser()
    parser.print_help()
    return 0


def _dispatch_agent(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    return agent_main.run(args)


def print_help_text():
    print(f'lk {__version__} — louke CLI')
    print()
    print('User-facing commands:')
    print('  lk init <name|path>         Initialize/adopt louke project skeleton')
    print('  lk models list|doctor|bind|unbind  Manage abstract model bindings')
    print('  lk board opencode|status    Generate IDE agent boards')
    print('  lk upgrade [--index URL] [--pre] [--dry-run]  Upgrade louke via pip')
    print('  lk version                  Print version')
    print('  lk help                     Print this help')
    print()
    print('Agent commands:')
    print('  lk agent <name> <cmd> [opts]')
    print('    scout      identity-check, foundation, invite-owner, commit-foundation')
    print('    sage       quote-check, commit-spec, create-issues, record-lock')
    print('    warden     foundation-check')
    print('    lex        verify-acceptance, verify-issue, verify-project, quote-check')
    print('    archer     ci-scan, check-acs, commit-design, validate-test-plan, validate-arch')
    print('    keeper     gate, regression')
    print('    judge      security-audit, quick-scan')
    print('    prism      review, test-patterns, security-quick-scan, code-quality')
    print('    devon      run-tests, commit-rgr')
    print('    shield     run-e2e, commit-e2e, scaffold')
    print('    librarian  distill, lint, rebuild-index, compact, rewrite')
    print('    maestro    status, advance, regress, escalate')
    print()
    print('Inline discussion (v0.7-003):')
    print('  lk discuss query --file <path> [--initiator <a>] [--blocker <a>] [--status <s>]')
    print('  lk discuss start --file <path> --anchor-line <N> --speaker <a> <message>')
    print('  lk discuss reply --file <path> --thread-id <id> --anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> --speaker <a> <message>')
    print('  lk discuss edit --file <path> --thread-id <id> --anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> --depth <N> --speaker <a> <new>')
    print('  lk discuss set-status --file <path> --thread-id <id> --anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> --status <resolved|reopen>')
    print()
    print('Run lk <command> --help for detailed usage.')


def _build_discuss_parser() -> argparse.ArgumentParser:
    """FR-0030: lk discuss 5 子命令 (query/start/reply/edit/set-status)."""
    parser = argparse.ArgumentParser(prog='lk discuss', add_help=True)
    sub = parser.add_subparsers(dest='discuss_command', required=True, metavar='<command>')

    # 1. query
    p_query = sub.add_parser('query', help='列出 thread (含 5 元组定位字段)')
    p_query.add_argument('--file', required=True, help='spec.md 路径')
    p_query.add_argument('--initiator', help='按发起人过滤 (e.g. Sage)')
    p_query.add_argument('--blocker', help='按 blocker 过滤 (e.g. Aaron)')
    p_query.add_argument('--status', choices=['open', 'resolved', 'reopen'],
                        help='按状态过滤')

    # 2. start
    p_start = sub.add_parser('start', help='创建新 thread (插在 anchor_line 后)')
    p_start.add_argument('--file', required=True)
    p_start.add_argument('--anchor-line', type=int, required=True, help='被评论内容行号')
    p_start.add_argument('--speaker', required=True, help='发起人 (e.g. Sage)')
    p_start.add_argument('message', help='评论内容 (单行)')

    # 3. reply
    p_reply = sub.add_parser('reply', help='追加回复到 thread 末尾')
    p_reply.add_argument('--file', required=True)
    p_reply.add_argument('--thread-id', required=True, help='如 T-001')
    p_reply.add_argument('--anchor-line', type=int, required=True)
    p_reply.add_argument('--anchor-text', required=True)
    p_reply.add_argument('--root-line', type=int, required=True)
    p_reply.add_argument('--root-text', required=True)
    p_reply.add_argument('--speaker', required=True)
    p_reply.add_argument('message')

    # 4. edit
    p_edit = sub.add_parser('edit', help='修改自己某条评论 (仅原作者)')
    p_edit.add_argument('--file', required=True)
    p_edit.add_argument('--thread-id', required=True)
    p_edit.add_argument('--anchor-line', type=int, required=True)
    p_edit.add_argument('--anchor-text', required=True)
    p_edit.add_argument('--root-line', type=int, required=True)
    p_edit.add_argument('--root-text', required=True)
    p_edit.add_argument('--depth', type=int, required=True, help='评论的嵌套深度 (1=根评论)')
    p_edit.add_argument('--speaker', required=True, help='原评论作者 (验证 = 发起人)')
    p_edit.add_argument('new_body', help='新评论内容')

    # 5. set-status
    p_status = sub.add_parser('set-status', help='修改 thread 状态 (RESOLVED 仅 initiator)')
    p_status.add_argument('--file', required=True)
    p_status.add_argument('--thread-id', required=True)
    p_status.add_argument('--anchor-line', type=int, required=True)
    p_status.add_argument('--anchor-text', required=True)
    p_status.add_argument('--root-line', type=int, required=True)
    p_status.add_argument('--root-text', required=True)
    p_status.add_argument('--status', required=True, choices=['resolved', 'reopen'])
    p_status.add_argument('--operator', required=True,
                          help='操作者 (验证 = initiator 才对 RESOLVED 有效)')

    return parser


def _cmd_discuss(argv: list) -> int:
    """lk discuss 5 子命令 dispatcher."""
    from ._tools import discuss
    parser = _build_discuss_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    try:
        if args.discuss_command == 'query':
            result = discuss.DiscussParser().parse_file(Path(args.file))
            threads = result.threads
            # Apply filters
            if args.initiator:
                threads = [t for t in threads if t.initiator == args.initiator.lower()]
            if args.status:
                threads = [t for t in threads if t.status == args.status]
            if args.blocker:
                # QoderWork P2-2 3 类别
                target = args.blocker.lower()
                open_threads = [t for t in threads if t.status == 'open']
                # unanswered: 我起的 + 无回复
                unanswered = [t for t in open_threads if t.initiator == target and t.reply_count == 0]
                # unresolved: 我起的 + 最后一层不是我也不是 resolved (这里只看 reply_count 和 status)
                # (简化: reply_count > 0 但 status != resolved)
                unresolved = [t for t in open_threads if t.initiator == target and t.reply_count > 0]
                # awaiting_my_reply: @mentioned me
                awaiting = [t for t in open_threads if target in t.mentioned_agents]
                threads = unanswered + unresolved + awaiting
            import json
            out = []
            for t in threads:
                out.append({
                    'thread_id': t.thread_id,
                    'initiator': t.initiator,
                    'status': t.status,
                    'last_speaker': t.last_speaker,
                    'reply_count': t.reply_count,
                    'snippet': t.snippet,
                    'mentioned_agents': t.mentioned_agents,
                    'total_lines': t.total_lines,
                    'anchor_line': t.anchor_line,
                    'anchor_text': t.anchor_text,
                    'root_line': t.root_line,
                    'root_text': t.root_text,
                })
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0

        elif args.discuss_command == 'start':
            p = discuss.DiscussParser()
            t = p.add_thread(Path(args.file), anchor_line=args.anchor_line,
                             initiator=args.speaker, body=args.message)
            print(f"created {t.thread_id} ({t.initiator}) at root_line={t.root_line}")
            return 0

        elif args.discuss_command == 'reply':
            p = discuss.DiscussParser()
            p.add_reply(Path(args.file), thread_id=args.thread_id,
                        body=args.message, speaker=args.speaker,
                        anchor_line=args.anchor_line, anchor_text=args.anchor_text,
                        root_line=args.root_line, root_text=args.root_text)
            print(f"reply added to {args.thread_id}")
            return 0

        elif args.discuss_command == 'edit':
            p = discuss.DiscussParser()
            p.edit_comment(Path(args.file), thread_id=args.thread_id,
                          depth=args.depth, speaker=args.speaker,
                          new_body=args.new_body,
                          anchor_line=args.anchor_line, anchor_text=args.anchor_text,
                          root_line=args.root_line, root_text=args.root_text)
            print(f"comment at depth {args.depth} in {args.thread_id} edited")
            return 0

        elif args.discuss_command == 'set-status':
            p = discuss.DiscussParser()
            p.set_status(Path(args.file), thread_id=args.thread_id,
                         new_status=args.status, operator_speaker=args.operator,
                         anchor_line=args.anchor_line, anchor_text=args.anchor_text,
                         root_line=args.root_line, root_text=args.root_text)
            print(f"{args.thread_id} status -> {args.status}")
            return 0

    except (FileNotFoundError, ValueError, PermissionError) as e:
        print(f"lk discuss: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
