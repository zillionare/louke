"""Integration tests for v0.12 CLI commands hooked into louke.__main__ (B8)."""

from __future__ import annotations

import argparse


def test_cli_v12_registers_subcommands():
    """Verify the 4 top-level v0.12 commands are registered after import."""
    from louke.__main__ import build_parser

    parser = build_parser()
    # Find which top-level commands exist
    sub_actions = []
    for action in parser._subparsers._actions:
        if isinstance(action, argparse._SubParsersAction):
            sub_actions = list(action.choices.keys())
    for name in ("project", "gate", "workflow", "migrate"):
        assert name in sub_actions, f"{name} not registered"


def test_cli_v12_invokes_dispatch(capsys, monkeypatch):
    """CLI dispatch routes project list to cli_v12 via mocked _request."""
    from louke import cli_v12, __main__

    monkeypatch.setattr(cli_v12, "_request", lambda *a, **kw: {"items": []})
    # Call the dispatcher the same way __main__ does
    parser = __main__.build_parser()
    args = parser.parse_args(["project", "list"])
    rc = cli_v12.dispatch(args)
    assert rc == 0
