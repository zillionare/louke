"""Tests for v0.12 CLI commands (B8)."""

from __future__ import annotations

import argparse
import json
from unittest.mock import patch

import pytest

from louke import cli_v12


def _run(argv: list[str]) -> int:
    """Build a parser, parse argv, dispatch to handler."""
    parser = argparse.ArgumentParser(prog="lk")
    sub = parser.add_subparsers(dest="cmd")
    cli_v12.register_subcommands(sub)
    args = parser.parse_args(argv)
    return cli_v12.dispatch(args)


def test_project_list_calls_active_endpoint(capsys):
    """`lk project list` GETs /api/projects/active."""
    with patch.object(cli_v12, "_request", return_value={"items": []}) as m:
        rc = _run(["project", "list"])
    assert rc == 0
    assert m.call_args.args[0] == "GET"
    assert m.call_args.args[1] == "/api/projects/active"
    captured = capsys.readouterr()
    assert '"items"' in captured.out


def test_project_list_with_history(capsys):
    with patch.object(cli_v12, "_request", return_value={"items": []}) as m:
        _run(["project", "list", "--status", "history"])
    assert m.call_args.args[1] == "/api/projects/history"


def test_project_show_calls_get_with_id(capsys):
    with patch.object(cli_v12, "_request", return_value={"project_id": "p_123"}) as m:
        _run(["project", "show", "p_123"])
    assert m.call_args.args == ("GET", "/api/projects/p_123")
    assert m.call_args.kwargs == {}


def test_gate_approve_posts_decision(capsys):
    with patch.object(cli_v12, "_request", return_value={"verdict": "approve"}) as m:
        rc = _run(["gate", "approve", "g_1"])
    assert rc == 0
    assert m.call_args.args == ("POST", "/api/gates/g_1/decisions")
    assert m.call_args.kwargs["body"] == {"actor": "cli", "verdict": "approve"}


def test_gate_reject_requires_reason(capsys):
    with patch.object(cli_v12, "_request") as m:
        with pytest.raises(SystemExit) as e:
            _run(["gate", "reject", "g_1"])
    assert e.value.code == 1
    assert m.called is False
    captured = capsys.readouterr()
    assert "--reason is required" in captured.err


def test_workflow_graph_calls_project_endpoint(capsys):
    with patch.object(cli_v12, "_request", return_value={"nodes": [], "edges": []}) as m:
        _run(["workflow", "graph", "run_1"])
    assert m.call_args.args == ("GET", "/api/projects/run_1/graph")


def test_migrate_preview_calls_endpoint(capsys):
    with patch.object(cli_v12, "_request", return_value={"recommended_mode": "local"}) as m:
        _run(["migrate", "preview", "/tmp/old workspace"])  # path with space
    assert m.call_args.args[0] == "GET"
    assert m.call_args.args[1].startswith("/api/migration/preview?workspace_path=")
    # Verify the space was URL-encoded
    assert "old%20workspace" in m.call_args.args[1] or "old+workspace" in m.call_args.args[1]


def test_request_http_error_exits_2(capsys):
    import urllib.error

    def boom(*a, **kw):
        raise urllib.error.HTTPError("http://x", 500, "server", {}, b"boom")

    with patch.object(cli_v12, "_request", side_effect=boom):
        with pytest.raises(SystemExit) as e:
            _run(["project", "list"])
    assert e.value.code == 2
    captured = capsys.readouterr()
    assert "HTTP 500" in captured.err


def test_request_unreachable_exits_3(capsys):
    import urllib.error

    def boom(*a, **kw):
        raise urllib.error.URLError("nope")

    with patch.object(cli_v12, "_request", side_effect=boom):
        with pytest.raises(SystemExit) as e:
            _run(["project", "list"])
    assert e.value.code == 3
    captured = capsys.readouterr()
    assert "cannot reach louke server" in captured.err
