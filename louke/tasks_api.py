"""FR-0501: FR/NFR Markdown task state toggle + persistence.

Mounted at /api/tasks. Adds an *internal* GET endpoint to read current state
+ revision (NOT listed in interfaces.md §1.2, see session note 2026-07-11 for
why). PATCH toggles via WorkspaceSecurity.write for allowlist enforcement.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from .security import WorkspaceSecurity, SecurityError, WRITABLE_BASENAMES


app = Starlette()

_VALID_TASKS = {"Valid", "Testable", "Decided"}


def _is_writable(ws_root: Path, path: Path) -> bool:
    """Return True if path matches the writable allowlist (.louke/project/**/{story,spec,acceptance}.md).

    Mirrors WorkspaceSecurity.write's allowlist check without touching disk,
    so non-design-docs return 403 before any mutation or task lookup.
    """
    rp = path.resolve(strict=False)
    try:
        rel = rp.relative_to(ws_root)
    except ValueError:
        return False
    parts = rel.parts
    if len(parts) < 5 or parts[0] != ".louke" or parts[1] != "project":
        return False
    return rel.name in WRITABLE_BASENAMES


# Match markdown task lines that look like:  "- [x] Valid" / "- [ ] Testable"
_TASK_RE = re.compile(
    r"^(\s*)-\s+\[(?P<mark>[ xX])\]\s+(?P<name>\S+)\s*$", re.MULTILINE
)


def _scan_tasks(content: str) -> dict[str, bool]:
    """Return {task_name: checked} from markdown task lines."""
    result: dict[str, bool] = {}
    for m in _TASK_RE.finditer(content):
        name = m.group("name")
        mark = m.group("mark").lower()
        result[name] = mark == "x"
    return result


def _replace_task(content: str, task_name: str, checked: bool) -> Optional[str]:
    """Return updated content (or None if task not found)."""
    new_mark = "x" if checked else " "
    pattern = re.compile(
        rf"^(\s*)-\s+\[[ xX]\]\s+{re.escape(task_name)}\s*$",
        re.MULTILINE,
    )
    if pattern.search(content) is None:
        return None
    return pattern.sub(
        lambda m: f"{m.group(1)}- [{new_mark}] {task_name}",
        content,
        count=1,
    )


async def get_task_state(request: Request) -> JSONResponse:
    """GET /api/tasks/{fr_id}?document_path=<rel> → {fr_id, document_path, tasks, revision}.

    Reads current markdown task state + revision. Internal endpoint (not in
    interfaces.md §1.2); required for PATCH optimistic-concurrency flow.

    Raises 400 if document_path missing; 403 on SecurityError (path/symlink).
    """
    fr_id = request.path_params["fr_id"]
    doc_path = request.query_params.get("document_path", "")
    if not doc_path:
        return JSONResponse(
            {"error_code": "VALIDATION_ERROR", "message": "document_path required"},
            status_code=400,
        )
    ws = Path.cwd().resolve()
    sec = WorkspaceSecurity(ws)
    try:
        fc = sec.read(Path(doc_path))
    except SecurityError as e:
        return JSONResponse(
            {"error_code": e.code, "message": e.message}, status_code=403
        )
    return JSONResponse(
        {
            "fr_id": fr_id,
            "document_path": doc_path,
            "tasks": _scan_tasks(fc.content),
            "revision": fc.revision,
        }
    )


async def patch_task(request: Request) -> JSONResponse:
    """PATCH /api/tasks/{fr_id} {document_path, task, checked, revision?} → updated state.

    Toggles a Valid/Testable/Decided markdown task line and persists via
    WorkspaceSecurity.write (NFR-0201 allowlist + revision check).

    Returns 400 on invalid body, 403 on non-writable / outside-workspace,
    404 if task line absent, 409 on revision conflict.
    """
    fr_id = request.path_params["fr_id"]
    body = await request.json()
    doc_path = body.get("document_path", "")
    task = body.get("task", "")
    checked = bool(body.get("checked", False))
    revision = body.get("revision")
    if not doc_path or task not in _VALID_TASKS:
        return JSONResponse(
            {
                "error_code": "VALIDATION_ERROR",
                "message": "document_path and valid task required",
            },
            status_code=400,
        )
    ws = Path.cwd().resolve()
    sec = WorkspaceSecurity(ws)
    try:
        fc = sec.read(Path(doc_path))
    except SecurityError as e:
        return JSONResponse(
            {"error_code": e.code, "message": e.message}, status_code=403
        )
    # Writable allowlist check before task lookup: non-design-docs are
    # FILE_READ_ONLY regardless of what's inside them.
    if not _is_writable(ws, fc.path):
        return JSONResponse(
            {
                "error_code": "FILE_READ_ONLY",
                "message": f"{doc_path} not in writable allowlist",
            },
            status_code=403,
        )
    new_content = _replace_task(fc.content, task, checked)
    if new_content is None:
        return JSONResponse(
            {
                "error_code": "TASK_NOT_FOUND",
                "message": f"task {task} not found in {doc_path}",
            },
            status_code=404,
        )
    try:
        new_rev = sec.write(Path(doc_path), new_content, revision=revision)
    except SecurityError as e:
        status = 409 if e.code == "REVISION_CONFLICT" else 403
        return JSONResponse(
            {"error_code": e.code, "message": e.message}, status_code=status
        )
    return JSONResponse(
        {
            "fr_id": fr_id,
            "document_path": doc_path,
            "tasks": _scan_tasks(new_content),
            "revision": new_rev,
        }
    )


app.add_route("/api/tasks/{fr_id}", get_task_state, methods=["GET"])
app.add_route("/api/tasks/{fr_id}", patch_task, methods=["PATCH"])
