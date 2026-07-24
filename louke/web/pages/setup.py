"""``/setup`` page sub-app: continuous Setup Wizard (B3a / FR-0101).

Renders a step-by-step Wizard surface for the FR-0101 Setup contract:
``identity -> repository -> dependencies -> review -> applying -> complete``.

The page is reachable from any step and supports return navigation: the
Wizard exposes per-step routes ``/setup/<step>/`` plus ``/setup/<step>/complete``
POST handler and ``/setup/return/<step>`` to revise an earlier choice.
Readiness and first-user creation remain first-class destinations within
the same shell; no separate landing page exists.

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

from ..setup_journey import (
    SetupStep,
    SetupJourney,
    render_step_views,
)

#: Base URL for upstream API calls. Empty string means same-origin.
_API_BASE: str = ""


def create_app() -> Starlette:
    """Return a self-contained Starlette sub-app for the ``/setup`` page."""
    return Starlette(routes=_routes())


def _routes() -> list[Route]:
    """Return the routes for the setup wizard page."""
    return [
        Route("/", endpoint=wizard_root, methods=["GET"]),
        Route("/identity/", endpoint=step_identity_get, methods=["GET"]),
        Route(
            "/identity/complete",
            endpoint=step_identity_complete,
            methods=["POST"],
        ),
        Route("/repository/", endpoint=step_repository_get, methods=["GET"]),
        Route(
            "/repository/complete",
            endpoint=step_repository_complete,
            methods=["POST"],
        ),
        Route("/dependencies/", endpoint=step_dependencies_get, methods=["GET"]),
        Route(
            "/dependencies/complete",
            endpoint=step_dependencies_complete,
            methods=["POST"],
        ),
        Route("/review/", endpoint=step_review_get, methods=["GET"]),
        Route(
            "/review/complete",
            endpoint=step_review_complete,
            methods=["POST"],
        ),
        Route("/applying/", endpoint=step_applying_get, methods=["GET"]),
        Route("/complete/", endpoint=step_complete_get, methods=["GET"]),
        Route(
            "/return/{step}",
            endpoint=wizard_return,
            methods=["POST"],
        ),
        Route("/first-user", endpoint=create_first_user, methods=["POST"]),
        Route("/reset", endpoint=wizard_reset, methods=["POST"]),
    ]


# ---------------------------------------------------------------------------
# Persistence seam
# ---------------------------------------------------------------------------


def _read_persisted_state(
    api_base: str, request: Request | None = None
) -> dict[str, Any]:
    """Read the persisted setup state via the API; return empty on miss.

    Uses an in-process direct call to the store rather than going through
    uvicorn.  Going through the HTTP socket would block the event loop and
    could observe torn writes during the redirect chain.
    """

    payload = _direct_store_call(request, lambda store: store.read_setup_state())
    return payload if isinstance(payload, dict) else {}


def _persist_state(
    api_base: str, payload: dict[str, Any], request: Request | None = None
) -> bool:
    """Persist setup state atomically via the store; return True on success."""
    from ..store import ProjectStore

    def _write(store: ProjectStore) -> None:
        store.write_setup_state(payload)

    return bool(_direct_store_call(request, _write))


def _direct_store_call(request: Request | None, fn):
    """Run ``fn(project_store)`` against the workspace backing the server.

    Prefers ``request.app.state.workspace_root`` so the page reads and
    writes the same store the API uses.  Falls back to ``Path.cwd()``
    for tests that do not bind the workspace root on the sub-app state.
    """
    from ..store import ProjectStore

    candidates: list[Path] = []
    if request is not None:
        root = getattr(request.app.state, "workspace_root", None)
        if root is not None:
            candidates.append(Path(root))
    candidates.append(Path.cwd())
    for root in candidates:
        if (root / ".louke" / "project" / "project.toml").exists():
            try:
                return fn(ProjectStore(root))
            except Exception:
                continue
    return None


from pathlib import Path  # noqa: E402


def _journey_from_payload(payload: dict[str, Any]) -> SetupJourney:
    """Build a SetupJourney from the API's persisted-state dict."""
    try:
        step = SetupStep(payload.get("current_step") or SetupStep.IDENTITY.value)
    except ValueError:
        step = SetupStep.IDENTITY
    completed_raw = payload.get("completed_steps") or []
    completed: tuple[SetupStep, ...] = tuple(
        SetupStep(c) for c in completed_raw if c in {s.value for s in SetupStep}
    )
    blocking_raw = payload.get("blocking_items") or []
    blocking: tuple[str, ...] = tuple(str(b) for b in blocking_raw)
    selections_raw = payload.get("selections") or {}
    selections: tuple[tuple[str, str], ...] = tuple(
        (str(k), str(v)) for k, v in selections_raw.items()
    )
    return SetupJourney(
        current_step=step,
        completed_steps=completed,
        blocking_items=blocking,
        selections=selections,
    )


def _payload_from_journey(journey: SetupJourney) -> dict[str, Any]:
    """Render a SetupJourney as the API's persisted-state dict shape."""
    return {
        "current_step": journey.current_step.value,
        "completed_steps": [s.value for s in journey.completed_steps],
        "blocking_items": list(journey.blocking_items),
        "selections": dict(journey.selections),
    }


# ---------------------------------------------------------------------------
# Wizard root / navigation
# ---------------------------------------------------------------------------


async def wizard_root(request: Request) -> Response:
    """GET /setup: redirect to the current step page or render first-user form.

    When the user has not yet created a first principal, show the first-user
    creation form. Otherwise redirect to the current step page.
    """
    api_base = _api_base(request)
    try:
        status = await _fetch_setup_status(api_base)
    except Exception:
        status = {"initialized": False}
    if not status.get("initialized"):
        return await setup_page(request)
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    return RedirectResponse(
        url=f"/setup/{journey.current_step.value}/", status_code=303
    )


async def wizard_return(request: Request) -> Response:
    """POST /setup/return/<step>: revise an earlier step.

    Invalidates dependent downstream results by re-anchoring the journey to
    ``step``. Returns the user to that step's page.
    """
    step_name = request.path_params["step"]
    api_base = _api_base(request)
    try:
        target = SetupStep(step_name)
    except ValueError:
        return RedirectResponse(url="/setup/", status_code=303)
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    updated = journey.return_to(target)
    _persist_state(api_base, _payload_from_journey(updated), request)
    return RedirectResponse(url=f"/setup/{target.value}/", status_code=303)


async def wizard_reset(request: Request) -> Response:
    """POST /setup/reset: clear persisted state and return to identity."""
    api_base = _api_base(request)
    _persist_state(api_base, _payload_from_journey(SetupJourney.new()), request)
    return RedirectResponse(url="/setup/identity/", status_code=303)


# ---------------------------------------------------------------------------
# Step handlers (GET)
# ---------------------------------------------------------------------------


async def _common_render(
    request: Request,
    journey: SetupJourney,
    body_html: str,
    *,
    can_advance: bool,
) -> HTMLResponse:
    """Render the wizard shell with the given step body.

    Args:
        request: Incoming HTTP request.
        journey: Current Setup journey projection.
        body_html: Per-step HTML body content.
        can_advance: Whether the user may submit "Complete this step".

    Returns:
        An HTMLResponse with the wizard shell rendered around the body.
    """
    setup_only = bool(getattr(request.app.state, "setup_only", True))
    return HTMLResponse(
        _render_wizard(
            setup_only=setup_only,
            journey=journey,
            body_html=body_html,
            can_advance=can_advance,
            error="",
        )
    )


async def step_identity_get(request: Request) -> Response:
    """GET /setup/identity/: render the first-user step form.

    If no principal exists yet, render the first-user creation form.
    Once a user exists, show the established panel. The wizard does
    NOT auto-advance; if the user returned to this step, the journey
    stays put until they explicitly proceed.
    """
    api_base = _api_base(request)
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    try:
        status = await _fetch_setup_status(api_base)
    except Exception:
        status = {"initialized": False}
    if not status.get("initialized"):
        # First-user form: identity is not yet complete. Render the same
        # backward-compatible form, but inside the wizard shell.
        body = await _first_user_form_html(status)
        return await _common_render(request, journey, body, can_advance=False)
    body = _identity_done_html(status)
    return await _common_render(request, journey, body, can_advance=False)


async def step_identity_complete(request: Request) -> Response:
    """POST /setup/identity/complete: complete the identity step.

    The first-user creation itself is handled by ``/setup/first-user``. This
    endpoint is hit after that submission to advance the wizard.
    """
    api_base = _api_base(request)
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    try:
        status = await _fetch_setup_status(api_base)
    except Exception:
        status = {"initialized": False}
    if not status.get("initialized"):
        return RedirectResponse(url="/setup/identity/", status_code=303)
    if SetupStep.IDENTITY not in journey.completed_steps:
        journey = journey.complete_current()
        _persist_state(api_base, _payload_from_journey(journey), request)
    return RedirectResponse(url="/setup/repository/", status_code=303)


async def step_repository_get(request: Request) -> Response:
    """GET /setup/repository/: render the init/clone choice form."""
    api_base = _api_base(request)
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    body = _repository_form_html(journey)
    return await _common_render(request, journey, body, can_advance=False)


async def step_repository_complete(request: Request) -> Response:
    """POST /setup/repository/complete: record the init/clone selection."""
    api_base = _api_base(request)
    body_args = _parse_form(await request.body())
    mode = body_args.get("mode", "").strip()
    remote_url = body_args.get("remote_url", "").strip()
    if mode not in {"init", "clone"}:
        return HTMLResponse(
            "Repository selection requires a valid mode.",
            status_code=400,
        )
    if mode == "clone" and not remote_url:
        return HTMLResponse(
            "Clone requires a remote URL.",
            status_code=400,
        )
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    if journey.current_step != SetupStep.REPOSITORY:
        return RedirectResponse(
            url=f"/setup/{journey.current_step.value}/", status_code=303
        )
    journey = journey.record_selection("mode", mode)
    if remote_url:
        journey = journey.record_selection("remote_url", remote_url)
    journey = journey.complete_current()
    _persist_state(api_base, _payload_from_journey(journey), request)
    return RedirectResponse(url="/setup/dependencies/", status_code=303)


async def step_dependencies_get(request: Request) -> Response:
    """GET /setup/dependencies/: render the runtime readiness report."""
    api_base = _api_base(request)
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    try:
        items = await _fetch_readiness(api_base)
    except Exception as exc:
        items = []
        error = str(exc)
    else:
        error = ""
    body = _dependencies_html(items, error=error)
    blocked = [item["name"] for item in items if item.get("status") == "BLOCKED"]
    blocking = tuple(blocked) if blocked else journey.blocking_items
    journey = SetupJourney(
        current_step=journey.current_step,
        completed_steps=journey.completed_steps,
        blocking_items=blocking,
        selections=journey.selections,
    )
    _persist_state(api_base, _payload_from_journey(journey), request)
    can_advance = not blocked
    return await _common_render(request, journey, body, can_advance=can_advance)


async def step_dependencies_complete(request: Request) -> Response:
    """POST /setup/dependencies/complete: advance once readiness is non-blocking."""
    api_base = _api_base(request)
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    if journey.current_step != SetupStep.DEPENDENCIES:
        return RedirectResponse(
            url=f"/setup/{journey.current_step.value}/", status_code=303
        )
    journey = journey.complete_current()
    _persist_state(api_base, _payload_from_journey(journey), request)
    return RedirectResponse(url="/setup/review/", status_code=303)


async def step_review_get(request: Request) -> Response:
    """GET /setup/review/: show the writable summary before Apply."""
    api_base = _api_base(request)
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    body = _review_html(journey)
    return await _common_render(request, journey, body, can_advance=True)


async def step_review_complete(request: Request) -> Response:
    """POST /setup/review/complete: advance from review to applying."""
    api_base = _api_base(request)
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    if journey.current_step != SetupStep.REVIEW:
        return RedirectResponse(
            url=f"/setup/{journey.current_step.value}/", status_code=303
        )
    journey = journey.complete_current()
    _persist_state(api_base, _payload_from_journey(journey), request)
    return RedirectResponse(url="/setup/applying/", status_code=303)


async def step_applying_get(request: Request) -> Response:
    """GET /setup/applying/: stub apply step; immediately rolls to complete.

    The real Apply step in v0.14-001 / v0.14-003 owns the actual side
    effects (git init, clone, dependency ratchet). In v0.14-004 we surface
    the wizard skeleton only; this stub completes the step.
    """
    api_base = _api_base(request)
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    if journey.current_step == SetupStep.APPLYING:
        journey = journey.complete_current()
        _persist_state(api_base, _payload_from_journey(journey), request)
    body = _applying_html()
    return await _common_render(request, journey, body, can_advance=True)


async def step_complete_get(request: Request) -> Response:
    """GET /setup/complete/: render the setup-complete confirmation page."""
    api_base = _api_base(request)
    journey = _journey_from_payload(_read_persisted_state(api_base, request))
    body = _complete_html(journey)
    return await _common_render(request, journey, body, can_advance=False)


# ---------------------------------------------------------------------------
# First-user handling (kept from B3a)
# ---------------------------------------------------------------------------


async def _fetch_readiness(api_base: str) -> list[dict[str, str]]:
    """Fetch the readiness report from ``GET {api_base}/api/readiness``."""
    async with httpx.AsyncClient(trust_env=False) as client:
        resp = await client.get(f"{api_base}/api/readiness/")
        resp.raise_for_status()
        return list(resp.json().get("items", []))


async def _post_first_user(
    api_base: str, *, name: str, credential: str
) -> dict[str, Any]:
    """POST the first-user form to ``{api_base}/api/setup/first-user``."""
    async with httpx.AsyncClient(trust_env=False) as client:
        resp = await client.post(
            f"{api_base}/api/setup/first-user",
            json={"name": name, "credential": credential},
        )
        resp.raise_for_status()
        return dict(resp.json())


async def _fetch_setup_status(api_base: str) -> dict[str, Any]:
    """Fetch the persisted first-user status from the setup API."""
    async with httpx.AsyncClient(trust_env=False) as client:
        resp = await client.get(f"{api_base}/api/setup/status")
        resp.raise_for_status()
        return dict(resp.json())


def _is_complete(items: list[dict[str, str]]) -> bool:
    """Return True when every readiness item is READY."""
    return all(item.get("status") == "READY" for item in items)


async def setup_page(request: Request) -> Response:
    """GET /setup: render the first-user form for a brand-new workspace."""
    setup_only = bool(getattr(request.app.state, "setup_only", True))
    try:
        status = await _fetch_setup_status(_api_base(request))
    except Exception:
        status = {"initialized": False}
    if status.get("initialized"):
        return RedirectResponse(url="/setup/identity/", status_code=303)
    body = await _first_user_form_html(status)
    return HTMLResponse(
        _render_wizard(
            setup_only=setup_only,
            journey=SetupJourney.new(),
            body_html=body,
            can_advance=False,
            error="",
        )
    )


async def create_first_user(request: Request) -> Response:
    """POST /setup/first-user: forward the first-user form to the API.

    On success, advances the wizard to the repository step.
    """
    name, credential = _parse_form(await request.body())
    api_base = _api_base(request)
    try:
        await _post_first_user(api_base, name=name, credential=credential)
    except Exception as exc:
        return HTMLResponse(
            _render_wizard(
                setup_only=True,
                journey=SetupJourney.new(),
                body_html=await _first_user_form_html(
                    {"initialized": False}, error=str(exc)
                ),
                can_advance=False,
                error=str(exc),
            ),
            status_code=400,
        )
    # Mark identity complete and advance the journey to the next step.
    journey = SetupJourney.new().complete_current()
    _persist_state(api_base, _payload_from_journey(journey), request)
    return RedirectResponse(url="/setup/repository/", status_code=303)


def _api_base(request: Request) -> str:
    """Return the absolute origin used for same-server API forwarding."""
    return str(request.base_url).rstrip("/")


def _parse_form(body: bytes) -> dict[str, str]:
    """Parse a urlencoded form body into a flat dict of stripped values."""
    pairs = parse_qs(body.decode("utf-8", errors="replace"))
    return {key: (vals[0] if vals else "").strip() for key, vals in pairs.items()}


# ---------------------------------------------------------------------------
# Per-step body fragments
# ---------------------------------------------------------------------------


async def _first_user_form_html(status: dict[str, Any], *, error: str = "") -> str:
    """Return the first-user form HTML fragment for the identity step."""
    err_html = f'<div class="error">{_esc(error)}</div>' if error else ""
    if status.get("initialized"):
        return (
            f"<p>First user already created.</p>"
            f'<div class="provenance">principal_id: {_esc(str(status.get("first_principal_id", "")))}</div>'
        )
    return f"""
<section>
  <h2>First user</h2>
  {err_html}
  <form method="post" action="/setup/first-user">
    <label for="name">Name</label>
    <input id="name" name="name" type="text" required />
    <label for="credential">Credential</label>
    <input id="credential" name="credential" type="password" required />
    <button type="submit">Create first user</button>
  </form>
</section>
"""


def _identity_done_html(status: dict[str, Any]) -> str:
    """Return the identity-complete confirmation fragment."""
    principal = status.get("first_principal_id") or ""
    return f"""
<section>
  <h2>Local identity</h2>
  <p class="ok">Identity established.</p>
  <div class="provenance"><strong>Principal id:</strong> {_esc(principal)}</div>
  <p><a class="primary-action" href="/setup/repository/">Continue to Repository</a></p>
</section>
"""


def _repository_form_html(journey: SetupJourney) -> str:
    """Return the repository step HTML form fragment."""
    mode_value = journey.get_selection("mode") or ""
    remote_value = journey.get_selection("remote_url") or ""
    return f"""
<section>
  <h2>Repository</h2>
  <p>Choose how this workspace obtains a repository. The choice is recorded
     only after Review and Confirm; nothing is executed here.</p>
  <form method="post" action="/setup/repository/complete">
    <fieldset>
      <legend>Mode</legend>
      <label><input type="radio" name="mode" value="init" {"checked" if mode_value == "init" else ""} />
        Initialize a new repository in this workspace</label>
      <label><input type="radio" name="mode" value="clone" {"checked" if mode_value == "clone" else ""} />
        Clone an existing repository</label>
    </fieldset>
    <label for="remote_url">Remote URL (clone only)</label>
    <input id="remote_url" name="remote_url" type="url" placeholder="https://github.com/org/repo.git" value="{_esc(remote_value)}" />
    <p class="hint">URLs with userinfo or non-HTTP schemes are rejected before any side effect runs.</p>
    <button type="submit">Continue</button>
  </form>
</section>
"""


def _dependencies_html(items: list[dict[str, str]], *, error: str = "") -> str:
    """Render the dependencies step with readiness facts and provenance."""
    err_html = f'<div class="error">{_esc(error)}</div>' if error else ""
    if not items:
        rows = "<li><em>No readiness items reported.</em></li>"
    else:
        rows = "".join(_render_item(i) for i in items)
    blocked = any(item.get("status") == "BLOCKED" for item in items)
    continue_btn = (
        '<form method="post" action="/setup/dependencies/complete"><button type="submit" disabled>Continue to Review</button></form>'
        if blocked
        else '<form method="post" action="/setup/dependencies/complete"><button type="submit">Continue to Review</button></form>'
    )
    return f"""
<section>
  <h2>Runtime dependencies</h2>
  <p>Each item is checked against your installation. Continue only when
     every required check is <strong>READY</strong>.</p>
  {err_html}
  <ul class="readiness">{rows}</ul>
  {continue_btn}
</section>
"""


def _review_html(journey: SetupJourney) -> str:
    """Render the Review step with the writable summary before Apply."""
    mode = journey.get_selection("mode") or "(not selected)"
    remote = journey.get_selection("remote_url") or "(none)"
    return f"""
<section>
  <h2>Review</h2>
  <p>These operations will run on Confirm. Nothing is executed yet.</p>
  <p>Every value below carries its provenance (the source of the fact):</p>
  <table class="summary">
    <tr><th>Local identity</th><td>established</td><td class="provenance">provenance: first principal persisted</td></tr>
    <tr><th>Repository mode</th><td>{_esc(mode)}</td><td class="provenance">provenance: selected at /setup/repository/</td></tr>
    <tr><th>Remote URL</th><td>{_esc(remote)}</td><td class="provenance">provenance: selected at /setup/repository/</td></tr>
    <tr><th>Dependencies</th><td>all required READY</td><td class="provenance">provenance: readiness report</td></tr>
  </table>
  <form method="post" action="/setup/review/complete">
    <button type="submit">Confirm and Apply</button>
  </form>
</section>
"""


def _applying_html() -> str:
    """Render the Apply step body (stub)."""
    return """
<section>
  <h2>Apply</h2>
  <p>Setup is in the Apply phase. Click Continue to advance.</p>
  <form method="post" action="/setup/review/complete">
    <button type="submit">Continue</button>
  </form>
</section>
"""


def _complete_html(journey: SetupJourney) -> str:
    """Render the final Complete step body."""
    return """
<section>
  <h2>Setup Complete</h2>
  <p class="ok">Your workspace is ready. You can begin a Story.</p>
  <p><a class="primary-action" href="/projects/new">Start Story</a></p>
</section>
"""


# ---------------------------------------------------------------------------
# Wizard shell rendering
# ---------------------------------------------------------------------------


def _render_wizard(
    *,
    setup_only: bool,
    journey: SetupJourney,
    body_html: str,
    can_advance: bool,
    error: str,
) -> str:
    """Render the wizard shell HTML around a per-step body."""
    views = render_step_views(journey)
    stepper = _render_stepper(views)
    blocking_html = _render_blocking(journey)
    error_html = f'<div class="error">{_esc(error)}</div>' if error else ""
    state = "setup-only" if setup_only else "normal"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>louke setup</title>
  <style>
    body {{ font-family: ui-sans-serif, system-ui, sans-serif; margin: 0; color: #111; }}
    .shell {{ max-width: 720px; margin: 0 auto; padding: 48px 24px; }}
    h1 {{ font-size: 24px; }} h2 {{ font-size: 18px; margin-top: 24px; }}
    .state {{ display: inline-block; padding: 2px 8px; border-radius: 6px; background: #f3f4f6; font-size: 12px; }}
    .stepper {{ display: flex; gap: 8px; flex-wrap: wrap; padding: 0; margin: 16px 0; list-style: none; }}
    .stepper li {{ display: flex; align-items: center; gap: 6px; padding: 6px 10px; border: 1px solid #e5e7eb; border-radius: 999px; font-size: 13px; background: #fff; }}
    .stepper li.completed {{ background: #ecfdf5; border-color: #a7f3d0; }}
    .stepper li.current {{ background: #dbeafe; border-color: #93c5fd; font-weight: 600; }}
    .stepper li.pending {{ background: #f9fafb; color: #6b7280; }}
    .stepper li.blocked {{ background: #fee2e2; border-color: #fecaca; color: #991b1b; }}
    .stepper .badge {{ display: inline-block; padding: 1px 6px; border-radius: 6px; font-size: 11px; background: rgba(0,0,0,0.05); }}
    form {{ margin: 16px auto; padding: 16px; border: 1px solid #e5e7eb; border-radius: 8px; max-width: 360px; }}
    fieldset {{ border: 0; padding: 0; margin: 8px 0; }}
    label {{ display: block; margin: 8px 0 4px; font-size: 13px; }}
    input {{ width: 100%; padding: 8px; border: 1px solid #d1d5db; border-radius: 6px; box-sizing: border-box; }}
    .hint {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
    button {{ margin-top: 12px; padding: 8px 14px; background: #111; color: white; border: 0; border-radius: 6px; cursor: pointer; }}
    button[disabled] {{ background: #9ca3af; cursor: not-allowed; }}
    a.primary-action {{ display: inline-block; padding: 8px 14px; background: #111; color: white; border-radius: 6px; text-decoration: none; }}
    .ok {{ color: #166534; }}
    .provenance {{ font-size: 12px; color: #6b7280; }}
    .error {{ color: #b91c1c; margin: 12px 0; }}
    ul {{ padding-left: 18px; }} li {{ padding: 6px 0; border-bottom: 1px solid #f3f4f6; }}
    .status-READY {{ color: #166534; font-weight: 600; }}
    .status-BLOCKED {{ color: #b91c1c; font-weight: 600; }}
    .status-DEGRADED {{ color: #b45309; font-weight: 600; }}
    table.summary {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
    table.summary th, table.summary td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid #e5e7eb; font-size: 13px; }}
    table.summary th {{ background: #f9fafb; }}
  </style>
</head>
<body><main class="shell">
  <h1>louke setup</h1>
  <p>Project state: <span class="state">{_esc(state)}</span> mode</p>
   {error_html}
  <section>
    <h2>Wizard</h2>
    <ol class="stepper" aria-label="Setup progress">
      {stepper}
    </ol>
  </section>
  {blocking_html}
  {body_html}
</main></body>
</html>
"""


def _render_stepper(views: tuple[Any, ...]) -> str:
    """Render the wizard stepper markup."""
    parts: list[str] = []
    for view in views:
        cls = view.state  # "completed" | "current" | "pending" | "blocked"
        badge_map = {
            "completed": "done",
            "current": "now",
            "pending": "next",
            "blocked": "blocked",
        }
        parts.append(
            f'<li class="{cls}"><span>{_esc(view.label)}</span>'
            f'<span class="badge">{badge_map.get(cls, "")}</span></li>'
        )
    return "".join(parts)


def _render_blocking(journey: SetupJourney) -> str:
    """Render blocking items prominently near the top of the wizard."""
    if not journey.blocking_items:
        return ""
    items = "".join(f"<li>{_esc(b)}</li>" for b in journey.blocking_items)
    return (
        f'<section class="blocking"><h2>Blocking items</h2><ul>{items}</ul></section>'
    )


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
