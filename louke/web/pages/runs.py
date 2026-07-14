"""``/runs/{run_id}`` page sub-app: workflow run detail (B3b).

Single inline-HTML page (no Jinja2). Renders the workflow run detail:
project header (definition_id, status, current step, revision), the workflow
graph as inline SVG (nodes as circles, edges as arrows, current step green,
completed steps blue, waiting gates orange), the last 50 events, the gates list,
and a run-command form that posts to upstream ``/api/runtime/{run_id}/commands``.

Upstream HTTP calls go through module-level seams (``_fetch_*`` / ``_post_*``)
so tests can patch them without a live server, mirroring ``/projects``.

Routes (relative to the mount path ``/runs``):

    GET  /runs/{run_id}         - render the workflow run detail page.
    POST /runs/{run_id}/command - apply a runtime command to advance the run.
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

#: Default principal used for page-submitted commands (no auth in B1).
_DEFAULT_PRINCIPAL: dict[str, str] = {"kind": "human", "id": "web-user"}

#: Node fill colors by state for the SVG graph.
_NODE_COLORS: dict[str, str] = {
    "completed": "#3b82f6",  # blue
    "current": "#22c55e",  # green
    "waiting_for_human": "#f97316",  # orange
    "blocked": "#ef4444",  # red
    "failed": "#ef4444",  # red
    "pending": "#9ca3af",  # gray
    "skipped_by_definition": "#d1d5db",  # light gray
}


def create_app(api_base: str = "") -> Starlette:
    """Return a self-contained Starlette sub-app for the runs page.

    Args:
        api_base: Base URL for upstream API calls (e.g. ``"http://testserver"``).
            Empty string means same-origin.

    Returns:
        A Starlette application whose routes include the full ``/runs/{run_id}``
        prefix (B3c will register this sub-app directly in ``app.py``).
    """
    app = Starlette(routes=_routes())
    app.state.api_base = api_base
    return app


def _routes() -> list[Route]:
    """Return the routes for the runs page sub-app."""
    return [
        Route("/runs/{run_id}", endpoint=run_detail),
        Route("/runs/{run_id}/command", endpoint=run_command, methods=["POST"]),
    ]


# -- upstream seams ----------------------------------------------------------


async def _fetch_run(api_base: str, run_id: str) -> dict[str, Any]:
    """Fetch a single run from ``GET {api_base}/api/runtime/runs/{run_id}``.

    Raises:
        httpx.HTTPError: if the upstream call fails (including 404).
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_base}/api/runtime/runs/{run_id}")
        resp.raise_for_status()
        return dict(resp.json())


async def _fetch_events(api_base: str, run_id: str) -> list[dict[str, Any]]:
    """Fetch events from ``GET {api_base}/api/runtime/runs/{run_id}/events``.

    Raises:
        httpx.HTTPError: if the upstream call fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_base}/api/runtime/runs/{run_id}/events")
        resp.raise_for_status()
        return list(resp.json().get("items", []))


async def _fetch_gates(api_base: str, run_id: str) -> list[dict[str, Any]]:
    """Fetch gates for a run from ``GET {api_base}/api/gates/runs/{run_id}/gates``.

    Raises:
        httpx.HTTPError: if the upstream call fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_base}/api/gates/runs/{run_id}/gates")
        resp.raise_for_status()
        return list(resp.json().get("items", []))


async def _post_command(
    api_base: str,
    run_id: str,
    *,
    expected_revision: int,
    result: str | None = None,
    requested_next_step: str | None = None,
) -> dict[str, Any]:
    """POST a runtime command to ``{api_base}/api/runtime/runs/{run_id}/commands``.

    Raises:
        httpx.HTTPError: if the upstream call fails (4xx/5xx).
    """
    payload: dict[str, Any] = {"expected_revision": expected_revision}
    if result is not None:
        payload["result"] = result
    if requested_next_step is not None:
        payload["requested_next_step"] = requested_next_step
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{api_base}/api/runtime/runs/{run_id}/commands", json=payload
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


async def run_detail(request: Request) -> Response:
    """GET /runs/{run_id}: render the run header, SVG graph, events and gates."""
    api_base = _api_base(request)
    run_id = request.path_params["run_id"]
    try:
        run = await _fetch_run(api_base, run_id)
    except Exception as exc:
        return HTMLResponse(_render_not_found(run_id, str(exc)))
    events, events_err = await _safe_fetch(_fetch_events, api_base, run_id)
    gates, gates_err = await _safe_fetch(_fetch_gates, api_base, run_id)
    error = events_err or gates_err
    return HTMLResponse(_render_detail(run, events, gates, error=error))


async def run_command(request: Request) -> Response:
    """POST /runs/{run_id}/command: forward a runtime command to the API.

    On success, redirects back to the run detail. On failure, re-renders the
    detail page with an error message (status 200).
    """
    api_base = _api_base(request)
    run_id = request.path_params["run_id"]
    form = _parse_form(await request.body())
    try:
        run = await _fetch_run(api_base, run_id)
    except Exception as exc:
        return HTMLResponse(_render_not_found(run_id, str(exc)))
    try:
        await _post_command(
            api_base,
            run_id,
            expected_revision=int(run.get("revision", 0)),
            result=form.get("result") or None,
            requested_next_step=form.get("step_id") or None,
        )
    except Exception as exc:
        events, _ = await _safe_fetch(_fetch_events, api_base, run_id)
        gates, _ = await _safe_fetch(_fetch_gates, api_base, run_id)
        return HTMLResponse(_render_detail(run, events, gates, error=str(exc)))
    return RedirectResponse(url=f"/runs/{run_id}", status_code=303)


async def _safe_fetch(
    fetch: Any, api_base: str, run_id: str
) -> tuple[list[dict[str, Any]], str]:
    """Return ``(items, error)`` from ``fetch(api_base, run_id)``, never raising."""
    try:
        return await fetch(api_base, run_id), ""
    except Exception as exc:
        return [], str(exc)


# -- HTML renderers ----------------------------------------------------------


_PAGE_STYLE = """\
    body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 24px; color: #111; }
    h1 { font-size: 24px; } h2 { font-size: 18px; margin-top: 24px; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; margin: 8px 0; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 6px; background: #f3f4f6; font-size: 12px; }
    .badge-waiting_for_human { background: #fef3c7; color: #92400e; }
    .badge-active, .badge-running { background: #dcfce7; color: #166534; }
    .badge-completed { background: #dbeafe; color: #1e40af; }
    .muted { color: #6b7280; }
    .error { color: #b91c1c; margin: 12px 0; }
    form { margin: 16px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; max-width: 480px; }
    label { display: block; margin: 8px 0 4px; font-size: 13px; }
    input, textarea, select { width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; }
    button { margin-top: 12px; padding: 8px 14px; background: #111; color: white; border: 0; border-radius: 6px; cursor: pointer; }
    ul { list-style: none; padding: 0; } li { padding: 6px 0; border-bottom: 1px solid #f3f4f6; }
"""


def _render_detail(
    run: dict[str, Any],
    events: list[dict[str, Any]],
    gates: list[dict[str, Any]],
    *,
    error: str,
) -> str:
    """Return the inline HTML for the run detail page."""
    run_id = _esc(run.get("run_id", ""))
    definition_id = _esc(run.get("definition_id", ""))
    definition_version = _esc(run.get("definition_version", ""))
    current_step = _esc(run.get("current_step", ""))
    revision = _esc(run.get("revision", ""))
    status = _esc(run.get("status", ""))
    error_html = f'<div class="error">{_esc(error)}</div>' if error else ""
    svg_html = _render_graph_svg(run, events)
    events_html = _render_events(events) or '<p class="muted">No events.</p>'
    gates_html = _render_gates(str(run.get("run_id", "")), gates) or _empty_gates()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>louke run {run_id}</title>
  <style>{_PAGE_STYLE}</style>
</head>
<body>
  <h1>Run {_truncate(run_id)}</h1>
  <p>definition: <code>{definition_id} v{definition_version}</code> | status: <span class="badge badge-{status}">{status}</span> | current step: <span class="badge">{current_step}</span> | revision: <code>{revision}</code></p>
  {error_html}
  <section>
    <h2>Graph</h2>
    {svg_html}
  </section>
  <section>
    <h2>Events</h2>
    {events_html}
  </section>
  <section>
    <h2>Gates</h2>
    {gates_html}
  </section>
  <section>
    <h2>Run command</h2>
    <form method="post" action="/runs/{run_id}/command">
      <label for="step_id">Step id</label>
      <input id="step_id" name="step_id" type="text" placeholder="{current_step}" />
      <label for="result">Result</label>
      <input id="result" name="result" type="text" placeholder="done" />
      <button type="submit">Submit</button>
    </form>
  </section>
</body>
</html>
"""


def _render_graph_svg(run: dict[str, Any], events: list[dict[str, Any]]) -> str:
    """Return an inline SVG of the workflow graph derived from run + events.

    Nodes are derived from the events' ``from_step``/``to_step`` and the run's
    ``current_step``. Edges are derived from event transitions.
    """
    nodes, edges = _derive_graph(run, events)
    if not nodes:
        return '<p class="muted">No graph available.</p>'
    return _build_svg(nodes, edges, run)


def _derive_graph(
    run: dict[str, Any], events: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Derive nodes and edges from the run state and event history.

    Nodes are the union of step ids seen in events (from/to/step_id) plus the
    run's current step. Edges are the distinct (from_step, to_step) pairs from
    transition events.
    """
    current_step = str(run.get("current_step", ""))
    seen: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    edge_keys: set[tuple[str, str]] = set()

    completed: set[str] = set()
    for event in events:
        from_step = event.get("from_step")
        to_step = event.get("to_step")
        step_id = event.get("step_id")
        for sid in (from_step, to_step, step_id):
            if sid and str(sid) not in seen:
                seen[str(sid)] = {"step_id": str(sid)}
        if from_step and to_step and str(from_step) != str(to_step):
            key = (str(from_step), str(to_step))
            if key not in edge_keys:
                edge_keys.add(key)
                edges.append({"from_step": str(from_step), "to_step": str(to_step)})
        if to_step and str(to_step) != current_step:
            completed.add(str(to_step))

    if current_step and current_step not in seen:
        seen[current_step] = {"step_id": current_step}

    nodes: list[dict[str, Any]] = []
    for node in seen.values():
        sid = str(node["step_id"])
        node["state"] = _node_state(sid, current_step, completed)
        nodes.append(node)
    return nodes, edges


def _node_state(
    step_id: str, current_step: str, completed: set[str]
) -> str:
    """Return the graph state for a node relative to the current run position."""
    if step_id == current_step:
        return "current"
    if step_id in completed:
        return "completed"
    return "pending"


def _build_svg(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    run: dict[str, Any],
) -> str:
    """Return the inline SVG markup for the workflow graph."""
    current_step = str(run.get("current_step", ""))
    status = str(run.get("status", ""))
    n = len(nodes)
    width = max(600, n * 140)
    height = 160
    spacing = width // max(n, 1)
    positions: dict[str, tuple[int, int]] = {}
    circles: list[str] = []
    labels: list[str] = []
    for idx, node in enumerate(nodes):
        sid = str(node["step_id"])
        state = str(node["state"])
        color = _node_fill(state, sid, current_step, status)
        x = spacing // 2 + idx * spacing
        y = 50
        positions[sid] = (x, y)
        circles.append(f'<circle cx="{x}" cy="{y}" r="20" fill="{color}" stroke="#111" />')
        labels.append(
            f'<text x="{x}" y="{y + 40}" text-anchor="middle" font-size="11">{_esc(sid)}</text>'
        )
    arrows: list[str] = []
    for edge in edges:
        src = str(edge["from_step"])
        dst = str(edge["to_step"])
        if src not in positions or dst not in positions:
            continue
        x1, y1 = positions[src]
        x2, y2 = positions[dst]
        arrows.append(
            f'<line x1="{x1 + 20}" y1="{y1}" x2="{x2 - 20}" y2="{y2}" stroke="#6b7280" stroke-width="1.5" marker-end="url(#arrow)" />'
        )
    return f"""<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">
  <defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L8,3 L0,6 Z" fill="#6b7280" /></marker></defs>
  {"".join(arrows)}
  {"".join(circles)}
  {"".join(labels)}
</svg>"""


def _node_fill(state: str, step_id: str, current_step: str, run_status: str) -> str:
    """Return the SVG fill color for a node.

    Current step is green; completed steps are blue; the current human_gate step
    is orange (waiting for human); pending steps are gray.
    """
    if step_id == current_step:
        if run_status == "waiting_for_human":
            return _NODE_COLORS["waiting_for_human"]
        return _NODE_COLORS["current"]
    return _NODE_COLORS.get(state, _NODE_COLORS["pending"])


def _render_events(events: list[dict[str, Any]]) -> str:
    """Return the HTML list for the events timeline (last 50)."""
    if not events:
        return ""
    recent = events[-50:]
    items = "".join(_render_event(e) for e in recent)
    return f"<ul>{items}</ul>"


def _render_event(event: dict[str, Any]) -> str:
    """Return the HTML list item for a single event."""
    event_type = _esc(event.get("type", ""))
    at = _esc(event.get("at", event.get("occurred_at", "")))
    sequence = _esc(event.get("sequence", ""))
    return f"<li>{at} #{sequence} {event_type}</li>"


def _render_gates(run_id: str, gates: list[dict[str, Any]]) -> str:
    """Return the HTML list of gates with links into the gate detail page."""
    if not gates:
        return ""
    items = "".join(_render_gate_row(run_id, g) for g in gates)
    return f"<ul>{items}</ul>"


def _render_gate_row(run_id: str, gate: dict[str, Any]) -> str:
    """Return the HTML list item for a single gate in the run detail page."""
    gate_id = _esc(gate.get("gate_id", ""))
    step_id = _esc(gate.get("step_id", ""))
    status = _esc(gate.get("status", ""))
    return (
        f'<li><a href="/runs/{_esc(run_id)}/gates/{gate_id}">{step_id}</a> '
        f'<span class="badge badge-{status}">{status}</span></li>'
    )


def _empty_gates() -> str:
    """Return the empty-state message for the gates section."""
    return '<p class="muted">No gates.</p>'


def _render_not_found(run_id: str, error: str) -> str:
    """Return the inline HTML for a not-found run detail page."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>louke run not found</title>
  <style>{_PAGE_STYLE}</style>
</head>
<body>
  <h1>Run not found</h1>
  <div class="error">Run {_esc(run_id)} not found. {_esc(error)}</div>
  <p><a href="/projects">Back to projects</a></p>
</body>
</html>
"""
