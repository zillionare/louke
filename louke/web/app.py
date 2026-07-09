from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, StreamingResponse
from starlette.routing import Route

from .bindings import get_bindings_payload, save_bindings_payload
from .documents import (
    get_doc_payload,
    get_wiki_payload,
    mutate_discussion,
    render_preview_payload,
    save_doc_payload,
    save_wiki_payload,
)
from .events import EventBroker
from .store import ConflictError, ProjectStore, ValidationError


def create_app(project_root: str | Path) -> Starlette:
    store = ProjectStore(Path(project_root))
    broker = EventBroker()
    app = Starlette(
        debug=False,
        routes=[
            Route("/", endpoint=home_page),
            Route("/models", endpoint=models_page),
            Route("/wiki", endpoint=wiki_index_page),
            Route("/wiki/{page:str}", endpoint=wiki_editor_page),
            Route("/docs/{spec_id:str}/{doc_name:str}", endpoint=doc_editor_page),
            Route("/health", endpoint=health),
            Route("/api/bindings", endpoint=api_bindings, methods=["GET", "PUT"]),
            Route("/api/wiki", endpoint=api_wiki_index, methods=["GET"]),
            Route("/api/wiki/{page:str}", endpoint=api_wiki_page, methods=["GET", "PUT"]),
            Route("/api/docs/{spec_id:str}/{doc_name:str}", endpoint=api_doc, methods=["GET", "PUT"]),
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


async def home_page(request: Request) -> HTMLResponse:
    store: ProjectStore = request.app.state.store
    spec_id = store.spec_id
    body = f"""
    <section class="hero">
      <h1>louke Web Workbench</h1>
      <p>当前 spec: <code>{_escape(spec_id)}</code></p>
    </section>
    <section class="grid cards">
      <a class="card" href="/models">
        <h2>模型绑定</h2>
        <p>拖拽式编辑 Agent / 角色绑定。</p>
      </a>
      <a class="card" href="/wiki">
        <h2>wiki</h2>
        <p>浏览与编辑 `.louke/wiki/pages/*.md`。</p>
      </a>
      <a class="card" href="/docs/{_escape(spec_id)}/spec">
        <h2>设计文档</h2>
        <p>打开 spec / acceptance / test-plan 双栏工作台。</p>
      </a>
    </section>
    """
    return HTMLResponse(_page_shell("louke web", body))


async def models_page(request: Request) -> HTMLResponse:
    store: ProjectStore = request.app.state.store
    body = f"""
    <header class="toolbar">
      <div>
        <h1>模型绑定</h1>
        <p class="muted">左侧模型列表可拖到角色或 Agent 卡片上。卡片会显示生效来源与解析结果。</p>
      </div>
      <div id="meta" class="meta"></div>
    </header>
    <div id="banner" class="banner" hidden></div>
    <main class="grid models-grid">
      <section class="panel">
        <h2>模型列表</h2>
        <div id="model-list" class="model-list"></div>
      </section>
      <section class="panel">
        <h2>角色绑定</h2>
        <div id="role-list" class="binding-list"></div>
      </section>
      <section class="panel">
        <h2>Agent 绑定</h2>
        <div id="agent-list" class="binding-list"></div>
      </section>
    </main>
    """
    script = _models_page_script(store.spec_id)
    return HTMLResponse(_page_shell("模型绑定", body, script=script))


async def wiki_index_page(request: Request) -> HTMLResponse:
    store: ProjectStore = request.app.state.store
    pages = store.list_wiki_pages()
    items = []
    for page in pages:
        items.append(
            f'<a class="card wiki-card" href="/wiki/{_escape(page["page"])}">'
            f'<h2>{_escape(page["page"])}</h2>'
            f'<p>{_escape(page["updated_at"] or "未记录更新时间")}</p>'
            f"</a>"
        )
    body = f"""
    <header class="toolbar">
      <div>
        <h1>wiki</h1>
        <p class="muted">现有页面与快速新建入口。</p>
      </div>
      <div class="toolbar-actions">
        <input id="new-page" placeholder="new-page-slug" />
        <button id="create-page">新建并打开</button>
      </div>
    </header>
    <section class="grid cards">
      {''.join(items) or '<div class="card"><p>当前没有 wiki 页面。</p></div>'}
    </section>
    """
    script = """
    <script>
    document.getElementById('create-page').addEventListener('click', () => {
      const value = document.getElementById('new-page').value.trim();
      if (!value) return;
      location.href = `/wiki/${encodeURIComponent(value)}`;
    });
    </script>
    """
    return HTMLResponse(_page_shell("wiki", body, script=script))


async def wiki_editor_page(request: Request) -> HTMLResponse:
    page = request.path_params["page"]
    body = f"""
    <header class="toolbar">
      <div>
        <h1>wiki: <code>{_escape(page)}</code></h1>
        <p class="muted">左侧源码，右侧实时预览。</p>
      </div>
      <div class="toolbar-actions">
        <button id="save">保存</button>
        <button id="reload">重新加载</button>
      </div>
    </header>
    <div id="banner" class="banner" hidden></div>
    <div id="meta" class="meta"></div>
    <main class="grid editor-grid">
      <section class="panel">
        <h2>Markdown</h2>
        <textarea id="source" spellcheck="false"></textarea>
      </section>
      <section class="panel">
        <div class="panel-header">
          <h2>预览</h2>
        </div>
        <div id="preview" class="preview"></div>
      </section>
    </main>
    """
    script = _editor_page_script(
        api_path=f"/api/wiki/{page}",
        kind="wiki",
        title=f"wiki:{page}",
        doc_name="",
        discussion_enabled=False,
    )
    return HTMLResponse(_page_shell(f"wiki {page}", body, script=script))


async def doc_editor_page(request: Request) -> HTMLResponse:
    spec_id = request.path_params["spec_id"]
    doc_name = request.path_params["doc_name"]
    body = f"""
    <header class="toolbar">
      <div>
        <h1>设计文档: <code>{_escape(doc_name)}</code></h1>
        <p class="muted">双栏工作台，支持正文/讨论聚焦、讨论回复与卡片视图。</p>
      </div>
      <div class="toolbar-actions">
        <button id="focus-content">看正文</button>
        <button id="focus-discussion">看讨论</button>
        <button id="toggle-collapse">折叠讨论</button>
        <button id="save">保存</button>
        <button id="reload">重新加载</button>
      </div>
    </header>
    <div id="banner" class="banner" hidden></div>
    <div id="meta" class="meta"></div>
    <main class="grid editor-grid">
      <section class="panel">
        <h2>Markdown</h2>
        <textarea id="source" spellcheck="false"></textarea>
      </section>
      <section class="panel">
        <div class="panel-header">
          <h2>预览</h2>
          <span class="muted">`inline-discussion` 默认弱化显示</span>
        </div>
        <div id="preview-shell" class="preview-shell focus-content">
          <div id="preview" class="preview"></div>
        </div>
        <div id="cards" class="cards-list"></div>
        <section id="discussion-tools" class="discussion-tools">
          <h2>讨论操作</h2>
          <div class="inline-form">
            <input id="new-anchor-line" type="number" min="1" placeholder="anchor line" />
            <input id="new-discussion-body" placeholder="新讨论内容" />
            <button id="start-discussion">发起讨论</button>
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
    )
    return HTMLResponse(_page_shell(f"{spec_id} {doc_name}", body, script=script))


async def api_bindings(request: Request) -> JSONResponse:
    store: ProjectStore = request.app.state.store
    broker: EventBroker = request.app.state.broker
    if request.method == "GET":
        return JSONResponse(get_bindings_payload(store))
    payload = await request.json()
    actor_name = _actor_name(request, payload)
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
    return JSONResponse({"pages": request.app.state.store.list_wiki_pages()})


async def api_wiki_page(request: Request) -> JSONResponse:
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
    actor_name = _actor_name(request, payload)
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
    actor_name = _actor_name(request, payload)
    try:
        response = save_doc_payload(
            store,
            spec_id=spec_id,
            doc_name=doc_name,
            body_md=str(payload.get("body_md") or ""),
            version_token=str(payload.get("version_token") or ""),
            actor_name=actor_name,
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


async def api_render(request: Request) -> JSONResponse:
    payload = await request.json()
    return JSONResponse(
        render_preview_payload(
            kind=str(payload.get("kind") or ""),
            doc_name=str(payload.get("doc_name") or ""),
            body_md=str(payload.get("body_md") or ""),
        )
    )


async def api_discussion_mutate(request: Request) -> JSONResponse:
    store: ProjectStore = request.app.state.store
    broker: EventBroker = request.app.state.broker
    payload = await request.json()
    actor_name = _actor_name(request, payload)
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


def _actor_name(request: Request, payload: dict[str, Any]) -> str:
    actor_name = str(request.headers.get("X-Louke-Actor") or payload.get("actor_name") or "").strip()
    if not actor_name:
        raise ValidationError("actor_name is required")
    return actor_name


def _page_shell(title: str, body: str, script: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_escape(title)}</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #111827;
      --panel: #1f2937;
      --panel-alt: #0f172a;
      --text: #e5e7eb;
      --muted: #94a3b8;
      --accent: #60a5fa;
      --border: #334155;
      --danger: #f97316;
      --success: #34d399;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      background: var(--bg);
      color: var(--text);
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    code {{ color: #bfdbfe; }}
    .shell {{ max-width: 1600px; margin: 0 auto; padding: 20px; }}
    .toolbar, .panel-header {{
      display: flex; justify-content: space-between; gap: 16px; align-items: center;
    }}
    .toolbar-actions, .inline-form {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .grid {{ display: grid; gap: 16px; }}
    .editor-grid {{ grid-template-columns: minmax(420px, 1fr) minmax(420px, 1fr); }}
    .models-grid {{ grid-template-columns: 280px 1fr 1fr; }}
    .cards {{ grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); margin-top: 16px; }}
    .panel, .card, .banner {{
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
    }}
    .hero {{ margin-bottom: 16px; }}
    .muted {{ color: var(--muted); }}
    textarea, input {{
      width: 100%;
      background: var(--panel-alt);
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      font: inherit;
    }}
    textarea {{ min-height: 70vh; resize: vertical; }}
    button {{
      background: #1d4ed8;
      color: white;
      border: 0;
      padding: 10px 14px;
      border-radius: 8px;
      cursor: pointer;
      font: inherit;
    }}
    .preview {{ min-height: 70vh; overflow: auto; }}
    .preview-shell.focus-content .discussion-block {{ opacity: 0.35; }}
    .preview-shell.focus-discussion .markdown-block {{ opacity: 0.35; }}
    .preview-shell.collapsed .discussion-block {{ display: none; }}
    .discussion-block, .discussion-tools, .cards-list {{ margin-top: 16px; }}
    .discussion-thread {{
      border-left: 3px solid var(--accent);
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
    .discussion-reply {{ margin: 10px 0 0 12px; padding-left: 12px; border-left: 1px dashed var(--border); }}
    .cards-list {{ display: grid; gap: 12px; }}
    .requirement-card {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      background: rgba(15, 23, 42, 0.55);
    }}
    .chip-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
    .chip {{ border: 1px solid var(--border); border-radius: 999px; padding: 2px 8px; color: var(--muted); }}
    .model-chip {{
      border: 1px solid var(--accent);
      background: rgba(96, 165, 250, 0.12);
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
      background: rgba(15, 23, 42, 0.55);
    }}
    .binding-card.drag-over {{ border-color: var(--accent); background: rgba(96, 165, 250, 0.1); }}
    .binding-meta {{ color: var(--muted); font-size: 13px; }}
    .meta {{ margin: 12px 0; color: var(--muted); }}
    .thread-item {{
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 10px;
      margin-top: 10px;
    }}
    .banner {{ margin: 12px 0; border-color: var(--danger); color: #fed7aa; }}
    pre {{ overflow: auto; background: var(--panel-alt); padding: 12px; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ border: 1px solid var(--border); padding: 8px; text-align: left; }}
    @media (max-width: 1100px) {{
      .editor-grid, .models-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    {body}
  </div>
  {script}
</body>
</html>"""


def _models_page_script(spec_id: str) -> str:
    config = json.dumps({"specId": spec_id}, ensure_ascii=False)
    return f"""
    <script>
    const config = {config};
    const actorName = localStorage.getItem('louke.actorName') || prompt('显示名', 'Aaron') || 'anonymous';
    localStorage.setItem('louke.actorName', actorName);
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
      meta.textContent = `最后修改: ${{state.last_modified_by || '未知'}} @ ${{state.updated_at || '未记录'}}`;
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
      const current = resolved.abstract || '未绑定';
      return `
        <div class="binding-card" data-kind="${{kind}}" data-id="${{id}}">
          <div><strong>${{id}}</strong></div>
          <div>${{current}}</div>
          <div class="binding-meta">来源: ${{resolved.source || ''}}${{resolved.role ? ' / role=' + resolved.role : ''}}</div>
          <div class="binding-meta">${{resolved.full || '未解析 full model'}}</div>
          <button class="clear-binding" data-kind="${{kind}}" data-id="${{id}}">清除覆盖</button>
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
        headers: {{'Content-Type': 'application/json', 'X-Louke-Actor': actorName}},
        body: JSON.stringify({{
          version_token: state.version_token,
          aliases: state.aliases,
          assignments: state.assignments,
          actor_name: actorName
        }})
      }});
      const data = await response.json();
      if (!response.ok) {{
        showBanner(data.error || '保存绑定失败');
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
        showBanner(`模型绑定已由 ${{data.actor_name}} 更新，正在刷新视图`);
        await load();
      }}
    }});

    load();
    </script>
    """


def _editor_page_script(api_path: str, kind: str, title: str, doc_name: str, discussion_enabled: bool) -> str:
    config = json.dumps(
        {
            "apiPath": api_path,
            "kind": kind,
            "title": title,
            "docName": doc_name,
            "discussionEnabled": discussion_enabled,
        },
        ensure_ascii=False,
    )
    return f"""
    <script>
    const config = {config};
    const actorName = localStorage.getItem('louke.actorName') || prompt('显示名', 'Aaron') || 'anonymous';
    localStorage.setItem('louke.actorName', actorName);
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
      meta.textContent = `最后修改: ${{data.last_modified_by || '未知'}} @ ${{data.updated_at || '未记录'}}`;
    }}

    function renderCards(items) {{
      if (!cards) return;
      cards.innerHTML = (items || []).map((item) => `
        <article class="requirement-card">
          <div><strong>${{item.id}}</strong> · ${{item.title}}</div>
          <p>${{item.summary || ''}}</p>
          <div class="chip-row">
            <span class="chip">Valid: ${{item.valid ? '✅' : '❌'}}</span>
            <span class="chip">Testable: ${{item.testable ? '✅' : '❌'}}</span>
            <span class="chip">Decided: ${{item.decided ? '✅' : '❌'}}</span>
          </div>
        </article>
      `).join('');
    }}

    function renderThreads(threads) {{
      if (!threadList) return;
      threadList.innerHTML = (threads || []).map((thread) => `
        <article class="thread-item">
          <div><strong>${{thread.thread_id}}</strong> · ${{thread.initiator}} · status=${{thread.status}}</div>
          <div class="binding-meta">anchor line ${{thread.anchor_line}} · root line ${{thread.root_line}}</div>
          <p>${{thread.snippet || ''}}</p>
          <div class="inline-form">
            <input data-thread="${{thread.thread_id}}" class="reply-body" placeholder="回复内容" />
            <button data-action="reply" data-thread="${{thread.thread_id}}">回复</button>
            <button data-action="set-status" data-thread="${{thread.thread_id}}" data-status="resolved">标记 resolved</button>
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
        showBanner(data.error || `加载 ${{config.title}} 失败`);
        return;
      }}
      hydrate(data);
    }}

    async function save() {{
      clearBanner();
      const response = await fetch(config.apiPath, {{
        method: 'PUT',
        headers: {{
          'Content-Type': 'application/json',
          'X-Louke-Actor': actorName
        }},
        body: JSON.stringify({{
          body_md: source.value,
          version_token: versionToken,
          actor_name: actorName
        }})
      }});
      const data = await response.json();
      if (!response.ok) {{
        showBanner(data.error || '保存失败');
        return;
      }}
      hydrate(data);
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
    }}

    async function mutateDiscussion(action, thread, payload) {{
      if (!config.discussionEnabled) return;
      const response = await fetch('/api/discussions/mutate', {{
        method: 'POST',
        headers: {{
          'Content-Type': 'application/json',
          'X-Louke-Actor': actorName
        }},
        body: JSON.stringify({{
          target_kind: config.kind,
          target_path: targetPath,
          version_token: versionToken,
          actor_name: actorName,
          action,
          anchor: {{ anchor_line: thread.anchor_line }},
          payload: Object.assign({{}}, payload, thread)
        }})
      }});
      const data = await response.json();
      if (!response.ok) {{
        showBanner(data.error || '讨论操作失败');
        return;
      }}
      hydrate(data);
    }}

    source.addEventListener('input', () => {{
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(refreshPreview, 250);
    }});
    saveButton.addEventListener('click', save);
    reloadButton.addEventListener('click', load);

    if (document.getElementById('focus-content')) {{
      document.getElementById('focus-content').addEventListener('click', () => {{
        previewShell.classList.add('focus-content');
        previewShell.classList.remove('focus-discussion');
      }});
      document.getElementById('focus-discussion').addEventListener('click', () => {{
        previewShell.classList.add('focus-discussion');
        previewShell.classList.remove('focus-content');
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
          headers: {{
            'Content-Type': 'application/json',
            'X-Louke-Actor': actorName
          }},
          body: JSON.stringify({{
            target_kind: config.kind,
            target_path: targetPath,
            version_token: versionToken,
            actor_name: actorName,
            action: 'start',
            anchor: {{ anchor_line: anchorLine }},
            payload: {{ body }}
          }})
        }});
        const data = await response.json();
        if (!response.ok) {{
          showBanner(data.error || '发起讨论失败');
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
          showBanner(`远端内容已由 ${{data.actor_name}} 更新，请重新加载或手工合并本地修改`);
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
