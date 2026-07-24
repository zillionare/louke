"""Public release creation page."""

from __future__ import annotations

from html import escape

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from louke.web.auth import SESSION_COOKIE, current_user
from louke.web.csrf_middleware import issue_for_session


async def release_new_page(request: Request) -> HTMLResponse | RedirectResponse:
    """Render `/projects/new` using the workspace release context.

    Args:
        request: Incoming authenticated page request.

    Returns:
        The release creation page, or a login redirect for anonymous users.

    Side Effects:
        None.
    """
    user = current_user(request.app.state.store, request.cookies.get(SESSION_COOKIE))
    if user is None:
        return RedirectResponse(url="/login?next=/projects/new", status_code=303)
    session_cookie = request.cookies.get(SESSION_COOKIE, "")
    revision = 0
    if hasattr(request.app.state, "workspace_root"):
        from louke.web.setup_state import try_read_manifest

        manifest = try_read_manifest(request.app.state.workspace_root)
        if manifest is not None:
            revision = manifest.revision
    csrf = issue_for_session(session_id=session_cookie or "preauth", revision=revision)
    release_version = _default_release_version(request.app.state.store.project_info())
    return HTMLResponse(
        _render_page(
            csrf,
            release_version,
        )
    )


def _default_release_version(project_info: dict[str, object]) -> str:
    """Return the workspace's current release version with a ``v`` prefix.

    Args:
        project_info: Parsed workspace project metadata.

    Returns:
        A release version suitable for the creation form, or an empty string
        when the workspace has no configured version.

    Raises:
        None.
    """
    project = project_info.get("project")
    if not isinstance(project, dict):
        return ""
    version = str(project.get("version") or "").strip()
    return f"v{version.lstrip('v')}" if version else ""


def _render_page(csrf_token: str, release_version: str) -> str:
    """Return the version-agnostic release preview and confirmation page.

    Args:
        csrf_token: CSRF token for mutation requests.
        release_version: Workspace-provided release version shown by default.

    Returns:
        Complete HTML for the release creation page.

    Raises:
        None.
    """
    token = escape(csrf_token, quote=True)
    version = escape(release_version, quote=True)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>New release</title></head>
<body>
<main>
<h1>Start a release</h1>
<form id="release-form">
<label for="story">What are you building?</label>
<textarea id="story" name="story" required></textarea>
<label for="release_version">Release version</label>
<input id="release_version" name="release_version" value="{version}" required>
<button id="preview" type="submit">Preview</button>
</form>
<section id="result" aria-live="polite"></section>
</main>
<script>
const csrf = "{token}";
const form = document.getElementById("release-form");
const result = document.getElementById("result");
let preview;
function createIdempotencyKey() {{
  if (window.crypto && typeof window.crypto.randomUUID === "function") {{
    return window.crypto.randomUUID();
  }}
  return `release-${{Date.now()}}-${{Math.random().toString(36).slice(2)}}`;
}}
form.addEventListener("submit", async (event) => {{
  event.preventDefault();
  const button = document.getElementById("preview");
  button.disabled = true;
  try {{
    const response = await fetch("/api/releases/preview", {{
      method: "POST", headers: {{"Content-Type": "application/json", "X-Louke-CSRF": csrf}},
      body: JSON.stringify({{story: form.story.value, release_version: form.release_version.value}})
    }});
    preview = await response.json();
    result.textContent = response.ok ?
      `Preview ${{preview.release.branch}} (digest ${{preview.request_digest}})` :
      (preview.message || "Preview failed");
    if (response.ok) {{
      const confirm = document.createElement("button");
      confirm.type = "button";
      confirm.textContent = "Confirm release";
      confirm.onclick = () => confirmRelease(confirm);
      result.appendChild(confirm);
    }}
  }} catch (error) {{
    result.textContent = `Preview failed: ${{error.message}}`;
  }} finally {{ button.disabled = false; }}
}});
async function confirmRelease(button) {{
  button.disabled = true;
  result.textContent = "Confirming release…";
  try {{
    const response = await fetch("/api/releases/confirm", {{
      method: "POST", headers: {{"Content-Type": "application/json", "X-Louke-CSRF": csrf}},
      body: JSON.stringify({{preview_id: preview.preview_id, expected_preview_revision: preview.preview_revision,
        request_digest: preview.request_digest, idempotency_key: createIdempotencyKey()}})
    }});
    const body = await response.json();
    if (!response.ok || !body.request_id) {{
      result.textContent = body.message || body.status || "Release confirmation failed";
      button.disabled = false;
      return;
    }}
    await watchStatus(body.request_id);
  }} catch (error) {{
    result.textContent = `Release confirmation failed: ${{error.message}}`;
    button.disabled = false;
  }}
}}
async function watchStatus(requestId) {{
  try {{
    const response = await fetch(`/api/releases/requests/${{requestId}}`);
    const body = await response.json();
    if (!response.ok) {{
      result.textContent = body.message || "Could not read release status";
      return;
    }}
    result.textContent = `Release status: ${{body.status}}`;
    if (body.status === "ready" && body.continue_url) {{
      window.location.assign(body.continue_url);
      return;
    }}
  if (["blocked", "conflict"].includes(body.status)) {{
    const detail = body.backlog?.reason || body.main_check?.remediation ||
      body.foundation?.remediation || "Resolve the reported issue, then recheck.";
    result.append(` — ${{detail}}`);
    const projects = document.createElement("a");
    projects.href = "/projects";
    projects.textContent = " Projects and Backlog";
    result.appendChild(projects);
    const retry = document.createElement("button");
    retry.type = "button";
    retry.textContent = "Recheck Foundation";
    retry.onclick = async () => {{
      retry.disabled = true;
      const checked = await fetch(`/api/releases/requests/${{requestId}}/recheck`, {{
        method: "POST", headers: {{"X-Louke-CSRF": csrf}}
      }});
      const next = await checked.json();
      if (next.continue_url) window.location.assign(next.continue_url);
      else await watchStatus(requestId);
    }};
    result.appendChild(retry);
    return;
  }}
    window.setTimeout(() => watchStatus(requestId), 1000);
  }} catch (error) {{
    result.textContent = `Could not read release status: ${{error.message}}`;
  }}
}}
</script>
</body></html>"""
