"""Public v0.14 release creation page."""

from __future__ import annotations

from html import escape

from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

from louke.web.auth import CSRF_COOKIE, SESSION_COOKIE, current_user


async def release_new_page(request: Request) -> HTMLResponse | RedirectResponse:
    """Render `/projects/new` without exposing retired workflow selectors."""
    user = current_user(request.app.state.store, request.cookies.get(SESSION_COOKIE))
    if user is None:
        return RedirectResponse(url="/login?next=/projects/new", status_code=303)
    csrf_cookie = request.cookies.get(CSRF_COOKIE, "")
    return HTMLResponse(_render_page(csrf_cookie))


def _render_page(csrf_token: str) -> str:
    """Return the form-first v0.14 release preview/confirm page."""
    token = escape(csrf_token, quote=True)
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>New release</title></head>
<body>
<main>
<h1>Start a release</h1>
<form id="release-form">
<label for="story">What are you building?</label>
<textarea id="story" name="story" required></textarea>
<label for="release_version">Release version</label>
<input id="release_version" name="release_version" value="v0.14.0" required>
<button id="preview" type="submit">Preview</button>
</form>
<section id="result" aria-live="polite"></section>
</main>
<script>
const csrf = "{token}";
const form = document.getElementById("release-form");
const result = document.getElementById("result");
let preview;
form.addEventListener("submit", async (event) => {{
  event.preventDefault();
  const button = document.getElementById("preview");
  button.disabled = true;
  try {{
    const response = await fetch("/api/v14/releases/preview", {{
      method: "POST", headers: {{"Content-Type": "application/json", "X-Louke-CSRF": csrf}},
      body: JSON.stringify({{story: form.story.value, release_version: form.release_version.value}})
    }});
    preview = await response.json();
    result.textContent = response.ok ?
      `Preview ${{preview.release.branch}} (digest ${{preview.request_digest}})` :
      (preview.message || "Preview failed");
    if (response.ok) {{
      const confirm = document.createElement("button");
      confirm.textContent = "Confirm release";
      confirm.onclick = () => confirmRelease(confirm);
      result.appendChild(confirm);
    }}
  }} finally {{ button.disabled = false; }}
}});
async function confirmRelease(button) {{
  button.disabled = true;
  const response = await fetch("/api/v14/releases/confirm", {{
    method: "POST", headers: {{"Content-Type": "application/json", "X-Louke-CSRF": csrf}},
    body: JSON.stringify({{preview_id: preview.preview_id, expected_preview_revision: preview.preview_revision,
      request_digest: preview.request_digest, idempotency_key: crypto.randomUUID()}})
  }});
  const body = await response.json();
  result.textContent = body.continue_url ? `Release status: ${{body.status}}` : (body.message || body.status);
  if (body.continue_url) window.location.assign(body.continue_url);
}}
</script>
</body></html>"""
