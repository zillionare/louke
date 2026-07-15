"""``/setup`` page sub-app: setup-only wizard (B3a).

Single inline-HTML page (no Jinja2). Shows project state, the readiness
report from ``GET /api/readiness``, and a form to create the first local
human principal (POST to ``/api/setup/first-user``). When readiness is
complete, redirects to ``/``.

Upstream HTTP calls go through module-level seams (``_fetch_readiness`` and
``_post_first_user``) so tests can patch them without a live server.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs

import httpx
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse, Response
from starlette.routing import Route

#: Base URL for upstream API calls. Empty string means same-origin.
_API_BASE: str = ""


def create_app() -> Starlette:
    """Return a self-contained Starlette sub-app for the ``/setup`` page."""
    return Starlette(routes=_routes())


def _routes() -> list[Route]:
    """Return the routes for the setup page sub-app."""
    return [
        Route("/", endpoint=setup_page),
        Route("/first-user", endpoint=create_first_user, methods=["POST"]),
    ]


async def _fetch_readiness(api_base: str) -> list[dict[str, str]]:
    """Fetch the readiness report from ``GET {api_base}/api/readiness``.

    Raises:
        httpx.HTTPError: if the upstream call fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{api_base}/api/readiness")
        resp.raise_for_status()
        return list(resp.json().get("items", []))


async def _post_first_user(
    api_base: str, *, name: str, credential: str
) -> dict[str, Any]:
    """POST the first-user form to ``{api_base}/api/setup/first-user``.

    Raises:
        httpx.HTTPError: if the upstream call fails.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{api_base}/api/setup/first-user",
            json={"name": name, "credential": credential},
        )
        resp.raise_for_status()
        return dict(resp.json())


def _is_complete(items: list[dict[str, str]]) -> bool:
    """Return True when every readiness item is READY."""
    return all(item.get("status") == "READY" for item in items)


async def setup_page(request: Request) -> Response:
    """GET /setup: render the setup-only wizard.

    When readiness is complete, redirects to ``/``. Otherwise renders the
    HTML page with the readiness list and the first-user form.
    """
    setup_only = bool(getattr(request.app.state, "setup_only", True))
    try:
        items = await _fetch_readiness(_API_BASE)
    except Exception as exc:
        return HTMLResponse(_render(setup_only, [], error=str(exc)))
    if _is_complete(items):
        return RedirectResponse(url="/", status_code=303)
    return HTMLResponse(_render(setup_only, items, error=""))


async def create_first_user(request: Request) -> Response:
    """POST /setup/first-user: forward the first-user form to the API.

    On success, redirects to ``/setup`` so readiness re-checks. On failure,
    re-renders the wizard with an error message.
    """
    name, credential = _parse_form(await request.body())
    try:
        await _post_first_user(_API_BASE, name=name, credential=credential)
    except Exception as exc:
        return HTMLResponse(_render(True, await _safe_readiness(), error=str(exc)))
    return RedirectResponse(url="/setup", status_code=303)


async def _safe_readiness() -> list[dict[str, str]]:
    """Return readiness items, or an empty list if the upstream call fails."""
    try:
        return await _fetch_readiness(_API_BASE)
    except Exception:
        return []


def _parse_form(body: bytes) -> tuple[str, str]:
    """Parse a urlencoded form body into (name, credential).

    Avoids python-multipart; we only handle application/x-www-form-urlencoded.
    """
    pairs = parse_qs(body.decode("utf-8", errors="replace"))
    return (
        (pairs.get("name", [""])[0]).strip(),
        (pairs.get("credential", [""])[0]).strip(),
    )


def _render(setup_only: bool, items: list[dict[str, str]], *, error: str) -> str:
    """Return the inline HTML for the setup wizard."""
    readiness_html = "".join(_render_item(i) for i in items)
    readiness_section = (
        f"<ul>{readiness_html}</ul>"
        if items
        else '<p class="muted">No readiness items.</p>'
    )
    error_html = f'<div class="error">{_esc(error)}</div>' if error else ""
    state = "setup-only" if setup_only else "normal"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>louke setup</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 24px; color: #111; }}
    h1 {{ font-size: 24px; }} h2 {{ font-size: 18px; margin-top: 24px; }}
    .state {{ display: inline-block; padding: 2px 8px; border-radius: 6px; background: #f3f4f6; font-size: 12px; }}
    form {{ margin: 16px 0; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; max-width: 360px; }}
    label {{ display: block; margin: 8px 0 4px; font-size: 13px; }}
    input {{ width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; }}
    button {{ margin-top: 12px; padding: 8px 14px; background: #111; color: white; border: 0; border-radius: 6px; cursor: pointer; }}
    .error {{ color: #b91c1c; margin: 12px 0; }}
    ul {{ list-style: none; padding: 0; }} li {{ padding: 6px 0; border-bottom: 1px solid #f3f4f6; }}
    .status-READY {{ color: #166534; }} .status-BLOCKED {{ color: #b91c1c; }} .status-DEGRADED {{ color: #b45309; }}
  </style>
</head>
<body>
  <h1>louke setup</h1>
  <p>Project state: <span class="state">{_esc(state)}</span> mode</p>
  {error_html}
  <section>
    <h2>Readiness</h2>
    {readiness_section}
  </section>
  <section>
    <h2>First user</h2>
    <form method="post" action="/setup/first-user">
      <label for="name">Name</label>
      <input id="name" name="name" type="text" required />
      <label for="credential">Credential</label>
      <input id="credential" name="credential" type="password" required />
      <button type="submit">Create first user</button>
    </form>
  </section>
</body>
</html>
"""


def _render_item(item: dict[str, str]) -> str:
    """Return the HTML list item for a single readiness check."""
    name = _esc(item.get("name", ""))
    status = _esc(item.get("status", ""))
    diagnosis = _esc(item.get("diagnosis", ""))
    remediation = _esc(item.get("remediation", ""))
    return (
        f"<li><strong>{name}</strong> "
        f'<span class="status-{status}">{status}</span>'
        f"<div>diagnosis: {diagnosis}</div>"
        f"<div>remediation: {remediation}</div></li>"
    )


def _esc(text: str) -> str:
    """Return an HTML-escaped version of ``text``."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )
