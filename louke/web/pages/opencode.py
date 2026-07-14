"""``/opencode`` page sub-app: OpenCode instance list + chat view (B6).

Single inline-HTML page (no Jinja2). The sub-app talks to the upstream
``/api/opencode/*`` sub-app via :mod:`httpx`. All upstream calls go through
module-level seams (``_fetch_*`` / ``_post_*`` / ``_delete_*``) so tests
can patch them without a live server, mirroring ``/projects`` and ``/runs``.

Routes (relative to the mount path ``/opencode``):

    GET  /                  - list instances + adapter_kind banner + Stop buttons.
    GET  /{instance_id}     - chat view: messages + send form + 4 control buttons.
    POST /new               - create a new instance, redirect to its chat view.

Honest mock vs real labeling: when ``adapter_kind == "mock"`` the index page
shows a yellow warning banner so the user knows responses are echoes, not
real OpenCode output (B5 already returns ``adapter_kind`` in ``/status``).

The chat view auto-refreshes messages every 5s via a ``<meta http-equiv
refresh>`` tag (SSE deferred to v0.13).
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


def create_app(api_base: str = "") -> Starlette:
    """Return a self-contained Starlette sub-app for the ``/opencode`` page.

    Args:
        api_base: Base URL for upstream API calls (e.g. ``"http://testserver"``).
            Empty string means same-origin.

    Returns:
        A Starlette application whose routes are relative to ``/opencode``.
    """
    app = Starlette(routes=_routes())
    app.state.api_base = api_base
    return app


def _routes() -> list[Route]:
    """Return the routes for the opencode page sub-app."""
    return [
        Route("/", endpoint=opencode_index),
        Route("/new", endpoint=new_instance, methods=["POST"]),
        Route("/{instance_id}", endpoint=opencode_chat),
    ]


# -- upstream seams ----------------------------------------------------------


async def _fetch_status(api_base: str) -> dict[str, Any]:
    """Fetch the adapter status from ``GET {api_base}/api/opencode/status``.

    The status carries ``adapter_kind`` (``mock`` | ``real``) which the
    index page uses to decide whether to show the mock warning banner.

    Raises:
        httpx.HTTPError: if the upstream call fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_base}/api/opencode/status")
        resp.raise_for_status()
        return dict(resp.json())


async def _fetch_instances(api_base: str) -> dict[str, Any]:
    """Fetch the instances list from ``GET {api_base}/api/opencode/instances``.

    Raises:
        httpx.HTTPError: if the upstream call fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_base}/api/opencode/instances")
        resp.raise_for_status()
        return dict(resp.json())


async def _fetch_messages(api_base: str, instance_id: str) -> dict[str, Any]:
    """Fetch messages from ``GET {api_base}/api/opencode/instances/{id}/messages``.

    Raises:
        httpx.HTTPError: if the upstream call fails (including 404).
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{api_base}/api/opencode/instances/{instance_id}/messages"
        )
        resp.raise_for_status()
        return dict(resp.json())


async def _post_create_instance(api_base: str) -> dict[str, Any]:
    """POST to create a new instance at ``{api_base}/api/opencode/instances``.

    Raises:
        httpx.HTTPError: if the upstream call fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{api_base}/api/opencode/instances")
        resp.raise_for_status()
        return dict(resp.json())


async def _post_send_message(
    api_base: str, instance_id: str, content: str
) -> dict[str, Any]:
    """POST a message to ``{api_base}/api/opencode/instances/{id}/messages``.

    Raises:
        httpx.HTTPError: if the upstream call fails (4xx/5xx).
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{api_base}/api/opencode/instances/{instance_id}/messages",
            json={"content": content},
        )
        resp.raise_for_status()
        return dict(resp.json())


async def _post_abort(api_base: str, instance_id: str) -> dict[str, Any]:
    """POST an abort to ``{api_base}/api/opencode/instances/{id}/abort``.

    Raises:
        httpx.HTTPError: if the upstream call fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{api_base}/api/opencode/instances/{instance_id}/abort"
        )
        resp.raise_for_status()
        return dict(resp.json())


async def _post_recover(api_base: str, instance_id: str) -> dict[str, Any]:
    """POST a recover to ``{api_base}/api/opencode/instances/{id}/recover``.

    Raises:
        httpx.HTTPError: if the upstream call fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{api_base}/api/opencode/instances/{instance_id}/recover"
        )
        resp.raise_for_status()
        return dict(resp.json())


async def _delete_instance(api_base: str, instance_id: str) -> dict[str, Any]:
    """DELETE an instance at ``{api_base}/api/opencode/instances?id={id}``.

    Raises:
        httpx.HTTPError: if the upstream call fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"{api_base}/api/opencode/instances",
            params={"id": instance_id},
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


# -- endpoints ----------------------------------------------------------------


async def opencode_index(request: Request) -> Response:
    """AC-FR1401-01: GET / - list instances with adapter_kind banner.

    Fetches ``/api/opencode/status`` (for ``adapter_kind``) and
    ``/api/opencode/instances`` (for the instance list). Upstream failures
    are rendered on the page (status 200), never 500.
    """
    api_base = _api_base(request)
    status: dict[str, Any] = {}
    instances: list[dict[str, Any]] = []
    error = ""
    try:
        status = await _fetch_status(api_base)
    except Exception as exc:
        error = f"status: {exc}"
    try:
        body = await _fetch_instances(api_base)
        instances = list(body.get("items", []))
    except Exception as exc:
        error = f"{error} | instances: {exc}".strip(" |")
    adapter_kind = str(
        status.get("adapter_kind")
        or (body.get("adapter_kind") if "body" in locals() else "")
        or "mock"
    )
    return HTMLResponse(_render_index(instances, adapter_kind, error=error))


async def opencode_chat(request: Request) -> Response:
    """AC-FR1401-01/02/03/04/05: GET /{instance_id} - chat view.

    Renders the message history, a send-message form, and four control
    buttons (Stop, Attach, End, Recover). The page auto-refreshes every
    5s so new messages appear without manual reload.
    """
    api_base = _api_base(request)
    instance_id = str(request.path_params["instance_id"])
    messages: list[dict[str, Any]] = []
    error = ""
    try:
        body = await _fetch_messages(api_base, instance_id)
        messages = list(body.get("items", []))
    except Exception as exc:
        error = str(exc)
    return HTMLResponse(_render_chat(instance_id, messages, error=error))


async def new_instance(request: Request) -> Response:
    """AC-FR1401-01: POST /new - create an instance, redirect to its chat view.

    On upstream failure, redirects back to the index (the index re-fetches
    status and surfaces the error there). We never return a 500.
    """
    api_base = _api_base(request)
    try:
        body = await _post_create_instance(api_base)
    except Exception as exc:
        return HTMLResponse(_render_index([], "mock", error=str(exc)))
    instance = body.get("instance") or {}
    new_id = str(instance.get("id", ""))
    if not new_id:
        return HTMLResponse(
            _render_index([], "mock", error="upstream returned no instance id")
        )
    return RedirectResponse(url=f"/opencode/{new_id}", status_code=303)


# -- HTML renderers ----------------------------------------------------------


_PAGE_STYLE = """\
    body { font-family: ui-sans-serif, system-ui, sans-serif; margin: 24px; color: #111; }
    h1 { font-size: 24px; } h2 { font-size: 18px; margin-top: 24px; }
    a { color: #2563eb; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .card { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px 16px; margin: 8px 0; }
    .badge { display: inline-block; padding: 2px 8px; border-radius: 6px; background: #f3f4f6; font-size: 12px; }
    .badge-running { background: #dcfce7; color: #166534; }
    .badge-stopped { background: #f3f4f6; color: #6b7280; }
    .badge-error { background: #fee2e2; color: #991b1b; }
    .banner-mock { background: #fef3c7; color: #92400e; border: 1px solid #f59e0b; border-radius: 6px; padding: 10px 14px; margin: 12px 0; }
    .banner-real { background: #dcfce7; color: #166534; border: 1px solid #22c55e; border-radius: 6px; padding: 10px 14px; margin: 12px 0; }
    .muted { color: #6b7280; }
    .error { color: #b91c1c; margin: 12px 0; }
    form { margin: 16px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; max-width: 640px; }
    label { display: block; margin: 8px 0 4px; font-size: 13px; }
    input, textarea { width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; }
    textarea { min-height: 80px; font-family: inherit; }
    button { margin-top: 12px; padding: 8px 14px; background: #111; color: white; border: 0; border-radius: 6px; cursor: pointer; }
    button.danger { background: #b91c1c; }
    button.secondary { background: #6b7280; }
    ul.msg { list-style: none; padding: 0; }
    li.msg { padding: 8px 0; border-bottom: 1px solid #f3f4f6; }
    li.msg .role { font-weight: bold; margin-right: 8px; }
"""


def _render_index(
    instances: list[dict[str, Any]],
    adapter_kind: str,
    *,
    error: str,
) -> str:
    """Return the inline HTML for the opencode instances list page."""
    banner = _render_adapter_banner(adapter_kind)
    error_html = f'<div class="error">{_esc(error)}</div>' if error else ""
    if instances:
        cards = "".join(_instance_card(i) for i in instances)
        new_form = _render_new_form()
    else:
        cards = '<p class="muted">No instances.</p>'
        new_form = _render_new_form()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>louke opencode</title>
  <style>{_PAGE_STYLE}</style>
</head>
<body>
  <h1>OpenCode</h1>
  {banner}
  {error_html}
  <section>
    <h2>Instances</h2>
    {cards}
  </section>
  {new_form}
</body>
</html>
"""


def _render_adapter_banner(adapter_kind: str) -> str:
    """Return the honest mock/real banner HTML based on ``adapter_kind``."""
    if adapter_kind == "mock":
        return (
            '<div class="banner-mock">'
            "<strong>Mock backend:</strong> messages echo. "
            "Set <code>LOUKE_OPENCODE_BACKEND=real</code> + "
            "<code>LOUKE_OPENCODE_BASE_URL</code> for real OpenCode."
            "</div>"
        )
    if adapter_kind == "real":
        return '<div class="banner-real"><strong>Real backend:</strong> live OpenCode.</div>'
    return ""


def _instance_card(instance: dict[str, Any]) -> str:
    """Return the HTML card for a single instance summary."""
    instance_id = _esc(instance.get("id", ""))
    status = _esc(instance.get("status", ""))
    created_at = _esc(instance.get("created_at", ""))
    err = instance.get("error")
    error_html = f' <span class="muted">{_esc(err)}</span>' if err else ""
    return f"""<div class="card">
  <div><a href="/opencode/{instance_id}">{_truncate(instance_id)}</a> <span class="badge badge-{status}">{status}</span>{error_html}</div>
  <div class="muted">created: {created_at}</div>
  <form method="post" action="/api/opencode/instances/{instance_id}/abort" style="display:inline; border:0; padding:0; margin:0; max-width:none;">
    <button type="submit" class="secondary">Stop</button>
  </form>
</div>"""


def _render_new_form() -> str:
    """Return the inline HTML for the new-instance form."""
    return """<form method="post" action="/opencode/new">
  <button type="submit">+ New instance</button>
</form>"""


def _render_chat(
    instance_id: str,
    messages: list[dict[str, Any]],
    *,
    error: str,
) -> str:
    """Return the inline HTML for the instance chat view."""
    safe_id = _esc(instance_id)
    error_html = f'<div class="error">{_esc(error)}</div>' if error else ""
    if messages:
        msgs_html = "".join(_render_message(m) for m in messages)
        msgs_section = f'<ul class="msg">{msgs_html}</ul>'
    else:
        msgs_section = '<p class="muted">No messages yet.</p>'
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta http-equiv="refresh" content="5" />
  <title>louke opencode {safe_id}</title>
  <style>{_PAGE_STYLE}</style>
</head>
<body>
  <h1>OpenCode chat <span class="muted">{_truncate(instance_id)}</span></h1>
  <p><a href="/opencode">&larr; back to instances</a></p>
  {error_html}
  <section>
    <h2>Messages</h2>
    {msgs_section}
  </section>
  <section>
    <h2>Send a message</h2>
    <form method="post" action="/api/opencode/instances/{safe_id}/messages">
      <textarea id="content" name="content" rows="4" required placeholder="Type a message..."></textarea>
      <button type="submit">Send</button>
    </form>
  </section>
  <section>
    <h2>Controls</h2>
    <form method="post" action="/api/opencode/instances/{safe_id}/abort" style="display:inline; border:0; padding:0; margin:0; max-width:none;">
      <button type="submit" class="secondary">Stop generation</button>
    </form>
    <form method="post" action="/opencode/{safe_id}" style="display:inline; border:0; padding:0; margin:0; max-width:none;">
      <button type="submit" class="secondary">Attach / refresh</button>
    </form>
    <form method="post" action="/api/opencode/instances/{safe_id}/recover" style="display:inline; border:0; padding:0; margin:0; max-width:none;">
      <button type="submit" class="secondary">Recover status</button>
    </form>
    <form method="post" action="/api/opencode/instances?id={safe_id}" style="display:inline; border:0; padding:0; margin:0; max-width:none;">
      <input type="hidden" name="_method" value="DELETE" />
      <button type="submit" class="danger">End session</button>
    </form>
  </section>
  <p class="muted">Auto-refreshing every 5s.</p>
</body>
</html>
"""


def _render_message(message: dict[str, Any]) -> str:
    """Return the HTML list item for a single message."""
    role = _esc(message.get("role", ""))
    kind = _esc(message.get("kind", ""))
    content = _esc(message.get("content", ""))
    created_at = _esc(message.get("created_at", ""))
    return (
        f'<li class="msg"><span class="role">{role}</span>'
        f'<span class="muted">{kind} {created_at}</span>'
        f"<div>{content}</div></li>"
    )
