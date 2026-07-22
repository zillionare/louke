"""Authenticated v0.14 Story read model and Scribe task endpoints."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from louke.v014.scribe_entry import ScribeEntryService, ScribeTaskError

from louke.web.auth import SESSION_COOKIE, current_user, verify_csrf_token


async def story_page(request: Request) -> HTMLResponse | JSONResponse:
    """Render the canonical Story page with its current task summary."""
    user_or_response = _require_human(request, csrf_required=False)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    run = _current_run(request)
    if run is None:
        return _error("NOT_FOUND", "no Runtime run exists", 404)
    artifact = request.app.state.v14_story_entry.artifact(run.run_id)
    if artifact is None:
        return _error("NOT_FOUND", "Story artifact does not exist", 404)
    task = _task_for_artifact(request, run.run_id)
    body = escape(artifact.body_md)
    task_text = escape(str(task.get("task_id"))) if task else "not created"
    return HTMLResponse(
        "<html><body><main id='story-page'>"
        f"<h1>Story</h1><p data-run='{escape(run.run_id)}'>"
        f"Phase: {escape(run.current_step)} · Revision: {artifact.revision}</p>"
        f"<pre data-task='{task_text}'>{body}</pre>"
        "<aside id='scribe-chat'>Scribe Chat</aside>"
        "</main></body></html>"
    )


async def current_project(request: Request) -> JSONResponse:
    """Return the current project/run and Story task read model."""
    user_or_response = _require_human(request, csrf_required=False)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    run = _current_run(request)
    if run is None:
        return _error("NOT_FOUND", "no Runtime run exists", 404)
    artifact = request.app.state.v14_story_entry.artifact(run.run_id)
    task = _task_for_artifact(request, run.run_id)
    return JSONResponse(
        {
            "project": {"project_id": request.path_params["project_id"]},
            "run": {
                "run_id": run.run_id,
                "revision": run.revision,
                "phase": run.current_step,
                "status": run.status,
            },
            "artifact": _artifact_model(artifact) if artifact else None,
            "task": _task_summary(task),
            "allowed_actions": [],
            "continue_url": f"/projects/{request.path_params['project_id']}/requirements/story",
        }
    )


async def story_artifact(request: Request) -> JSONResponse:
    """Return the persisted Story artifact without exposing write authority."""
    user_or_response = _require_human(request, csrf_required=False)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    if request.path_params["kind"] != "story":
        return _error("NOT_FOUND", "only the Story artifact is available", 404)
    artifact = request.app.state.v14_story_entry.artifact(request.path_params["run_id"])
    if artifact is None:
        return _error("NOT_FOUND", "Story artifact does not exist", 404)
    return JSONResponse(_artifact_model(artifact))


async def task_read(request: Request) -> JSONResponse:
    """Return a task bound to the requested Runtime run."""
    user_or_response = _require_human(request, csrf_required=False)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    try:
        return JSONResponse(_scribe(request).task_read(**request.path_params))
    except ScribeTaskError as exc:
        return _error(exc.code, exc.message, 409)


async def task_messages(request: Request) -> JSONResponse:
    """Return persisted Chat messages for a bound Scribe task."""
    user_or_response = _require_human(request, csrf_required=False)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    try:
        return JSONResponse(
            {"messages": _scribe(request).list_messages(**request.path_params)}
        )
    except ScribeTaskError as exc:
        return _error(exc.code, exc.message, 409)


async def task_reply(request: Request) -> JSONResponse:
    """Persist and dispatch one authenticated Human Chat reply."""
    user_or_response = _require_human(request, csrf_required=True)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    payload = await request.json()
    try:
        result = _scribe(request).reply(
            run_id=request.path_params["run_id"],
            task_id=request.path_params["task_id"],
            client_message_id=_required_string(payload, "client_message_id"),
            correlation_id=_required_string(payload, "correlation_id"),
            body=_required_string(payload, "body"),
            expected_attempt_id=_required_string(payload, "expected_attempt_id"),
            expected_artifact_revision=_required_int(
                payload, "expected_artifact_revision"
            ),
        )
    except ScribeTaskError as exc:
        return _error(exc.code, exc.message, 409)
    except ValueError as exc:
        return _error("VALIDATION_ERROR", str(exc), 400)
    return JSONResponse(result, status_code=202)


async def task_reconcile(request: Request) -> JSONResponse:
    """Reconcile a task with its existing OpenCode session."""
    user_or_response = _require_human(request, csrf_required=True)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    try:
        return JSONResponse(
            _scribe(request).reconcile(
                request.path_params["run_id"], request.path_params["task_id"]
            )
        )
    except ScribeTaskError as exc:
        return _error(exc.code, exc.message, 409)


async def task_retry(request: Request) -> JSONResponse:
    """Retry a blocked task using the server-owned workspace path."""
    user_or_response = _require_human(request, csrf_required=True)
    if isinstance(user_or_response, JSONResponse):
        return user_or_response
    try:
        result = _scribe(request).retry(
            request.path_params["run_id"],
            request.path_params["task_id"],
            str(Path(request.app.state.v14_scribe_entry.workspace_root or "")),
        )
    except ScribeTaskError as exc:
        return _error(exc.code, exc.message, 409)
    return JSONResponse(result, status_code=202)


def _scribe(request: Request) -> ScribeEntryService:
    """Return the application-owned Scribe service."""
    return request.app.state.v14_scribe_entry


def _current_run(request: Request):
    """Return the newest persisted run for the configured project."""
    runs = request.app.state.v12_run_store.list_runs()
    return runs[-1] if runs else None


def _task_for_artifact(request: Request, run_id: str) -> dict[str, Any] | None:
    """Read the task bound to a run without creating a new task."""
    return _scribe(request).task_for_run(run_id)


def _artifact_model(artifact: Any) -> dict[str, Any]:
    """Build the public Story artifact model."""
    return {
        "kind": "story",
        "path": "story.md",
        "body_md": artifact.body_md,
        "revision": artifact.revision,
        "version_token": artifact.digest,
        "digest": artifact.digest,
        "commit_sha": artifact.commit_sha,
        "locked": True,
        "readonly": True,
        "readonly_reason": "Scribe lease owns Story task scope",
    }


def _task_summary(task: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the compact current-model task summary."""
    if task is None:
        return None
    return {
        "task_id": task["task_id"],
        "attempt_id": task["active_attempt_id"],
        "session_id": task["session_id"],
        "status": task["status"],
        "connection": task["connection"],
    }


def _require_human(request: Request, *, csrf_required: bool):
    """Require a server-authenticated Human session and optional CSRF proof."""
    session = request.cookies.get(SESSION_COOKIE)
    user = current_user(request.app.state.store, session)
    if user is None:
        return _error("AUTH_REQUIRED", "login required", 401)
    if csrf_required and not verify_csrf_token(
        request.app.state.store, session, request.headers.get("x-louke-csrf")
    ):
        return _error("CSRF_INVALID", "valid session-bound CSRF token required", 403)
    return user


def _required_string(payload: dict[str, Any], field: str) -> str:
    """Return a required non-empty string field."""
    value = payload.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required")
    return value.strip()


def _required_int(payload: dict[str, Any], field: str) -> int:
    """Return a required integer field without accepting booleans."""
    value = payload.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field} must be an integer")
    return value


def _error(code: str, message: str, status: int) -> JSONResponse:
    """Return a stable API error envelope."""
    return JSONResponse({"error_code": code, "message": message}, status_code=status)
