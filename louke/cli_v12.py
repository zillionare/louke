"""v0.12 user-facing CLI commands (B8).

Each command calls the v0.12 sub-app endpoint via HTTP and prints JSON or
human-readable text to stdout. Uses LOUKE_API_BASE env var (default
http://127.0.0.1:8000) for the server URL.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


_DEFAULT_API_BASE = "http://127.0.0.1:8000"


def _api_base() -> str:
    return os.environ.get("LOUKE_API_BASE", _DEFAULT_API_BASE).rstrip("/")


def _request(method: str, path: str, *, body=None):
    url = f"{_api_base()}{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=10) as resp:
        payload = resp.read().decode("utf-8")
        if not payload:
            return None
        return json.loads(payload)


def _print(obj):
    if obj is None:
        return
    print(json.dumps(obj, indent=2, sort_keys=True))


def cmd_project_list(args):
    status = args.status or "active"
    _print(_request("GET", f"/api/projects/{status}"))
    return 0


def cmd_project_show(args):
    _print(_request("GET", f"/api/projects/{args.project_id}"))
    return 0


def cmd_gate_approve(args):
    body = {"actor": args.actor or "cli", "verdict": "approve"}
    if args.reason:
        body["reason"] = args.reason
    _print(_request("POST", f"/api/gates/{args.gate_id}/decisions", body=body))
    return 0


def cmd_gate_reject(args):
    if not args.reason:
        print("lk: --reason is required for reject", file=sys.stderr)
        raise SystemExit(1)
    body = {"actor": args.actor or "cli", "verdict": "reject", "reason": args.reason}
    _print(_request("POST", f"/api/gates/{args.gate_id}/decisions", body=body))
    return 0


def cmd_workflow_graph(args):
    _print(_request("GET", f"/api/projects/{args.run_id}/graph"))
    return 0


def cmd_migrate_preview(args):
    from urllib.parse import quote

    wp = quote(args.workspace_path, safe="")
    _print(_request("GET", f"/api/migration/preview?workspace_path={wp}"))
    return 0


def register_project(sub):
    p = sub.add_parser("project", help="Manage v0.12 projects")
    pp = p.add_subparsers(dest="command", required=True)
    pl = pp.add_parser("list", help="List projects")
    pl.add_argument(
        "--status", choices=["active", "history", "backlog"], default="active"
    )
    pl.set_defaults(func=cmd_project_list)
    ps = pp.add_parser("show", help="Show project detail")
    ps.add_argument("project_id")
    ps.set_defaults(func=cmd_project_show)


def register_gate(sub):
    p = sub.add_parser("gate", help="Manage v0.12 gates")
    pp = p.add_subparsers(dest="command", required=True)
    pa = pp.add_parser("approve", help="Approve a gate")
    pa.add_argument("gate_id")
    pa.add_argument("--actor", default="cli")
    pa.add_argument("--reason", default=None)
    pa.set_defaults(func=cmd_gate_approve)
    pr = pp.add_parser("reject", help="Reject a gate (requires --reason)")
    pr.add_argument("gate_id")
    pr.add_argument("--actor", default="cli")
    pr.add_argument("--reason")
    pr.set_defaults(func=cmd_gate_reject)


def register_workflow(sub):
    p = sub.add_parser("workflow", help="Workflow graph & state")
    pp = p.add_subparsers(dest="command", required=True)
    pg = pp.add_parser("graph", help="Show workflow graph for a run")
    pg.add_argument("run_id")
    pg.set_defaults(func=cmd_workflow_graph)


def register_migrate(sub):
    p = sub.add_parser("migrate", help="Legacy workspace adoption")
    pp = p.add_subparsers(dest="command", required=True)
    ppv = pp.add_parser("preview", help="Preview migration")
    ppv.add_argument("workspace_path")
    ppv.set_defaults(func=cmd_migrate_preview)


def register_subcommands(sub):
    register_project(sub)
    register_gate(sub)
    register_workflow(sub)
    register_migrate(sub)


def dispatch(args):
    if not hasattr(args, "func"):
        return 1
    try:
        return args.func(args)
    except urllib.error.HTTPError as e:
        try:
            raw = e.read()
            body_text = (
                raw.decode("utf-8", errors="replace")
                if isinstance(raw, bytes)
                else str(raw)
            )
        except Exception:
            body_text = ""
        print(f"lk: HTTP {e.code}: {body_text}", file=sys.stderr)
        raise SystemExit(2)
    except urllib.error.URLError as e:
        print(
            f"lk: cannot reach louke server at {_api_base()}: {e.reason}",
            file=sys.stderr,
        )
        raise SystemExit(3)
