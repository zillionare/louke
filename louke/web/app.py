from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response, StreamingResponse
from starlette.routing import Route

from .auth import SESSION_COOKIE, AuthenticatedUser, authenticate_user, current_user, issue_session_cookie, register_user
from .bindings import get_bindings_payload, save_bindings_payload
from .documents import (
    get_doc_payload,
    get_wiki_payload,
    mutate_discussion,
    render_preview_payload,
    save_doc_payload,
    save_wiki_payload,
    toggle_status_payload,
)
from .events import EventBroker
from .store import ConflictError, ProjectStore, ValidationError


def create_app(project_root: str | Path | None = None) -> Starlette:
    if project_root is None:
        project_root = Path.cwd()
    store = ProjectStore(Path(project_root))
    broker = EventBroker()
    app = Starlette(
        debug=False,
        routes=[
            Route("/assets/{asset_path:path}", endpoint=asset_file),
            Route("/login", endpoint=login_page),
            Route("/", endpoint=home_page),
            Route("/models", endpoint=models_page),
            Route("/wiki", endpoint=wiki_index_page),
            Route("/wiki/{page:path}", endpoint=wiki_editor_page),
            Route("/docs/{spec_id:str}/{doc_name:str}", endpoint=doc_editor_page),
            Route("/health", endpoint=health),
            Route("/api/auth/register", endpoint=api_auth_register, methods=["POST"]),
            Route("/api/auth/login", endpoint=api_auth_login, methods=["POST"]),
            Route("/api/auth/logout", endpoint=api_auth_logout, methods=["POST"]),
            Route("/api/bindings", endpoint=api_bindings, methods=["GET", "PUT"]),
            Route("/api/wiki", endpoint=api_wiki_index, methods=["GET"]),
            Route("/api/wiki/{page:path}", endpoint=api_wiki_page, methods=["GET", "PUT"]),
            Route("/api/docs/{spec_id:str}/{doc_name:str}", endpoint=api_doc, methods=["GET", "PUT"]),
            Route("/api/docs/{spec_id:str}/{doc_name:str}/toggle-status", endpoint=api_toggle_status, methods=["POST"]),
            Route("/api/specs", endpoint=api_specs, methods=["GET"]),
            Route("/api/render", endpoint=api_render, methods=["POST"]),
            Route("/api/discussions/mutate", endpoint=api_discussion_mutate, methods=["POST"]),
            Route("/api/events", endpoint=api_events, methods=["GET"]),
        ],
    )
    app.state.store = store
    app.state.broker = broker
    return app


async def health(request: Request) -> JSONResponse:
    return JSONResponse(request.app.state.store.health_payload())


async def asset_file(request: Request) -> Response:
    asset_name = request.path_params["asset_path"]
    asset_path = (_assets_dir() / asset_name).resolve()
    assets_root = _assets_dir().resolve()
    if not str(asset_path).startswith(str(assets_root)) or not asset_path.exists() or not asset_path.is_file():
        return JSONResponse({"error": "asset not found"}, status_code=404)
    return FileResponse(asset_path)


async def login_page(request: Request) -> HTMLResponse | RedirectResponse:
    store: ProjectStore = request.app.state.store
    user = _current_user(request)
    if user is not None:
        return RedirectResponse(url="/", status_code=303)
    next_path = request.query_params.get("next") or "/"
    return HTMLResponse(_login_shell(lang=_ui_language(request), next_path=next_path, has_users=bool(store.list_users())))


async def home_page(request: Request) -> HTMLResponse:
    user = _require_page_user(request)
    if isinstance(user, Response):
        return user
    store: ProjectStore = request.app.state.store
    lang = _ui_language(request)
    spec_id = store.spec_id
    body = f"""
    <section class="hero">
      <span class="eyebrow">{_escape(_t(lang, "home.eyebrow"))}</span>
      <h1>louke Web Workbench</h1>
      <p class="lede">{_escape(_t(lang, "home.lede_before"))}<code>{_escape(spec_id)}</code>{_escape(_t(lang, "home.lede_after"))}</p>
    </section>
    <section class="grid cards">
      <a class="card card-link" href="/models">
        <div class="card-kicker">models</div>
        <h2>{_escape(_t(lang, "nav.models"))}</h2>
        <p>{_escape(_t(lang, "home.models_desc"))}</p>
      </a>
      <a class="card card-link" href="/docs/{_escape(spec_id)}/spec">
        <div class="card-kicker">docs</div>
        <h2>{_escape(_t(lang, "nav.docs"))}</h2>
        <p>{_escape(_t(lang, "home.docs_desc"))}</p>
      </a>
      <a class="card card-link" href="/wiki">
        <div class="card-kicker">wiki</div>
        <h2>wiki</h2>
        <p>{_escape(_t(lang, "home.wiki_desc"))}</p>
      </a>
    </section>
    """
    return HTMLResponse(_page_shell("louke web", store, user, lang, "home", body))


async def models_page(request: Request) -> HTMLResponse:
    user = _require_page_user(request)
    if isinstance(user, Response):
        return user
    store: ProjectStore = request.app.state.store
    lang = _ui_language(request)
    body = f"""
    <header class="page-header">
      <div>
        <span class="eyebrow">Models</span>
        <h1>{_escape(_t(lang, "nav.models"))}</h1>
        <p class="lede">{_escape(_t(lang, "models.lede"))}</p>
      </div>
      <div id="meta" class="meta"></div>
    </header>
    <div id="banner" class="banner" hidden></div>
    <main class="grid models-grid">
      <section class="panel">
        <h2>{_escape(_t(lang, "models.catalog"))}</h2>
        <div id="model-list" class="model-list"></div>
      </section>
      <section class="panel">
        <h2>{_escape(_t(lang, "models.roles"))}</h2>
        <div id="role-list" class="binding-list"></div>
      </section>
      <section class="panel">
        <h2>{_escape(_t(lang, "models.agents"))}</h2>
        <div id="agent-list" class="binding-list"></div>
      </section>
    </main>
    """
    script = _models_page_script(lang)
    return HTMLResponse(_page_shell(_t(lang, "nav.models"), store, user, lang, "models", body, script=script))


async def wiki_index_page(request: Request) -> HTMLResponse:
    user = _require_page_user(request)
    if isinstance(user, Response):
        return user
    store: ProjectStore = request.app.state.store
    lang = _ui_language(request)
    pages = store.list_wiki_pages()
    items = []
    for page in pages:
        items.append(
            f'<a class="card card-link wiki-card" href="/wiki/{_quote_path(page["page"])}">'
            f'<h2>{_escape(page["page"])}</h2>'
            f'<p>{_escape(page["updated_at"] or _t(lang, "meta.not_recorded"))}</p>'
            f"</a>"
        )
    body = f"""
    <header class="page-header">
      <div>
        <span class="eyebrow">Wiki</span>
        <h1>wiki</h1>
        <p class="lede">{_escape(_t(lang, "wiki.index_lede"))}</p>
      </div>
      <div class="toolbar-actions">
        <input id="new-page" placeholder="guides/getting-started" />
        <button id="create-page">{_escape(_t(lang, "wiki.create_open"))}</button>
      </div>
    </header>
    <section class="grid cards">
      {''.join(items) or f'<div class="card"><p>{_escape(_t(lang, "wiki.empty"))}</p></div>'}
    </section>
    """
    script = """
    <script>
    document.getElementById('create-page').addEventListener('click', () => {
      const value = document.getElementById('new-page').value.trim();
      if (!value) return;
      location.href = `/wiki/${value.split('/').map(encodeURIComponent).join('/')}`;
    });
    </script>
    """
    return HTMLResponse(_page_shell("wiki", store, user, lang, "wiki", body, script=script))


async def wiki_editor_page(request: Request) -> HTMLResponse:
    user = _require_page_user(request)
    if isinstance(user, Response):
        return user
    store: ProjectStore = request.app.state.store
    lang = _ui_language(request)
    page = request.path_params["page"]
    encoded_page = _quote_path(page)
    body = f"""
    <header class="page-header">
      <div>
        <span class="eyebrow">Wiki</span>
        <h1>wiki: <code>{_escape(page)}</code></h1>
        <p class="lede">{_escape(_t(lang, "wiki.editor_lede"))}</p>
      </div>
      <div class="toolbar-actions">
        <button id="save">{_escape(_t(lang, "common.save"))}</button>
        <button id="reload">{_escape(_t(lang, "common.reload"))}</button>
      </div>
    </header>
    <div id="banner" class="banner" hidden></div>
    <div id="meta" class="meta"></div>
    <main class="grid editor-grid">
      <section class="panel">
        <h2>{_escape(_t(lang, "common.markdown"))}</h2>
        <textarea id="source" spellcheck="false"></textarea>
      </section>
      <section class="panel">
        <div class="panel-header">
          <h2>{_escape(_t(lang, "common.preview"))}</h2>
        </div>
        <div id="preview" class="preview"></div>
      </section>
    </main>
    """
    script = _editor_page_script(
        api_path=f"/api/wiki/{encoded_page}",
        kind="wiki",
        title=f"wiki:{page}",
        doc_name="",
        discussion_enabled=False,
        actor_name=user.username,
        lang=lang,
    )
    return HTMLResponse(
        _page_shell(f"wiki {page}", store, user, lang, "wiki", body, script=script, current_wiki_page=page)
    )


async def doc_editor_page(request: Request) -> HTMLResponse:
    user = _require_page_user(request)
    if isinstance(user, Response):
        return user
    store: ProjectStore = request.app.state.store
    lang = _ui_language(request)
    spec_id = request.path_params["spec_id"]
    doc_name = request.path_params["doc_name"]
    body = f"""
    <header class="page-header">
      <div>
        <span class="eyebrow">Design Docs</span>
        <h1>{_escape(_t(lang, "docs.title"))}: <code>{_escape(doc_name)}</code></h1>
        <p class="lede">{_escape(_t(lang, "docs.lede"))}</p>
      </div>
      <div class="toolbar-actions">
        <button id="focus-toggle" class="focus-toggle-btn">{_escape(_t(lang, "docs.focus_content"))}</button>
        <button id="toggle-collapse">{_escape(_t(lang, "docs.toggle_collapse"))}</button>
        <button id="save">{_escape(_t(lang, "common.save"))}</button>
        <button id="reload">{_escape(_t(lang, "common.reload"))}</button>
        <span id="autosave-indicator" class="autosave-indicator" hidden></span>
      </div>
    </header>
    <div id="banner" class="banner" hidden></div>
    <div id="meta" class="meta"></div>
    <main class="grid editor-grid">
      <section class="panel">
        <h2>{_escape(_t(lang, "common.markdown"))}</h2>
        <textarea id="source" spellcheck="false"></textarea>
      </section>
      <section class="panel">
        <div class="panel-header">
          <h2>{_escape(_t(lang, "common.preview"))}</h2>
          <span class="muted">{_escape(_t(lang, "docs.inline_hint"))}</span>
        </div>
        <div id="preview-shell" class="preview-shell focus-content">
          <div id="preview" class="preview"></div>
        </div>
        <div id="cards" class="cards-list"></div>
        <section id="discussion-tools" class="discussion-tools">
          <h2>{_escape(_t(lang, "docs.discussion_actions"))}</h2>
          <div class="inline-form">
            <input id="new-anchor-line" type="number" min="1" placeholder="anchor line" />
            <input id="new-discussion-body" placeholder="{_escape(_t(lang, 'docs.new_discussion_placeholder'))}" />
            <button id="start-discussion">{_escape(_t(lang, "docs.start_discussion"))}</button>
          </div>
          <div id="thread-list" class="thread-list"></div>
        </section>
      </section>
    </main>
    """
    script = _editor_page_script(
        api_path=f"/api/docs/{spec_id}/{doc_name}",
        kind="doc",
        title=f"{spec_id}:{doc_name}",
        doc_name=doc_name,
        discussion_enabled=True,
        actor_name=user.username,
        lang=lang,
    )
    return HTMLResponse(
        _page_shell(f"{spec_id} {doc_name}", store, user, lang, "docs", body, script=script, current_doc_name=doc_name)
    )


async def api_auth_register(request: Request) -> JSONResponse:
    store: ProjectStore = request.app.state.store
    payload = await request.json()
    try:
        user = register_user(
            store,
            username=str(payload.get("username") or ""),
            password=str(payload.get("password") or ""),
        )
    except ValidationError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    response = JSONResponse({"ok": True, "username": user.username})
    _set_session_cookie(response, store, user.username)
    return response


async def api_auth_login(request: Request) -> JSONResponse:
    store: ProjectStore = request.app.state.store
    payload = await request.json()
    try:
        user = authenticate_user(
            store,
            username=str(payload.get("username") or ""),
            password=str(payload.get("password") or ""),
        )
    except ValidationError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    response = JSONResponse({"ok": True, "username": user.username})
    _set_session_cookie(response, store, user.username)
    return response


async def api_auth_logout(request: Request) -> JSONResponse:
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


async def api_bindings(request: Request) -> JSONResponse:
    user = _require_api_user(request)
    if isinstance(user, Response):
        return user
    store: ProjectStore = request.app.state.store
    broker: EventBroker = request.app.state.broker
    if request.method == "GET":
        return JSONResponse(get_bindings_payload(store))
    payload = await request.json()
    actor_name = user.username
    try:
        response = save_bindings_payload(store, payload, actor_name)
    except ConflictError as exc:
        broker.publish_nowait(
            "conflict.detected",
            {
                "target": ".louke/models.json",
                "actor_name": actor_name,
                "updated_at": store.read_bindings()[2].updated_at,
            },
        )
        return JSONResponse({"error": str(exc)}, status_code=409)
    except ValidationError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    broker.publish_nowait(
        "bindings.updated",
        {"updated_at": response["updated_at"], "actor_name": response["last_modified_by"]},
    )
    return JSONResponse(response)


async def api_wiki_index(request: Request) -> JSONResponse:
    user = _require_api_user(request)
    if isinstance(user, Response):
        return user
    return JSONResponse({"pages": request.app.state.store.list_wiki_pages()})


async def api_wiki_page(request: Request) -> JSONResponse:
    user = _require_api_user(request)
    if isinstance(user, Response):
        return user
    store: ProjectStore = request.app.state.store
    broker: EventBroker = request.app.state.broker
    page = request.path_params["page"]
    if request.method == "GET":
        try:
            return JSONResponse(get_wiki_payload(store, page))
        except FileNotFoundError:
            if request.headers.get("accept", "").startswith("application/json"):
                return JSONResponse(
                    {
                        "page": page,
                        "path": store.relative_path(store.wiki_page_path(page)),
                        "body_md": "",
                        "rendered_html": "",
                        "version_token": "new",
                        "updated_at": "",
                        "last_modified_by": "",
                    }
                )
            raise
    payload = await request.json()
    actor_name = user.username
    try:
        response = save_wiki_payload(
            store,
            page=page,
            body_md=str(payload.get("body_md") or ""),
            version_token=str(payload.get("version_token") or ""),
            actor_name=actor_name,
        )
    except ConflictError as exc:
        broker.publish_nowait(
            "conflict.detected",
            {
                "target": store.relative_path(store.wiki_page_path(page)),
                "actor_name": actor_name,
                "updated_at": store.latest_activity(store.wiki_page_path(page)).updated_at,
            },
        )
        return JSONResponse({"error": str(exc)}, status_code=409)
    except ValidationError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    broker.publish_nowait(
        "wiki.updated",
        {
            "target": response["path"],
            "updated_at": response["updated_at"],
            "actor_name": response["last_modified_by"],
        },
    )
    return JSONResponse(response)


async def api_doc(request: Request) -> JSONResponse:
    user = _require_api_user(request)
    if isinstance(user, Response):
        return user
    store: ProjectStore = request.app.state.store
    broker: EventBroker = request.app.state.broker
    spec_id = request.path_params["spec_id"]
    doc_name = request.path_params["doc_name"]
    if request.method == "GET":
        try:
            return JSONResponse(get_doc_payload(store, spec_id, doc_name))
        except (FileNotFoundError, ValidationError) as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
    payload = await request.json()
    actor_name = user.username
    try:
        response = save_doc_payload(
            store,
            spec_id=spec_id,
            doc_name=doc_name,
            body_md=str(payload.get("body_md") or ""),
            version_token=str(payload.get("version_token") or ""),
            actor_name=actor_name,
            force=bool(payload.get("force")),
        )
    except ConflictError as exc:
        try:
            target = store.relative_path(store.doc_path(spec_id, doc_name))
            updated_at = store.latest_activity(store.doc_path(spec_id, doc_name)).updated_at
        except Exception:
            target = ""
            updated_at = ""
        broker.publish_nowait(
            "conflict.detected",
            {"target": target, "actor_name": actor_name, "updated_at": updated_at},
        )
        return JSONResponse({"error": str(exc)}, status_code=409)
    except ValidationError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    broker.publish_nowait(
        "document.updated",
        {
            "target": response["path"],
            "updated_at": response["updated_at"],
            "actor_name": response["last_modified_by"],
        },
    )
    return JSONResponse(response)


async def api_toggle_status(request: Request) -> JSONResponse:
    user = _require_api_user(request)
    if isinstance(user, Response):
        return user
    store: ProjectStore = request.app.state.store
    spec_id = request.path_params["spec_id"]
    doc_name = request.path_params["doc_name"]
    payload = await request.json()
    fr_id = str(payload.get("fr_id") or "")
    field = str(payload.get("field") or "")
    version_token = str(payload.get("version_token") or "")
    if field not in ("valid", "testable", "decided") or not fr_id:
        return JSONResponse({"error": "invalid fr_id or field"}, status_code=400)
    try:
        response = toggle_status_payload(
            store, spec_id=spec_id, doc_name=doc_name,
            fr_id=fr_id, field=field,
            version_token=version_token, actor_name=user.username,
        )
    except ConflictError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    except (FileNotFoundError, ValidationError) as exc:
        return JSONResponse({"error": str(exc)}, status_code=404)
    return JSONResponse(response)


async def api_specs(request: Request) -> JSONResponse:
    user = _require_api_user(request)
    if isinstance(user, Response):
        return user
    store: ProjectStore = request.app.state.store
    return JSONResponse({"specs": store.list_spec_ids()})


async def api_render(request: Request) -> JSONResponse:
    user = _require_api_user(request)
    if isinstance(user, Response):
        return user
    payload = await request.json()
    return JSONResponse(
        render_preview_payload(
            kind=str(payload.get("kind") or ""),
            doc_name=str(payload.get("doc_name") or ""),
            body_md=str(payload.get("body_md") or ""),
        )
    )


async def api_discussion_mutate(request: Request) -> JSONResponse:
    user = _require_api_user(request)
    if isinstance(user, Response):
        return user
    store: ProjectStore = request.app.state.store
    broker: EventBroker = request.app.state.broker
    payload = await request.json()
    actor_name = user.username
    try:
        response = mutate_discussion(
            store,
            target_kind=str(payload.get("target_kind") or ""),
            target_path=str(payload.get("target_path") or ""),
            version_token=str(payload.get("version_token") or ""),
            actor_name=actor_name,
            action=str(payload.get("action") or ""),
            anchor=dict(payload.get("anchor") or {}),
            payload=dict(payload.get("payload") or {}),
        )
    except ConflictError as exc:
        broker.publish_nowait(
            "conflict.detected",
            {
                "target": str(payload.get("target_path") or ""),
                "actor_name": actor_name,
                "updated_at": "",
            },
        )
        return JSONResponse({"error": str(exc)}, status_code=409)
    except (ValidationError, FileNotFoundError, PermissionError, ValueError) as exc:
        status = 422 if isinstance(exc, PermissionError | ValueError) else 400
        return JSONResponse({"error": str(exc)}, status_code=status)
    event_name = "document.updated" if payload.get("target_kind") == "doc" else "wiki.updated"
    broker.publish_nowait(
        event_name,
        {
            "target": response["path"],
            "updated_at": response["updated_at"],
            "actor_name": response["last_modified_by"],
        },
    )
    return JSONResponse(response)


async def api_events(request: Request) -> StreamingResponse:
    user = _require_api_user(request)
    if isinstance(user, Response):
        return user
    broker: EventBroker = request.app.state.broker
    queue = broker.subscribe()

    async def stream():
        try:
            yield b": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                except TimeoutError:
                    yield b": keepalive\n\n"
                    continue
                event = message["event"]
                data = json.dumps(message["data"], ensure_ascii=False)
                yield f"event: {event}\ndata: {data}\n\n".encode("utf-8")
        finally:
            broker.unsubscribe(queue)

    return StreamingResponse(stream(), media_type="text/event-stream")


def _current_user(request: Request) -> AuthenticatedUser | None:
    store: ProjectStore = request.app.state.store
    return current_user(store, request.cookies.get(SESSION_COOKIE))


def _require_page_user(request: Request) -> AuthenticatedUser | Response:
    user = _current_user(request)
    if user is not None:
        return user
    next_path = request.url.path
    if request.url.query:
        next_path = f"{next_path}?{request.url.query}"
    return RedirectResponse(url=f"/login?{urlencode({'next': next_path})}", status_code=303)


def _require_api_user(request: Request) -> AuthenticatedUser | Response:
    user = _current_user(request)
    if user is not None:
        return user
    return JSONResponse({"error": "login required"}, status_code=401)


def _ui_language(request: Request) -> str:
    raw = str(request.headers.get("accept-language") or "").strip().lower()
    if not raw:
        return "en"
    for token in raw.split(","):
        code = token.split(";")[0].strip()
        if code.startswith("zh"):
            return "zh"
        if code.startswith("en"):
            return "en"
    return "en"


def _set_session_cookie(response: Response, store: ProjectStore, username: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        issue_session_cookie(store, username),
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        path="/",
    )


def _page_shell(
    title: str,
    store: ProjectStore,
    user: AuthenticatedUser,
    lang: str,
    section: str,
    body: str,
    script: str = "",
    current_doc_name: str = "",
    current_wiki_page: str = "",
) -> str:
    sidebar = _sidebar_html(store, user, lang, section, current_doc_name, current_wiki_page)
    return f"""<!DOCTYPE html>
<html lang="{_escape('zh-CN' if lang == 'zh' else 'en')}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #fafafa;
      --surface: #ffffff;
      --surface-alt: #f3f4f6;
      --sidebar: #fcfcfc;
      --text: #111111;
      --muted: #6b7280;
      --border: #e5e7eb;
      --border-strong: #d1d5db;
      --accent: #111111;
      --danger: #b91c1c;
      --success: #166534;
      --shadow: 0 1px 2px rgba(17, 24, 39, 0.04);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }}
    a {{ color: inherit; text-decoration: none; }}
    code, pre, textarea, input, .mono {{
      font-family: "SFMono-Regular", ui-monospace, Menlo, Consolas, monospace;
    }}
    code {{
      background: var(--surface-alt);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 1px 5px;
    }}
    .app-shell {{
      min-height: 100vh;
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr);
    }}
    .sidebar {{
      position: sticky;
      top: 0;
      align-self: start;
      height: 100vh;
      overflow: auto;
      padding: 20px 16px;
      background: var(--sidebar);
      border-right: 1px solid var(--border);
    }}
    .brand {{
      display: block;
      padding: 12px 14px;
      margin-bottom: 18px;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }}
    .brand-title {{
      font-size: 14px;
      font-weight: 700;
      letter-spacing: 0.02em;
    }}
    .brand-subtitle {{
      margin-top: 4px;
      color: var(--muted);
      font-size: 12px;
    }}
    .user-card {{
      margin-bottom: 18px;
      padding: 12px 14px;
      border: 1px solid var(--border);
      border-radius: 14px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }}
    .user-row {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 10px;
    }}
    .user-name {{
      font-weight: 600;
      font-size: 14px;
    }}
    .ghost-button {{
      background: transparent;
      color: var(--muted);
      border: 0;
      padding: 6px 10px;
      font-size: 13px;
      border-radius: 8px;
      cursor: pointer;
      min-height: 32px;
    }}
    .ghost-button:hover {{
      background: var(--surface-alt);
      color: var(--text);
    }}
    .nav-section {{
      margin-top: 18px;
    }}
    .nav-label {{
      margin: 0 0 8px;
      padding: 0 10px;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .nav-link {{
      display: block;
      padding: 10px 12px;
      border-radius: 10px;
      color: var(--muted);
    }}
    .nav-link:hover {{
      background: var(--surface-alt);
      color: var(--text);
    }}
    .nav-link.active {{
      background: var(--text);
      color: #ffffff;
    }}
    .nav-sublinks {{
      margin-top: 6px;
      padding-left: 8px;
      border-left: 1px solid var(--border);
    }}
    .nav-subgroup {{
      margin-bottom: 10px;
    }}
    .nav-subtitle {{
      padding: 4px 10px;
      color: var(--muted);
      font-size: 12px;
    }}
    .nav-sublink {{
      display: block;
      margin: 2px 0;
      padding: 8px 10px;
      border-radius: 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    .nav-sublink:hover {{
      background: var(--surface-alt);
      color: var(--text);
    }}
    .nav-sublink.active {{
      background: var(--surface);
      color: var(--text);
      border: 1px solid var(--border);
    }}
    .workspace {{
      min-width: 0;
      padding: 28px;
    }}
    .workspace-inner {{
      max-width: 1600px;
      margin: 0 auto;
    }}
    .page-header, .panel-header {{
      display: flex; justify-content: space-between; gap: 16px; align-items: center;
    }}
    .toolbar-actions, .inline-form {{ display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }}
    .focus-toggle-btn {{ position: relative; padding-right: 28px; }}
    .focus-toggle-btn::after {{
      content: '⇄'; position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
      font-size: 12px; opacity: 0.5;
    }}
    .focus-toggle-btn.state-discussion {{ background: var(--surface); color: var(--text); border-color: var(--border-strong); }}
    .autosave-indicator {{ font-size: 12px; color: var(--muted); padding: 0 4px; }}
    .grid {{ display: grid; gap: 16px; }}
    .editor-grid {{ grid-template-columns: minmax(420px, 1fr) minmax(420px, 1fr); }}
    .models-grid {{ grid-template-columns: 280px 1fr 1fr; }}
    .cards {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); margin-top: 16px; }}
    .panel, .card, .banner {{
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      box-shadow: var(--shadow);
    }}
    .card-link:hover {{
      border-color: var(--border-strong);
      transform: translateY(-1px);
    }}
    .hero {{ margin-bottom: 18px; }}
    .eyebrow {{
      display: inline-block;
      margin-bottom: 10px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    h1, h2, h3 {{ margin: 0 0 10px; letter-spacing: -0.02em; }}
    h1 {{ font-size: 30px; }}
    h2 {{ font-size: 18px; }}
    p {{ line-height: 1.6; }}
    .lede {{ margin: 0; color: var(--muted); max-width: 900px; }}
    .card-kicker {{
      margin-bottom: 12px;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }}
    .muted {{ color: var(--muted); }}
    textarea, input {{
      width: 100%;
      background: var(--surface);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      font: inherit;
    }}
    textarea {{ min-height: 70vh; resize: vertical; }}
    button {{
      background: var(--text);
      color: white;
      border: 1px solid var(--text);
      padding: 10px 14px;
      border-radius: 8px;
      cursor: pointer;
      font: inherit;
    }}
    button:hover {{
      opacity: 0.92;
    }}
    .preview {{ min-height: 70vh; overflow: auto; }}
    .preview-shell.focus-content .discussion-block {{ opacity: 0.35; }}
    .preview-shell.focus-discussion .markdown-block {{ opacity: 0.35; }}
    .preview-shell.collapsed .discussion-block {{ display: none; }}
    .discussion-block, .discussion-tools, .cards-list {{ margin-top: 16px; }}
    .discussion-thread {{
      border-left: 1.5px solid rgba(15, 23, 42, 0.18);
      padding-left: 12px;
      margin: 14px 0;
    }}
    .discussion-status {{
      margin-left: 8px;
      color: var(--success);
      border: 1px solid var(--success);
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
    }}
    .discussion-reply {{ margin: 10px 0 0 12px; padding-left: 12px; border-left: 0.5px dashed rgba(226, 232, 240, 0.9); }}
    .cards-list {{ display: grid; gap: 12px; }}
    .requirement-card {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      background: var(--surface-alt);
    }}
    .chip-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
    .chip {{ border: 1px solid var(--border); border-radius: 999px; padding: 2px 8px; color: var(--muted); }}
    .chip-toggle {{
      border: 1px solid var(--border); border-radius: 999px; padding: 4px 10px;
      font-size: 12px; cursor: pointer; background: var(--surface); color: var(--muted);
      opacity: 0.5;
    }}
    .chip-toggle.on {{ opacity: 1; border-color: var(--success, #16a34a); color: var(--success, #16a34a); }}
    .chip-toggle:hover {{ opacity: 0.8; }}
    .xref-link {{
      color: var(--muted); text-decoration: underline dashed; text-underline-offset: 2px;
      cursor: pointer; font-weight: 500;
    }}
    .xref-link:hover {{ color: var(--text); text-decoration: underline; }}
    .xref-link.xref-cross {{ border-bottom: 1px dotted var(--border-strong); }}
    .xref-back {{
      position: sticky; top: 0; z-index: 10; display: inline-flex; align-items: center; gap: 4px;
      background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
      padding: 4px 10px; font-size: 12px; cursor: pointer; color: var(--muted);
      margin-bottom: 8px;
    }}
    .xref-back:hover {{ background: var(--surface-alt); color: var(--text); }}
    .model-chip {{
      border: 1px solid var(--border-strong);
      background: var(--surface-alt);
      border-radius: 8px;
      padding: 10px;
      margin-bottom: 8px;
      cursor: grab;
    }}
    .binding-card {{
      border: 1px dashed var(--border);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 10px;
      background: var(--surface-alt);
    }}
    .binding-card.drag-over {{ border-color: var(--text); background: #f5f5f5; }}
    .binding-meta {{ color: var(--muted); font-size: 13px; }}
    .meta {{ margin: 12px 0; color: var(--muted); }}
    .thread-item {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      margin-top: 10px;
      background: var(--surface-alt);
    }}
    .banner {{ margin: 12px 0; border-color: #fecaca; color: var(--danger); background: #fef2f2; }}
    pre {{ overflow: auto; background: var(--surface-alt); padding: 12px; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid var(--border); padding: 8px; text-align: left; }}
    blockquote {{
      margin: 16px 0;
      padding-left: 16px;
      border-left: 2px solid var(--border-strong);
      color: var(--muted);
    }}
    @media (max-width: 1100px) {{
      .app-shell {{ grid-template-columns: 1fr; }}
      .sidebar {{
        position: static;
        height: auto;
        border-right: 0;
        border-bottom: 1px solid var(--border);
      }}
      .workspace {{ padding: 20px; }}
      .editor-grid, .models-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body data-actor-name="{_escape(user.username)}" data-ui-lang="{_escape(lang)}">
  <div class="app-shell">
    <aside class="sidebar">
      {sidebar}
    </aside>
    <main class="workspace">
      <div class="workspace-inner">
        {body}
      </div>
    </main>
  </div>
  {script}
  <script>
    document.querySelectorAll('[data-action="logout"]').forEach((button) => {{
      button.addEventListener('click', async () => {{
        await fetch('/api/auth/logout', {{ method: 'POST' }});
        location.href = '/login';
      }});
    }});
  </script>
</body>
</html>"""


def _sidebar_html(
    store: ProjectStore,
    user: AuthenticatedUser,
    lang: str,
    section: str,
    current_doc_name: str,
    current_wiki_page: str,
) -> str:
    spec_id = store.spec_id
    docs = store.list_spec_documents(spec_id)
    wiki_groups = _group_wiki_pages(store.list_wiki_pages(), lang)
    return f"""
    <a class="brand" href="/">
      <div class="brand-title">louke / web</div>
      <div class="brand-subtitle">{_escape(_t(lang, "sidebar.spec"))}: {_escape(spec_id)}</div>
    </a>
    <div class="user-card">
      <div class="nav-label">{_escape(_t(lang, "sidebar.signed_in"))}</div>
      <div class="user-row">
        <div class="user-name">{_escape(user.username)}</div>
        <button type="button" class="ghost-button" data-action="logout">{_escape(_t(lang, "sidebar.logout"))}</button>
      </div>
    </div>
    <div class="nav-section">
      <div class="nav-label">{_escape(_t(lang, "sidebar.main"))}</div>
      <a class="{_nav_link_class(section == 'models')}" href="/models">{_escape(_t(lang, "nav.models"))}</a>
      <a class="{_nav_link_class(section == 'docs')}" href="/docs/{_escape(spec_id)}/spec">{_escape(_t(lang, "nav.docs"))}</a>
      {_docs_sublinks(spec_id, docs, current_doc_name)}
      <a class="{_nav_link_class(section == 'wiki')}" href="/wiki">wiki</a>
      {_wiki_sublinks(wiki_groups, current_wiki_page)}
    </div>
    """


def _docs_sublinks(spec_id: str, docs: list[dict[str, str]], current_doc_name: str) -> str:
    if not docs:
        return ""
    links = []
    for item in docs:
        links.append(
            f'<a class="{_nav_sublink_class(item["doc_name"] == current_doc_name)}" '
            f'href="/docs/{_escape(spec_id)}/{_escape(item["doc_name"])}">{_escape(item["doc_name"])}</a>'
        )
    return f"""
    <div class="nav-sublinks">
      <div class="nav-subgroup">
        <div class="nav-subtitle">{_escape(spec_id)}</div>
        {''.join(links)}
      </div>
    </div>
    """


def _wiki_sublinks(groups: dict[str, list[dict[str, str]]], current_wiki_page: str) -> str:
    if not groups:
        return ""
    chunks = []
    for group_name, items in groups.items():
        links = []
        for item in items:
            links.append(
                f'<a class="{_nav_sublink_class(item["page"] == current_wiki_page)}" '
                f'href="/wiki/{_quote_path(item["page"])}">{_escape(item["label"])}</a>'
            )
        chunks.append(
            f'<div class="nav-subgroup"><div class="nav-subtitle">{_escape(group_name)}</div>{"".join(links)}</div>'
        )
    return f'<div class="nav-sublinks">{"".join(chunks)}</div>'


def _group_wiki_pages(pages: list[dict[str, str]], lang: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for item in pages:
        parts = item["page"].split("/")
        if len(parts) == 1:
            group_name = _t(lang, "wiki.root")
            label = parts[0]
        else:
            group_name = parts[0]
            label = "/".join(parts[1:])
        grouped[group_name].append({"page": item["page"], "label": label})
    return dict(sorted(grouped.items(), key=lambda entry: entry[0]))


def _nav_link_class(active: bool) -> str:
    return "nav-link active" if active else "nav-link"


def _nav_sublink_class(active: bool) -> str:
    return "nav-sublink active" if active else "nav-sublink"


def _models_page_script(lang: str) -> str:
    strings = json.dumps(_script_strings(lang, "models"), ensure_ascii=False)
    return f"""
    <script>
    const actorName = document.body.dataset.actorName;
    const strings = {strings};
    const meta = document.getElementById('meta');
    const banner = document.getElementById('banner');
    const modelList = document.getElementById('model-list');
    const roleList = document.getElementById('role-list');
    const agentList = document.getElementById('agent-list');
    let state = null;

    function showBanner(message) {{
      banner.hidden = false;
      banner.textContent = message;
    }}

    function clearBanner() {{
      banner.hidden = true;
      banner.textContent = '';
    }}

    function render() {{
      if (!state) return;
      meta.textContent = `${{strings.lastModified}}: ${{state.last_modified_by || strings.unknown}} @ ${{state.updated_at || strings.notRecorded}}`;
      modelList.innerHTML = state.catalog.map((item) => `
        <div class="model-chip" draggable="true" data-model="${{item.abstract}}">
          <div><strong>${{item.abstract}}</strong></div>
          <div class="binding-meta">${{item.full || '未解析'}}</div>
        </div>
      `).join('');
      roleList.innerHTML = Object.keys(state.roster).map((role) => renderTarget('role', role, state.resolved.roles[role])).join('');
      agentList.innerHTML = Object.entries(state.resolved.agents).map(([agent, resolved]) => renderTarget('agent', agent, resolved)).join('');
      bindDnD();
    }}

    function renderTarget(kind, id, resolved) {{
      const current = resolved.abstract || strings.unbound;
      return `
        <div class="binding-card" data-kind="${{kind}}" data-id="${{id}}">
          <div><strong>${{id}}</strong></div>
          <div>${{current}}</div>
          <div class="binding-meta">${{strings.source}}: ${{resolved.source || ''}}${{resolved.role ? ' / role=' + resolved.role : ''}}</div>
          <div class="binding-meta">${{resolved.full || strings.unresolvedFullModel}}</div>
          <div class="binding-meta">${{strings.bindingEffect}}</div>
          <button class="clear-binding" data-kind="${{kind}}" data-id="${{id}}">${{strings.clearOverride}}</button>
        </div>
      `;
    }}

    function bindDnD() {{
      document.querySelectorAll('.model-chip').forEach((item) => {{
        item.addEventListener('dragstart', (event) => {{
          event.dataTransfer.setData('text/plain', item.dataset.model);
        }});
      }});
      document.querySelectorAll('.binding-card').forEach((card) => {{
        card.addEventListener('dragover', (event) => {{
          event.preventDefault();
          card.classList.add('drag-over');
        }});
        card.addEventListener('dragleave', () => card.classList.remove('drag-over'));
        card.addEventListener('drop', async (event) => {{
          event.preventDefault();
          card.classList.remove('drag-over');
          const model = event.dataTransfer.getData('text/plain');
          if (!model) return;
          const kind = card.dataset.kind;
          const id = card.dataset.id;
          if (kind === 'role') state.assignments.roles[id] = model;
          if (kind === 'agent') state.assignments.agents[id] = model;
          await persist();
        }});
      }});
      document.querySelectorAll('.clear-binding').forEach((button) => {{
        button.addEventListener('click', async () => {{
          const kind = button.dataset.kind;
          const id = button.dataset.id;
          if (kind === 'role') delete state.assignments.roles[id];
          if (kind === 'agent') delete state.assignments.agents[id];
          await persist();
        }});
      }});
    }}

    async function persist() {{
      clearBanner();
      const response = await fetch('/api/bindings', {{
        method: 'PUT',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
          version_token: state.version_token,
          aliases: state.aliases,
          assignments: state.assignments
        }})
      }});
      const data = await response.json();
      if (!response.ok) {{
        showBanner(data.error || strings.saveBindingsFailed);
        return;
      }}
      state = data;
      render();
    }}

    async function load() {{
      const response = await fetch('/api/bindings');
      state = await response.json();
      render();
    }}

    const events = new EventSource('/api/events');
    events.addEventListener('bindings.updated', async (event) => {{
      const data = JSON.parse(event.data);
      if (data.actor_name !== actorName) {{
        showBanner(strings.bindingsUpdated.replace('{{actor}}', data.actor_name));
        await load();
      }}
    }});

    load();
    </script>
    """


def _editor_page_script(
    api_path: str,
    kind: str,
    title: str,
    doc_name: str,
    discussion_enabled: bool,
    actor_name: str,
    lang: str,
) -> str:
    strings = _script_strings(lang, "editor")
    config = json.dumps(
        {
            "apiPath": api_path,
            "kind": kind,
            "title": title,
            "docName": doc_name,
            "discussionEnabled": discussion_enabled,
            "actorName": actor_name,
            "strings": strings,
        },
        ensure_ascii=False,
    )
    return f"""
    <script>
    const config = {config};
    const actorName = config.actorName;
    const strings = config.strings;
    const source = document.getElementById('source');
    const preview = document.getElementById('preview');
    const cards = document.getElementById('cards');
    const meta = document.getElementById('meta');
    const banner = document.getElementById('banner');
    const saveButton = document.getElementById('save');
    const reloadButton = document.getElementById('reload');
    const previewShell = document.getElementById('preview-shell');
    const threadList = document.getElementById('thread-list');
    let versionToken = '';
    let targetPath = '';
    let debounceTimer = null;
    let requestSerial = 0;

    function showBanner(message) {{
      banner.hidden = false;
      banner.textContent = message;
    }}

    function clearBanner() {{
      banner.hidden = true;
      banner.textContent = '';
    }}

    function renderMeta(data) {{
      meta.textContent = `${{strings.lastModified}}: ${{data.last_modified_by || strings.unknown}} @ ${{data.updated_at || strings.notRecorded}}`;
    }}

    function renderCards(items) {{
      if (!cards) return;
      cards.innerHTML = (items || []).map((item) => `
        <article class="requirement-card">
          <div><strong>${{item.id}}</strong> · ${{item.title}}</div>
          <p>${{item.summary || ''}}</p>
          <div class="chip-row">
            <button class="chip-toggle ${{item.valid ? 'on' : ''}}" data-fr="${{item.id}}" data-field="valid">✅ ${{strings.valid}}</button>
            <button class="chip-toggle ${{item.testable ? 'on' : ''}}" data-fr="${{item.id}}" data-field="testable">✅ ${{strings.testable}}</button>
            <button class="chip-toggle ${{item.decided ? 'on' : ''}}" data-fr="${{item.id}}" data-field="decided">✅ ${{strings.decided}}</button>
          </div>
        </article>
      `).join('');
      document.querySelectorAll('.chip-toggle').forEach((btn) => {{
        btn.addEventListener('click', async () => {{
          const frId = btn.dataset.fr;
          const field = btn.dataset.field;
          const response = await fetch(config.apiPath + '/toggle-status', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{ fr_id: frId, field: field, version_token: versionToken }})
          }});
          const data = await response.json();
          if (response.status === 409) {{
            showConflict(data);
            return;
          }}
          if (!response.ok) {{
            showBanner(data.error || strings.statusToggleFailed);
            return;
          }}
          hydrate(data);
          showAutosaveIndicator(strings.statusToggled);
        }});
      }});
    }}

    function renderThreads(threads) {{
      if (!threadList) return;
      threadList.innerHTML = (threads || []).map((thread) => `
        <article class="thread-item">
          <div><strong>${{thread.thread_id}}</strong> · ${{thread.initiator}} · ${{strings.status}}=${{thread.status}}</div>
          <div class="binding-meta">${{strings.anchorLine}} ${{thread.anchor_line}} · ${{strings.rootLine}} ${{thread.root_line}}</div>
          <p>${{thread.snippet || ''}}</p>
          <div class="inline-form">
            <input data-thread="${{thread.thread_id}}" class="reply-body" placeholder="${{strings.replyPlaceholder}}" />
            <button data-action="reply" data-thread="${{thread.thread_id}}">${{strings.reply}}</button>
            <button data-action="set-status" data-thread="${{thread.thread_id}}" data-status="resolved">${{strings.markResolved}}</button>
          </div>
        </article>
      `).join('');
      document.querySelectorAll('[data-action="reply"]').forEach((button) => {{
        button.addEventListener('click', async () => {{
          const thread = (threads || []).find((item) => item.thread_id === button.dataset.thread);
          const body = document.querySelector(`input.reply-body[data-thread="${{thread.thread_id}}"]`).value.trim();
          if (!body) return;
          await mutateDiscussion('reply', thread, {{ body, thread_id: thread.thread_id }});
        }});
      }});
      document.querySelectorAll('[data-action="set-status"]').forEach((button) => {{
        button.addEventListener('click', async () => {{
          const thread = (threads || []).find((item) => item.thread_id === button.dataset.thread);
          await mutateDiscussion('set-status', thread, {{ status: button.dataset.status, thread_id: thread.thread_id }});
        }});
      }});
    }}

    function hydrate(data) {{
      source.value = data.body_md || '';
      preview.innerHTML = data.rendered_html || '';
      versionToken = data.version_token || '';
      targetPath = data.path || targetPath;
      renderMeta(data);
      renderCards(data.cards || []);
      renderThreads(data.discussion_threads || []);
    }}

    async function load() {{
      clearBanner();
      const response = await fetch(config.apiPath, {{
        headers: {{'Accept': 'application/json'}}
      }});
      const data = await response.json();
      if (!response.ok) {{
        showBanner(data.error || strings.loadFailed.replace('{{title}}', config.title));
        return;
      }}
      hydrate(data);
    }}

    async function save(force) {{
      clearBanner();
      const body = JSON.stringify({{
        body_md: source.value,
        version_token: versionToken,
        force: !!force
      }});
      const response = await fetch(config.apiPath, {{
        method: 'PUT',
        headers: {{ 'Content-Type': 'application/json' }},
        body: body
      }});
      const data = await response.json();
      if (response.status === 409 && !force) {{
        showConflict(data);
        return;
      }}
      if (!response.ok) {{
        showBanner(data.error || strings.saveFailed);
        return;
      }}
      hydrate(data);
      showAutosaveIndicator(strings.saved || 'Saved');
    }}

    function showConflict(data) {{
      banner.hidden = false;
      banner.innerHTML = `${{strings.conflictDetected || 'Conflict detected'}}: ${{data.error || ''}}
        <button id="view-remote" class="conflict-btn">${{strings.viewRemote || 'View remote'}}</button>
        <button id="force-overwrite" class="conflict-btn">${{strings.forceOverwrite || 'Force overwrite'}}</button>`;
      document.getElementById('view-remote').addEventListener('click', async () => {{
        const resp = await fetch(config.apiPath, {{ headers: {{'Accept': 'application/json'}} }});
        const remote = await resp.json();
        preview.innerHTML = remote.rendered_html || '';
        showBanner(`${{strings.remoteLoaded || 'Remote loaded (read-only). Merge or discard your edits.'}}`);
      }});
      document.getElementById('force-overwrite').addEventListener('click', async () => {{
        await save(true);
      }});
    }}

    async function refreshPreview() {{
      const serial = ++requestSerial;
      const response = await fetch('/api/render', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/json'}},
        body: JSON.stringify({{
          kind: config.kind,
          doc_name: config.docName,
          body_md: source.value
        }})
      }});
      const data = await response.json();
      if (serial !== requestSerial) return;
      preview.innerHTML = data.rendered_html || '';
      renderCards(data.cards || []);
      renderThreads(data.discussion_threads || []);
      attachXrefHandlers();
    }}

    // FR-0700: cross-reference link handling
    let xrefHistory = [];
    let allSpecs = [];
    async function loadSpecList() {{
      try {{
        const resp = await fetch('/api/specs', {{ headers: {{'Accept': 'application/json'}} }});
        const data = await resp.json();
        allSpecs = data.specs || [];
      }} catch(e) {{ allSpecs = []; }}
    }}
    loadSpecList();

    function attachXrefHandlers() {{
      preview.querySelectorAll('.xref-link').forEach((link) => {{
        if (link._xrefBound) return;
        link._xrefBound = true;
        link.addEventListener('click', async (e) => {{
          e.preventDefault();
          if (link.classList.contains('xref-cross')) {{
            await navigateCrossSpec(link);
          }} else {{
            const anchorId = link.getAttribute('href').slice(1);
            const target = preview.querySelector('#' + CSS.escape(anchorId));
            if (target) {{
              xrefHistory.push(preview.scrollTop);
              showXrefBack();
              target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
            }} else {{
              link.style.color = 'var(--border)';
              link.style.textDecoration = 'line-through';
            }}
          }}
        }});
      }});
    }}

    async function navigateCrossSpec(link) {{
      const prefix = link.dataset.spec;
      const ref = link.dataset.ref;
      const match = allSpecs.find(s => s.includes('-' + prefix + '-'));
      if (!match) {{
        showBanner(strings.xrefNotFound || `Spec "${{prefix}}" not found`);
        return;
      }}
      xrefHistory.push({{ spec: config.apiPath, scroll: preview.scrollTop }});
      showXrefBack();
      const resp = await fetch(`/api/docs/${{match}}/spec`, {{ headers: {{'Accept': 'application/json'}} }});
      const data = await resp.json();
      const prevHtml = preview.innerHTML;
      preview.innerHTML = `<button class="xref-back" id="xref-back">← ${{strings.xrefBack || 'Back'}}</button>` + (data.rendered_html || '');
      document.getElementById('xref-back').addEventListener('click', () => {{
        preview.innerHTML = prevHtml;
        attachXrefHandlers();
        hideXrefBack();
      }});
      const anchorId = ref.toLowerCase();
      const target = preview.querySelector('#' + CSS.escape(anchorId));
      if (target) {{
        target.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
      }}
    }}

    function showXrefBack() {{
      // Native #anchor navigation uses browser history automatically;
      // cross-spec uses explicit back button
    }}
    function hideXrefBack() {{}}

    async function mutateDiscussion(action, thread, payload) {{
      if (!config.discussionEnabled) return;
      const response = await fetch('/api/discussions/mutate', {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify({{
          target_kind: config.kind,
          target_path: targetPath,
          version_token: versionToken,
          action,
          anchor: {{ anchor_line: thread.anchor_line }},
          payload: Object.assign({{}}, payload, thread)
        }})
      }});
      const data = await response.json();
      if (!response.ok) {{
        showBanner(data.error || strings.discussionFailed);
        return;
      }}
      hydrate(data);
    }}

    let autosaveTimer = null;
    function showAutosaveIndicator(msg) {{
      const ind = document.getElementById('autosave-indicator');
      if (!ind) return;
      ind.textContent = msg;
      ind.hidden = false;
      clearTimeout(ind._fadeTimer);
      ind._fadeTimer = setTimeout(() => {{ ind.hidden = true; }}, 3000);
    }}

    source.addEventListener('input', () => {{
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(refreshPreview, 250);
      clearTimeout(autosaveTimer);
      autosaveTimer = setTimeout(async () => {{
        await save(false);
      }}, 5000);
    }});
    saveButton.addEventListener('click', () => {{
      clearTimeout(autosaveTimer);
      save(false);
    }});
    reloadButton.addEventListener('click', load);

    // FR-0200: sync scroll between editor and preview
    let syncScrollSource = null;
    function syncScroll(from, to) {{
      if (syncScrollSource && syncScrollSource !== from) return;
      syncScrollSource = from;
      const ratio = from.scrollTop / Math.max(1, from.scrollHeight - from.clientHeight);
      to.scrollTop = ratio * Math.max(1, to.scrollHeight - to.clientHeight);
      setTimeout(() => {{ syncScrollSource = null; }}, 50);
    }}
    source.addEventListener('scroll', () => syncScroll(source, preview));
    preview.addEventListener('scroll', () => syncScroll(preview, source));

    // FR-0300: focus toggle (3-state: balanced -> content -> discussion -> balanced)
    const focusToggle = document.getElementById('focus-toggle');
    if (focusToggle) {{
      let focusState = 'balanced';
      focusToggle.textContent = strings.focusBalanced || 'Balanced';
      focusToggle.addEventListener('click', () => {{
        if (focusState === 'balanced') {{
          focusState = 'content';
          previewShell.classList.add('focus-content');
          previewShell.classList.remove('focus-discussion');
          focusToggle.textContent = strings.focusContent || 'Content';
          focusToggle.classList.remove('state-discussion');
        }} else if (focusState === 'content') {{
          focusState = 'discussion';
          previewShell.classList.remove('focus-content');
          previewShell.classList.add('focus-discussion');
          focusToggle.textContent = strings.focusDiscussion || 'Discussion';
          focusToggle.classList.add('state-discussion');
        }} else {{
          focusState = 'balanced';
          previewShell.classList.remove('focus-discussion');
          previewShell.classList.remove('focus-content');
          focusToggle.textContent = strings.focusBalanced || 'Balanced';
          focusToggle.classList.remove('state-discussion');
        }}
      }});
      document.getElementById('toggle-collapse').addEventListener('click', () => {{
        previewShell.classList.toggle('collapsed');
      }});
      document.getElementById('start-discussion').addEventListener('click', async () => {{
        const anchorLine = Number(document.getElementById('new-anchor-line').value || 0);
        const body = document.getElementById('new-discussion-body').value.trim();
        if (!anchorLine || !body) return;
        const response = await fetch('/api/discussions/mutate', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: JSON.stringify({{
            target_kind: config.kind,
            target_path: targetPath,
            version_token: versionToken,
            action: 'start',
            anchor: {{ anchor_line: anchorLine }},
            payload: {{ body }}
          }})
        }});
        const data = await response.json();
        if (!response.ok) {{
          showBanner(data.error || strings.startDiscussionFailed);
          return;
        }}
        hydrate(data);
      }});
    }}

    const events = new EventSource('/api/events');
    ['document.updated', 'wiki.updated', 'conflict.detected'].forEach((eventName) => {{
      events.addEventListener(eventName, (event) => {{
        const data = JSON.parse(event.data);
        if (targetPath && data.target === targetPath && data.actor_name !== actorName) {{
          showBanner(strings.remoteUpdated.replace('{{actor}}', data.actor_name));
        }}
      }});
    }});

    load();
    </script>
    """


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _quote_path(path: str) -> str:
    return quote(path, safe="/")


TRANSLATIONS = {
    "zh": {
        "home.eyebrow": "Workbench",
        "home.lede_before": "当前 spec: ",
        "home.lede_after": "。左侧 sidebar 常驻，模型、wiki、设计文档都从当前项目直接打开。",
        "home.models_desc": "拖拽角色或 Agent 绑定，保存后立刻写入当前项目 `.louke/models.json`。",
        "home.docs_desc": "以 spec 目录为准，打开 spec / acceptance / test-plan 编辑与预览。",
        "home.wiki_desc": "浏览与编辑 `.louke/wiki/pages/`，支持按一级目录分组导航。",
        "nav.models": "模型绑定",
        "nav.docs": "设计文档",
        "models.lede": "左侧模型列表可拖到角色或 Agent 卡片上。保存后会立即写入当前项目 `.louke/models.json`，新的命令解析与新启动 Agent 立刻生效；已在运行的会话不会热切换。",
        "models.catalog": "模型列表",
        "models.roles": "角色绑定",
        "models.agents": "Agent 绑定",
        "wiki.index_lede": "支持直接输入 `dir/page` 新建目录页；sidebar 会按一级目录自动归类。",
        "wiki.create_open": "新建并打开",
        "wiki.empty": "当前没有 wiki 页面。",
        "wiki.editor_lede": "左侧源码，右侧实时预览。编辑保存后立即写回当前项目页面。",
        "wiki.root": "根目录",
        "docs.title": "设计文档",
        "docs.lede": "双栏工作台，支持正文/讨论聚焦、讨论回复与卡片视图。",
        "docs.focus_content": "看正文",
        "docs.focus_discussion": "看讨论",
        "docs.toggle_collapse": "折叠讨论",
        "docs.inline_hint": "`inline-discussion` 默认弱化显示",
        "docs.discussion_actions": "讨论操作",
        "docs.new_discussion_placeholder": "新讨论内容",
        "docs.start_discussion": "发起讨论",
        "common.save": "保存",
        "common.reload": "重新加载",
        "common.markdown": "Markdown",
        "common.preview": "预览",
        "meta.not_recorded": "未记录更新时间",
        "sidebar.spec": "spec",
        "sidebar.signed_in": "已登录",
        "sidebar.logout": "退出",
        "sidebar.main": "主导航",
        "login.subtitle": "使用已有账号登录。",
        "login.create_first": "请先创建第一个账号。",
        "login.sign_in": "登录",
        "login.register": "注册",
        "login.username": "用户名",
        "login.password": "密码",
        "login.sign_in_button": "登录",
        "login.register_button": "注册并登录",
        "login.request_failed": "请求失败",
    },
    "en": {
        "home.eyebrow": "Workbench",
        "home.lede_before": "Current spec: ",
        "home.lede_after": ". The sidebar stays visible, and models, wiki, and design docs open from the current project.",
        "home.models_desc": "Drag roles or agents to bind models and save directly into `.louke/models.json`.",
        "home.docs_desc": "Open spec / acceptance / test-plan editors and previews from the current spec directory.",
        "home.wiki_desc": "Browse and edit `.louke/wiki/pages/` with first-level directory grouping in the sidebar.",
        "nav.models": "Model Bindings",
        "nav.docs": "Design Docs",
        "models.lede": "Drag models onto roles or agents. Saving writes to `.louke/models.json` immediately; new commands and newly started agents pick up the change right away.",
        "models.catalog": "Model Catalog",
        "models.roles": "Role Bindings",
        "models.agents": "Agent Bindings",
        "wiki.index_lede": "Create nested pages with `dir/page`; the sidebar groups them by first-level directory.",
        "wiki.create_open": "Create & Open",
        "wiki.empty": "No wiki pages yet.",
        "wiki.editor_lede": "Source on the left, live preview on the right. Saving writes back to the current project page immediately.",
        "wiki.root": "root",
        "docs.title": "Design Document",
        "docs.lede": "Two-pane workspace with content/discussion focus, replies, and card view.",
        "docs.focus_content": "Focus Content",
        "docs.focus_discussion": "Focus Discussion",
        "docs.toggle_collapse": "Collapse Discussion",
        "docs.inline_hint": "`inline-discussion` is de-emphasized by default",
        "docs.discussion_actions": "Discussion Actions",
        "docs.new_discussion_placeholder": "New discussion content",
        "docs.start_discussion": "Start Discussion",
        "common.save": "Save",
        "common.reload": "Reload",
        "common.markdown": "Markdown",
        "common.preview": "Preview",
        "meta.not_recorded": "No timestamp recorded",
        "sidebar.spec": "spec",
        "sidebar.signed_in": "Signed In",
        "sidebar.logout": "Log Out",
        "sidebar.main": "Main",
        "login.subtitle": "Sign in with an existing account.",
        "login.create_first": "Create the first account to continue.",
        "login.sign_in": "Sign In",
        "login.register": "Register",
        "login.username": "Username",
        "login.password": "Password",
        "login.sign_in_button": "Sign In",
        "login.register_button": "Register & Sign In",
        "login.request_failed": "Request failed",
    },
}


def _t(lang: str, key: str) -> str:
    bundle = TRANSLATIONS.get(lang) or TRANSLATIONS["en"]
    if key in bundle:
        return bundle[key]
    return TRANSLATIONS["en"].get(key, key)


def _script_strings(lang: str, scope: str) -> dict[str, str]:
    if lang == "zh" and scope == "models":
        return {
            "lastModified": "最后修改",
            "unknown": "未知",
            "notRecorded": "未记录",
            "unbound": "未绑定",
            "source": "来源",
            "unresolvedFullModel": "未解析 full model",
            "bindingEffect": "保存后对当前项目立即生效；新启动的 Agent / 命令会读取这个绑定。",
            "clearOverride": "清除覆盖",
            "saveBindingsFailed": "保存绑定失败",
            "bindingsUpdated": "模型绑定已由 {{actor}} 更新，正在刷新视图",
        }
    if scope == "models":
        return {
            "lastModified": "Last modified",
            "unknown": "Unknown",
            "notRecorded": "Not recorded",
            "unbound": "Unbound",
            "source": "Source",
            "unresolvedFullModel": "Full model not resolved",
            "bindingEffect": "Changes apply to this project immediately; newly started agents and commands use this binding.",
            "clearOverride": "Clear Override",
            "saveBindingsFailed": "Failed to save bindings",
            "bindingsUpdated": "Bindings were updated by {{actor}}. Refreshing view.",
        }
    if lang == "zh":
        return {
            "lastModified": "最后修改",
            "unknown": "未知",
            "notRecorded": "未记录",
            "valid": "Valid",
            "testable": "Testable",
            "decided": "Decided",
            "status": "status",
            "anchorLine": "anchor line",
            "rootLine": "root line",
            "replyPlaceholder": "回复内容",
            "reply": "回复",
            "markResolved": "标记 resolved",
            "loadFailed": "加载 {{title}} 失败",
            "saveFailed": "保存失败",
            "discussionFailed": "讨论操作失败",
            "startDiscussionFailed": "发起讨论失败",
            "remoteUpdated": "远端内容已由 {{actor}} 更新，请重新加载或手工合并本地修改",
            "focusContent": "看正文",
            "focusDiscussion": "看讨论",
            "focusBalanced": "均衡",
            "saved": "已自动保存",
            "conflictDetected": "检测到写入冲突",
            "viewRemote": "查看远端版本",
            "forceOverwrite": "强制覆盖",
            "remoteLoaded": "已加载远端版本（只读），请合并或放弃本地编辑",
            "statusToggled": "状态已更新",
            "statusToggleFailed": "状态更新失败",
            "xrefBack": "返回",
            "xrefNotFound": "未找到对应的 spec",
        }
    return {
        "lastModified": "Last modified",
        "unknown": "Unknown",
        "notRecorded": "Not recorded",
        "valid": "Valid",
        "testable": "Testable",
        "decided": "Decided",
        "status": "status",
        "anchorLine": "anchor line",
        "rootLine": "root line",
        "replyPlaceholder": "Reply content",
        "reply": "Reply",
        "markResolved": "Mark resolved",
        "loadFailed": "Failed to load {{title}}",
        "saveFailed": "Save failed",
        "discussionFailed": "Discussion action failed",
        "startDiscussionFailed": "Failed to start discussion",
        "remoteUpdated": "Remote content was updated by {{actor}}. Reload or merge your local edits manually.",
        "focusContent": "Content",
        "focusDiscussion": "Discussion",
        "focusBalanced": "Balanced",
        "saved": "Auto-saved",
        "conflictDetected": "Write conflict detected",
        "viewRemote": "View remote",
        "forceOverwrite": "Force overwrite",
        "remoteLoaded": "Remote loaded (read-only). Merge or discard your edits.",
        "statusToggled": "Status updated",
        "statusToggleFailed": "Status update failed",
        "xrefBack": "Back",
        "xrefNotFound": "Spec not found",
    }


def _login_shell(lang: str, next_path: str, has_users: bool) -> str:
    next_json = json.dumps(next_path, ensure_ascii=False)
    empty_state = _t(lang, "login.subtitle") if has_users else _t(lang, "login.create_first")
    hero_image = "/assets/min-square_97-snk-X32c8tE-unsplash.jpg"
    return f"""<!DOCTYPE html>
<html lang="{_escape('zh-CN' if lang == 'zh' else 'en')}">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>louke login</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --surface: #ffffff;
      --surface-alt: #f1f3f5;
      --text: #0f172a;
      --muted: #64748b;
      --border: #e2e8f0;
      --border-strong: #cbd5e1;
      --danger: #dc2626;
      --danger-bg: #fef2f2;
      --danger-border: #fecaca;
      --accent: #0f172a;
      --accent-hover: #1e293b;
      --ring: rgba(15, 23, 42, 0.12);
      --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
      --shadow-md: 0 4px 16px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.04);
      --shadow-lg: 0 24px 48px rgba(15, 23, 42, 0.08), 0 2px 8px rgba(15, 23, 42, 0.04);
      --radius: 14px;
      --radius-lg: 24px;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif;
      -webkit-font-smoothing: antialiased;
    }}
    .auth-shell {{
      width: min(960px, calc(100vw - 32px));
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      overflow: hidden;
      background: var(--surface);
      box-shadow: var(--shadow-lg);
    }}
    .auth-hero {{ padding: 40px; }}
    .auth-panel {{
      padding: 44px 40px;
      display: grid;
      gap: 24px;
      align-content: start;
    }}
    .auth-hero {{
      position: relative;
      min-height: 620px;
      display: grid;
      place-items: center;
      border-right: 1px solid var(--border);
      color: #ffffff;
      background:
        linear-gradient(180deg, rgba(15, 23, 42, 0.18) 0%, rgba(15, 23, 42, 0.42) 100%),
        url('{hero_image}') center center / cover no-repeat;
    }}
    .eyebrow {{
      color: var(--muted);
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.12em;
    }}
    .hero-eyebrow {{ color: rgba(255, 255, 255, 0.82); }}
    h1, h2 {{ margin: 0; letter-spacing: -0.02em; font-weight: 700; }}
    h2 {{ font-size: 22px; }}
    p {{ margin: 0; line-height: 1.6; color: var(--muted); }}
    .hero-copy {{
      max-width: 560px;
      display: grid;
      gap: 14px;
      padding: 32px;
      text-align: center;
    }}
    .hero-copy h1 {{
      margin: 0;
      color: #ffffff;
      font-size: clamp(22px, 2.7vw, 34px);
      line-height: 1.15;
    }}
    .photo-credit {{
      position: absolute;
      right: 24px;
      bottom: 24px;
      max-width: 440px;
      font-size: 12px;
      line-height: 1.6;
      color: rgba(255, 255, 255, 0.64);
    }}
    .photo-credit a {{
      color: rgba(255, 255, 255, 0.72);
      text-decoration: underline;
      text-underline-offset: 2px;
    }}
    .tabs {{
      display: inline-grid;
      grid-template-columns: 1fr 1fr;
      gap: 4px;
      padding: 4px;
      border: 1px solid var(--border);
      border-radius: var(--radius);
      background: var(--surface-alt);
    }}
    .tab-button {{
      padding: 11px 16px;
      border-radius: 10px;
      border: 0;
      background: transparent;
      color: var(--muted);
      cursor: pointer;
      font: inherit;
      font-weight: 500;
      transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
    }}
    .tab-button:hover {{ color: var(--text); }}
    .tab-button.active {{
      background: var(--surface);
      color: var(--text);
      box-shadow: var(--shadow-sm);
    }}
    .tab-panel[hidden] {{ display: none; }}
    .tab-panel .eyebrow {{ margin-bottom: -6px; }}
    label {{
      display: grid;
      gap: 8px;
      font-size: 13px;
      font-weight: 500;
      color: var(--text);
    }}
    input {{
      width: 100%;
      padding: 13px 14px;
      border-radius: 11px;
      border: 1px solid var(--border-strong);
      background: var(--surface);
      color: var(--text);
      font: inherit;
      font-size: 15px;
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }}
    input::placeholder {{ color: #94a3b8; }}
    input:focus {{
      outline: none;
      border-color: var(--accent);
      box-shadow: 0 0 0 3px var(--ring);
    }}
    button {{
      padding: 0 18px;
      height: 46px;
      border-radius: 11px;
      border: 1px solid var(--accent);
      background: var(--accent);
      color: white;
      cursor: pointer;
      font: inherit;
      font-size: 15px;
      font-weight: 600;
      transition: transform 0.05s ease, background 0.15s ease, box-shadow 0.15s ease;
    }}
    button:hover {{ background: var(--accent-hover); }}
    button:active {{ transform: translateY(1px); }}
    button:focus-visible {{ outline: none; box-shadow: 0 0 0 3px var(--ring); }}
    .secondary {{ background: var(--surface); color: var(--text); border-color: var(--border-strong); }}
    .secondary:hover {{ background: var(--surface-alt); }}
    .stack {{ display: grid; gap: 16px; }}
    .row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }}
    .banner {{
      padding: 11px 14px;
      border: 1px solid var(--danger-border);
      border-radius: 11px;
      background: var(--danger-bg);
      color: var(--danger);
      font-size: 14px;
    }}
    @media (max-width: 860px) {{
      .auth-shell {{ grid-template-columns: 1fr; }}
      .auth-hero {{ border-right: 0; border-bottom: 1px solid var(--border); }}
      .row {{ grid-template-columns: 1fr; }}
      .photo-credit {{
        right: 20px;
        bottom: 20px;
        max-width: none;
      }}
      .auth-panel {{ padding: 32px 24px; }}
    }}
  </style>
</head>
<body>
  <main class="auth-shell">
    <section class="auth-hero">
      <div class="hero-copy">
        <h1>Beyond Vibes, Into Craft</h1>
        <h2>超越氛围编程 自是精工镂刻</h2>
      </div>
      <div class="photo-credit">
        Photo by <a href="https://unsplash.com/@min_square97?utm_source=unsplash&utm_medium=referral&utm_content=creditCopyText" target="_blank" rel="noreferrer">Min Square_97</a> on <a href="https://unsplash.com/photos/a-close-up-of-a-clock-with-gold-gears-snk-X32c8tE?utm_source=unsplash&utm_medium=referral&utm_content=creditCopyText" target="_blank" rel="noreferrer">Unsplash</a>
      </div>
    </section>
    <section class="auth-panel">
      <div class="tabs" role="tablist" aria-label="认证入口">
        <button id="tab-login" class="tab-button active" type="button" role="tab" aria-selected="true">{_escape(_t(lang, "login.sign_in"))}</button>
        <button id="tab-register" class="tab-button" type="button" role="tab" aria-selected="false">{_escape(_t(lang, "login.register"))}</button>
      </div>
      <div id="panel-login" class="stack tab-panel" role="tabpanel">
        <div class="eyebrow">{_escape(_t(lang, "login.sign_in"))}</div>
        <h2>{_escape(_t(lang, "login.sign_in"))}</h2>
        <label>{_escape(_t(lang, "login.username"))}<input id="login-username" autocomplete="username" /></label>
        <label>{_escape(_t(lang, "login.password"))}<input id="login-password" type="password" autocomplete="current-password" /></label>
        <button id="login-submit">{_escape(_t(lang, "login.sign_in_button"))}</button>
      </div>
      <div id="panel-register" class="stack tab-panel" role="tabpanel" hidden>
        <div class="eyebrow">{_escape(_t(lang, "login.register"))}</div>
        <h2>{_escape(_t(lang, "login.register"))}</h2>
        <div class="row">
          <label>{_escape(_t(lang, "login.username"))}<input id="register-username" autocomplete="username" /></label>
          <label>{_escape(_t(lang, "login.password"))}<input id="register-password" type="password" autocomplete="new-password" /></label>
        </div>
        <button id="register-submit" class="secondary">{_escape(_t(lang, "login.register_button"))}</button>
      </div>
      <div id="banner" class="banner" hidden></div>
    </section>
  </main>
  <script>
    const nextPath = {next_json};
    const requestFailed = {json.dumps(_t(lang, "login.request_failed"), ensure_ascii=False)};
    const banner = document.getElementById('banner');
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const panelLogin = document.getElementById('panel-login');
    const panelRegister = document.getElementById('panel-register');
    function showBanner(message) {{
      banner.hidden = false;
      banner.textContent = message;
    }}
    function switchTab(target) {{
      const loginActive = target === 'login';
      tabLogin.classList.toggle('active', loginActive);
      tabRegister.classList.toggle('active', !loginActive);
      tabLogin.setAttribute('aria-selected', loginActive ? 'true' : 'false');
      tabRegister.setAttribute('aria-selected', loginActive ? 'false' : 'true');
      panelLogin.hidden = !loginActive;
      panelRegister.hidden = loginActive;
      banner.hidden = true;
    }}
    async function submit(path, payload) {{
      banner.hidden = true;
      const response = await fetch(path, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(payload)
      }});
      const data = await response.json();
      if (!response.ok) {{
        showBanner(data.error || requestFailed);
        return;
      }}
      location.href = nextPath || '/';
    }}
    tabLogin.addEventListener('click', () => switchTab('login'));
    tabRegister.addEventListener('click', () => switchTab('register'));
    document.getElementById('login-submit').addEventListener('click', async () => {{
      await submit('/api/auth/login', {{
        username: document.getElementById('login-username').value.trim(),
        password: document.getElementById('login-password').value
      }});
    }});
    document.getElementById('register-submit').addEventListener('click', async () => {{
      await submit('/api/auth/register', {{
        username: document.getElementById('register-username').value.trim(),
        password: document.getElementById('register-password').value
      }});
    }});
  </script>
</body>
</html>"""


def _assets_dir() -> Path:
    return Path(__file__).resolve().parent / "assets"
