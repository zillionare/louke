"""``/projects/{project_id}/gates`` page sub-app: gate list, detail and decide (B3b).

Single inline-HTML page (no Jinja2). Lists all gates for a project's run,
renders a single gate's detail (state, bound digest, expected revision, allowed
actions) and accepts an approve/reject form that posts to the upstream
``/api/gates/{gate_id}/decisions`` endpoint.

For ``requirements_approval`` and ``m_lock`` gates the detail page shows two
clearly labeled sections (AC-FR1901-03). When the gate is stale or has open
discussions, the approve button is disabled and a blocker text is shown.

Upstream HTTP calls go through module-level seams (``_fetch_*`` / ``_post_*``)
so tests can patch them without a live server, mirroring ``/projects``.

Routes (relative to the mount path ``/projects/{project_id}/gates``):

    GET  /                         - list gates for the project's run.
    GET  /{gate_id}                - render the gate detail page.
    POST /{gate_id}/decide         - submit a decision and redirect or re-render.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

#: Attribute on ``app.state`` holding the upstream API base URL.
_API_BASE_ATTR: str = "api_base"

#: Default principal used for page-submitted decisions when no auth context is
#: available. The upstream gate service requires a host-authenticated human
#: principal; the page forwards this fixed principal so the API can enforce
#: authentication in a later milestone.
_DEFAULT_PRINCIPAL: dict[str, str] = {"kind": "human", "id": "web-user"}


def create_app(api_base: str = "") -> Starlette:
    """Return a self-contained Starlette sub-app for the gates page.

    Args:
        api_base: Base URL for upstream API calls (e.g. ``"http://testserver"``).
            Empty string means same-origin.

    Returns:
        A Starlette application whose routes are relative to
        ``/projects/{project_id}/gates``.
    """
    app = Starlette(routes=_routes())
    app.state.api_base = api_base
    return app


def _routes() -> list[Route]:
    """Return the routes for the gates page sub-app.

    Routes include the full ``/projects/{project_id}/gates`` prefix because
    ``project_id`` is a path parameter that cannot live in a Starlette ``Mount``
    path. B3c will register this sub-app directly in ``app.py``.
    """
    return [
        Route("/projects/{project_id}/gates", endpoint=gates_index),
        Route("/projects/{project_id}/gates/{gate_id}", endpoint=gate_detail),
        Route(
            "/projects/{project_id}/gates/{gate_id}/decide",
            endpoint=gate_decide,
            methods=["POST"],
        ),
    ]


# -- upstream seams ----------------------------------------------------------


async def _fetch_project(api_base: str, project_id: str) -> dict[str, Any]:
    """Fetch a single project from ``GET {api_base}/api/projects/{id}``.

    Raises:
        httpx.HTTPError: if the upstream call fails (including 404).
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_base}/api/projects/{project_id}")
        resp.raise_for_status()
        return dict(resp.json())


async def _fetch_gates(api_base: str, run_id: str) -> list[dict[str, Any]]:
    """Fetch gates for a run from ``GET {api_base}/api/gates/runs/{run_id}/gates``.

    Raises:
        httpx.HTTPError: if the upstream call fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_base}/api/gates/runs/{run_id}/gates")
        resp.raise_for_status()
        return list(resp.json().get("items", []))


async def _fetch_gate(api_base: str, gate_id: str) -> dict[str, Any]:
    """Fetch a single gate from ``GET {api_base}/api/gates/{gate_id}``.

    Raises:
        httpx.HTTPError: if the upstream call fails (including 404).
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_base}/api/gates/{gate_id}")
        resp.raise_for_status()
        return dict(resp.json())


async def _post_decision(
    api_base: str,
    gate_id: str,
    *,
    run_id: str,
    decision: str,
    bound_digest: str,
    expected_revision: int,
    principal: dict[str, str],
    reason: str | None = None,
) -> dict[str, Any]:
    """POST a gate decision to ``{api_base}/api/gates/{gate_id}/decisions``.

    Raises:
        httpx.HTTPError: if the upstream call fails (4xx/5xx).
    """
    payload: dict[str, Any] = {
        "run_id": run_id,
        "decision": decision,
        "bound_digest": bound_digest,
        "expected_revision": expected_revision,
        "principal": principal,
    }
    if reason:
        payload["reason"] = reason
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{api_base}/api/gates/{gate_id}/decisions", json=payload
        )
        resp.raise_for_status()
        return dict(resp.json())


# -- helpers -----------------------------------------------------------------


def _api_base(request: Request) -> str:
    """Return the upstream API base URL stored on ``app.state``."""
    return str(getattr(request.app.state, _API_BASE_ATTR, ""))


def _parse_form(body: bytes) -> dict[str, str]:
    """Parse a urlencoded form body into a flat ``{field: value}`` dict.

    Avoids python-multipart; we only handle application/x-www-form-urlencoded.
    """
    pairs = parse_qs(body.decode("utf-8", errors="replace"))
    return {key: (vals[0] if vals else "") for key, vals in pairs.items()}


def _esc(text: Any) -> str:
    """Return an HTML-escaped version of ``text``."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _truncate(text: str, max_len: int = 12) -> str:
    """Return ``text`` truncated to ``max_len`` chars with a trailing ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


# -- endpoints ---------------------------------------------------------------


async def gates_index(request: Request) -> Response:
    """GET /: render the gates list for the project's run."""
    api_base = _api_base(request)
    project_id = request.path_params["project_id"]
    try:
        project = await _fetch_project(api_base, project_id)
    except Exception as exc:
        return HTMLResponse(_render_not_found(project_id, str(exc)))
    run_id = str(project.get("run_id", ""))
    gates, error = await _safe_fetch_gates(api_base, run_id)
    return HTMLResponse(_render_index(project_id, project, gates, error=error))


async def _safe_fetch_gates(
    api_base: str, run_id: str
) -> tuple[list[dict[str, Any]], str]:
    """Return ``(gates, error)`` from the gates list call, never raising."""
    try:
        return await _fetch_gates(api_base, run_id), ""
    except Exception as exc:
        return [], str(exc)


async def gate_detail(request: Request) -> Response:
    """GET /{gate_id}: render the gate detail page with the approve/reject form."""
    api_base = _api_base(request)
    project_id = request.path_params["project_id"]
    gate_id = request.path_params["gate_id"]
    try:
        project = await _fetch_project(api_base, project_id)
    except Exception as exc:
        return HTMLResponse(_render_not_found(project_id, str(exc)))
    try:
        gate = await _fetch_gate(api_base, gate_id)
    except Exception as exc:
        return HTMLResponse(
            _render_detail(project_id, project, gate=None, error=str(exc))
        )
    return HTMLResponse(_render_detail(project_id, project, gate=gate, error=""))


async def gate_decide(request: Request) -> Response:
    """POST /{gate_id}/decide: submit a decision and redirect or re-render."""
    api_base = _api_base(request)
    project_id = request.path_params["project_id"]
    gate_id = request.path_params["gate_id"]
    form = _parse_form(await request.body())
    verdict = form.get("verdict", "")
    reason = form.get("reason", "")

    if verdict == "reject" and not reason.strip():
        return HTMLResponse(
            _render_decide_error(project_id, gate_id, "reject decision requires a reason"),
        )

    try:
        project = await _fetch_project(api_base, project_id)
        gate = await _fetch_gate(api_base, gate_id)
    except Exception as exc:
        return HTMLResponse(
            _render_decide_error(project_id, gate_id, str(exc)),
        )

    try:
        await _post_decision(
            api_base,
            gate_id,
            run_id=str(gate.get("run_id", "")),
            decision=verdict,
            bound_digest=str(gate.get("bound_digest", "")),
            expected_revision=int(gate.get("expected_revision", 0)),
            principal=_DEFAULT_PRINCIPAL,
            reason=reason or None,
        )
    except Exception as exc:
        return HTMLResponse(
            _render_detail(project_id, project, gate=gate, error=str(exc)),
        )

    return RedirectResponse(
        url=f"/projects/{project_id}/gates/{gate_id}", status_code=303
    )


# -- HTML renderers ----------------------------------------------------------


_PAGE_STYLE = """\
    body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 24px; color: #111; }
    h1 { font-size: 24px; } h2 { font-size: 18px; margin-top: 24px; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; margin: 8px 0; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 6px; background: #f3f4f6; font-size: 12px; }
    .badge-waiting_for_human { background: #fef3c7; color: #92400e; }
    .badge-approved { background: #dcfce7; color: #166534; }
    .badge-rejected { background: #fee2e2; color: #991b1b; }
    .badge-stale { background: #fee2e2; color: #991b1b; }
    .muted { color: #6b7280; }
    .error { color: #b91c1c; margin: 12px 0; }
    .blocker { color: #b45309; margin: 8px 0; padding: 8px; background: #fffbeb; border: 1px solid #fde68a; border-radius: 6px; }
    form { margin: 16px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; max-width: 480px; }
    label { display: block; margin: 8px 0 4px; font-size: 13px; }
    input, textarea, select { width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; }
    button { margin-top: 12px; padding: 8px 14px; background: #111; color: white; border: 0; border-radius: 6px; cursor: pointer; }
    button:disabled { background: #d1d5db; cursor: not-allowed; }
    ul { list-style: none; padding: 0; } li { padding: 6px 0; border-bottom: 1px solid #f3f4f6; }
"""


def _render_index(
    project_id: str,
    project: dict[str, Any],
    gates: list[dict[str, Any]],
    *,
    error: str,
) -> str:
    """Return the inline HTML for the gates list page."""
    name = _esc(project.get("name", ""))
    run_id = _esc(project.get("run_id", ""))
    cards = "".join(_gate_card(project_id, g) for g in gates)
    body = cards or '<p class="muted">No gates for this project.</p>'
    error_html = f'<div class="error">{_esc(error)}</div>' if error else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>louke gates</title>
  <style>{_PAGE_STYLE}</style>
</head>
<body>
  <h1>Gates <a class="badge" href="/projects/{_esc(project_id)}">{name}</a></h1>
  <p class="muted">project: {_truncate(project_id)} | run: {_truncate(run_id)}</p>
  {error_html}
  <section>
    {body}
  </section>
</body>
</html>
"""


def _gate_card(project_id: str, gate: dict[str, Any]) -> str:
    """Return the HTML card for a single gate in the list."""
    gate_id = _esc(gate.get("gate_id", ""))
    step_id = _esc(gate.get("step_id", ""))
    status = _esc(gate.get("status", ""))
    bound_digest = _esc(gate.get("bound_digest", ""))
    return f"""<div class="card">
  <div><a href="/projects/{_esc(project_id)}/gates/{gate_id}">{step_id}</a> <span class="badge badge-{status}">{status}</span></div>
  <div class="muted">gate: {_truncate(gate_id)} | digest: {_truncate(bound_digest, 24)}</div>
</div>"""


def _render_detail(
    project_id: str,
    project: dict[str, Any],
    *,
    gate: dict[str, Any] | None,
    error: str,
) -> str:
    """Return the inline HTML for the gate detail page."""
    run_id = _esc(project.get("run_id", ""))
    error_html = f'<div class="error">{_esc(error)}</div>' if error else ""
    if gate is None:
        return _render_gate_not_found(project_id, error_html)
    gate_id = _esc(gate.get("gate_id", ""))
    step_id = _esc(gate.get("step_id", ""))
    status = _esc(gate.get("status", ""))
    bound_digest = _esc(gate.get("bound_digest", ""))
    expected_revision = _esc(gate.get("expected_revision", ""))
    actor_id = _esc(gate.get("actor_id", "") or "")
    reason = _esc(gate.get("reason", "") or "")
    decided_at = _esc(gate.get("decided_at", "") or "")

    section_label = _gate_section_label(str(gate.get("step_id", "")))
    decision_html = _render_decision_record(actor_id, decided_at, reason, status)
    blocker_html = _render_blocker(gate)
    form_html = _render_decide_form(project_id, gate_id, gate)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>louke {step_id}</title>
  <style>{_PAGE_STYLE}</style>
</head>
<body>
  <h1>{step_id} <span class="badge badge-{status}">{status}</span></h1>
  <p class="muted">project: {_truncate(project_id)} | run: {_truncate(run_id)} | gate: {_truncate(gate_id)}</p>
  {error_html}
  <section>
    <h2>{section_label}</h2>
    <div class="card">
      <div>bound digest: <code>{bound_digest}</code></div>
      <div>expected revision: <code>{expected_revision}</code></div>
    </div>
    {decision_html}
  </section>
  <section>
    <h2>Decision</h2>
    {blocker_html}
    {form_html}
  </section>
  <p><a href="/projects/{_esc(project_id)}/gates">Back to gates</a></p>
</body>
</html>
"""


def _render_gate_not_found(project_id: str, error_html: str) -> str:
    """Return the inline HTML for a missing gate."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>louke gate not found</title>
  <style>{_PAGE_STYLE}</style>
</head>
<body>
  <h1>Gate not found</h1>
  {error_html}
  <p><a href="/projects/{_esc(project_id)}/gates">Back to gates</a></p>
</body>
</html>
"""


def _gate_blockers(gate: dict[str, Any]) -> list[str]:
    """Return human-readable reasons why the gate cannot be approved."""
    blockers: list[str] = []
    status = str(gate.get("status", ""))
    if status == "stale":
        blockers.append("gate is stale")
    open_discussions = gate.get("open_discussions", 0)
    if isinstance(open_discussions, int) and open_discussions > 0:
        blockers.append(f"{open_discussions} open discussions")
    if status in ("approved", "rejected"):
        blockers.append(f"gate already {status}")
    return blockers


def _render_blocker(gate: dict[str, Any]) -> str:
    """Return the HTML blocker text when the gate cannot be approved."""
    blockers = _gate_blockers(gate)
    if not blockers:
        return ""
    items = "".join(f"<li>{_esc(b)}</li>" for b in blockers)
    return f'<div class="blocker">Cannot approve: <ul>{items}</ul></div>'


def _gate_section_label(step_id: str) -> str:
    """Return the labeled section heading for a gate kind (AC-FR1901-03)."""
    if step_id == "requirements_approval":
        return "Requirements Approval"
    if step_id == "m_lock":
        return "M-LOCK"
    return step_id.replace("_", " ").title()


def _render_decision_record(
    actor_id: str, decided_at: str, reason: str, status: str
) -> str:
    """Return the HTML for a recorded decision, or an empty string when pending."""
    if status == "waiting_for_human":
        return ""
    return f"""<div class="card">
  <div>actor: <code>{actor_id}</code></div>
  <div>decided at: <code>{decided_at}</code></div>
  {f'<div>reason: {_esc(reason)}</div>' if reason else ''}
</div>"""


def _render_decide_form(project_id: str, gate_id: str, gate: dict[str, Any]) -> str:
    """Return the HTML form for approve/reject, disabled when blocked or decided."""
    disabled = "disabled" if _gate_blockers(gate) else ""
    return f"""<form method="post" action="/projects/{_esc(project_id)}/gates/{_esc(gate_id)}/decide">
  <label for="verdict">Verdict</label>
  <select id="verdict" name="verdict" {disabled}>
    <option value="approve">Approve</option>
    <option value="reject">Reject</option>
  </select>
  <label for="reason">Reason (required for reject)</label>
  <textarea id="reason" name="reason" rows="3" {disabled}></textarea>
  <button type="submit" {disabled}>Submit</button>
</form>"""


def _render_decide_error(project_id: str, gate_id: str, error: str) -> str:
    """Return the inline HTML for a decide error page (re-render with error)."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>louke gate error</title>
  <style>{_PAGE_STYLE}</style>
</head>
<body>
  <h1>Gate decision error</h1>
  <div class="error">{_esc(error)}</div>
  <p><a href="/projects/{_esc(project_id)}/gates/{_esc(gate_id)}">Back to gate</a></p>
</body>
</html>
"""


def _render_not_found(project_id: str, error: str) -> str:
    """Return the inline HTML for a not-found gates page."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>louke project not found</title>
  <style>{_PAGE_STYLE}</style>
</head>
<body>
  <h1>Project not found</h1>
  <div class="error">Project {_esc(project_id)} not found. {_esc(error)}</div>
  <p><a href="/projects">Back to projects</a></p>
</body>
</html>
"""
