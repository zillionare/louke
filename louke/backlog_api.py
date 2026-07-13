"""FR-0601: local story backlog API.

Mounted at /api/backlog. Persists entries to .louke/project/backlog.json
(architecture §2.3 canonical path).

The 'start_development' delete action wires the existing Louke workflow
entry - for unit tests we just simulate 'workflow accepted' (status=removed);
real wiring to `lk agent maestro status` is left to M-DEV Batch 4 (FR-0201).
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from .paths import canonical_root


app = Starlette()

_lock = threading.RLock()


def _store_path() -> Path:
    p = canonical_root() / "project" / "backlog.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load() -> dict:
    p = _store_path()
    if not p.exists():
        return {"entries": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"entries": []}


def _save(data: dict) -> None:
    p = _store_path()
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    import os

    os.replace(tmp, p)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _entry_dict(e: dict) -> dict:
    return {
        "id": e["id"],
        "story": e["story"],
        "status": e["status"],
        "created_at": e["created_at"],
        "error": e.get("error"),
    }


async def list_backlog(request: Request):
    with _lock:
        data = _load()
    return JSONResponse({"entries": [_entry_dict(e) for e in data["entries"]]})


async def create_entry(request: Request):
    body = await request.json()
    story = body.get("story", "")
    if not story or not str(story).strip():
        return JSONResponse(
            {"error_code": "VALIDATION_ERROR", "message": "story required"},
            status_code=400,
        )
    with _lock:
        data = _load()
        entry = {
            "id": _new_id(),
            "story": story,
            "status": "pending",
            "created_at": _now_iso(),
        }
        data["entries"].append(entry)
        _save(data)
    return JSONResponse(_entry_dict(entry), status_code=201)


async def delete_entry(request: Request):
    body = await request.json()
    target_id = body.get("id", "")
    action = body.get("action", "")
    if not target_id:
        return JSONResponse(
            {"error_code": "VALIDATION_ERROR", "message": "id required"},
            status_code=400,
        )
    if action != "start_development":
        return JSONResponse(
            {
                "error_code": "SELECTION_REQUIRED",
                "message": "action must be 'start_development'",
            },
            status_code=400,
        )
    with _lock:
        data = _load()
        idx = next(
            (i for i, e in enumerate(data["entries"]) if e["id"] == target_id), None
        )
        if idx is None:
            return JSONResponse(
                {
                    "error_code": "BACKLOG_NOT_FOUND",
                    "message": f"unknown id {target_id}",
                },
                status_code=404,
            )
        entry = data["entries"][idx]
        entry["status"] = "dispatching"
        # Simulate workflow accepted -> remove
        data["entries"].pop(idx)
        _save(data)
    return JSONResponse(
        {
            "id": target_id,
            "status": "removed",
            "workflow_started": True,
        }
    )


app.add_route("/api/backlog", list_backlog, methods=["GET"])
app.add_route("/api/backlog", create_entry, methods=["POST"])
app.add_route("/api/backlog", delete_entry, methods=["DELETE"])
