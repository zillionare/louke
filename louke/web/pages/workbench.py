"""Workbench shell and the read-only Batch B navigation panels."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
import re

from starlette.requests import Request
from starlette.responses import HTMLResponse

from ..render import render_markdown_view


TOOLBAR_ITEMS = (
    ("chat", "Chat", "💬"),
    ("dev-docs", "Dev Docs", "▤"),
    ("end-user-docs", "End User Docs", "▥"),
    ("wiki", "Wiki", "◈"),
    ("runs", "Runs", "▶"),
    ("accounts", "Accounts", "●"),
    ("gears", "Settings", "⚙"),
)


async def workbench(request: Request) -> HTMLResponse:
    """Render the workbench with filesystem-backed read-only navigation."""
    store = request.app.state.store
    specs = _spec_tree(store.specs_dir, store.root)
    wiki_pages = [item["page"] for item in store.list_wiki_pages()]
    agents = _agents()
    return HTMLResponse(
        _page(
            _toolbar(),
            _devdocs(specs),
            _devdocs_view(
                specs,
                store.specs_dir,
                request.query_params.get("spec"),
                request.query_params.get("doc"),
            ),
            _end_user_docs(store.root),
            _wiki(wiki_pages),
            _runs_sidebar(store.root),
            _chat_sidebar(agents),
            _chat_content(agents),
            _runs_content(store.root),
        )
    )


def _toolbar() -> str:
    return "".join(
        f'<button type="button" data-testid="toolbar-{key}" '
        f'data-activity="{key}" aria-label="{label}" title="{label}">'
        f'<span aria-hidden="true">{icon}</span></button>'
        for key, label, icon in TOOLBAR_ITEMS
    )


def _spec_tree(specs_dir: Path, root: Path) -> list[tuple[str, list[str]]]:
    if not specs_dir.exists():
        return []
    result: list[tuple[str, list[str]]] = []
    for directory in sorted(path for path in specs_dir.iterdir() if path.is_dir()):
        files = sorted(
            path.relative_to(root).as_posix()
            for path in directory.glob("*.md")
            if path.is_file()
        )
        result.append((directory.name, files))
    return result


def _agents() -> list[str]:
    """Discover registered agents with Maestro first and stable filename order."""
    agents_dir = Path(__file__).parents[2] / "agents"
    names = sorted(
        path.stem
        for path in agents_dir.glob("*.md")
        if path.is_file() and path.stem.lower() != "maestro"
    )
    return ["Maestro", *names]


def _chat_sidebar(agents: list[str]) -> str:
    """Render the read-only agent picker."""
    items = "".join(
        f'<button type="button" class="chat-agent" data-testid="chat-agent-{escape(name.lower())}" '
        f'data-chat-agent="{escape(name)}" aria-selected="{"true" if index == 0 else "false"}">'
        f'<span aria-hidden="true">🤖</span><span>{escape(name)}</span></button>'
        for index, name in enumerate(agents)
    )
    return (
        '<section data-sidebar-kind="chat"><strong>Chat</strong>'
        '<div data-testid="chat-agent-list" role="listbox" aria-label="Chat agents">'
        f"{items}</div></section>"
    )


def _chat_content(agents: list[str]) -> str:
    """Render isolated transcript containers and the plain message form."""
    transcripts = "".join(
        f'<section data-testid="chat-transcript-{escape(name.lower())}" '
        f'data-agent="{escape(name)}" hidden></section>'
        for name in agents
    )
    return (
        '<div data-tab-content="chat" data-chat-panel>'
        '<section data-testid="chat-transcript" aria-live="polite">'
        f"{transcripts}</section>"
        '<form data-testid="chat-form"><input data-testid="chat-input" type="text" '
        'placeholder="Type a message to Maestro..." autocomplete="off">'
        '<button data-testid="chat-submit" type="submit">Send</button></form>'
        '<div data-testid="chat-toast" role="status" hidden></div></div>'
    )


def _devdocs(specs: list[tuple[str, list[str]]]) -> str:
    groups = []
    for spec_id, files in specs:
        children = "".join(
            f'<button type="button" data-testid="devdocs-file-{escape(Path(file).stem)}" '
            f'data-doc-path="{escape(file)}">{escape(Path(file).stem)}</button>'
            for file in files
        )
        groups.append(
            f'<details data-devdocs-spec="{escape(spec_id)}" data-expanded="false">'
            f'<summary data-testid="devdocs-spec-{escape(spec_id)}">{escape(spec_id)}</summary>'
            f"<div>{children}</div></details>"
        )
    return (
        '<section data-sidebar-kind="dev-docs" hidden><strong>Dev Docs</strong>'
        '<div data-testid="devdocs-tree">' + "".join(groups) + "</div></section>"
    )


_REFERENCE = re.compile(r"\b(?P<ref>(?:FR|NFR|US)-\d{3,4})\b")


def _devdocs_view(
    specs: list[tuple[str, list[str]]],
    specs_dir: Path,
    requested_spec: str | None,
    requested_doc: str | None,
) -> str:
    """Render the initial read-only Dev Docs preview and source panel."""
    if not specs or not specs[0][1]:
        return '<div data-tab-content="dev-docs" hidden></div>'
    spec_id, files = next(
        (
            (candidate, documents)
            for candidate, documents in specs
            if candidate == requested_spec
        ),
        specs[0],
    )
    requested_name = f"{requested_doc}.md" if requested_doc else ""
    selected = next(
        (file for file in files if Path(file).name == requested_name),
        next((file for file in files if Path(file).name == "spec.md"), files[0]),
    )
    path = specs_dir / spec_id / Path(selected).name
    body_md = path.read_text(encoding="utf-8")
    rendered_html = render_markdown_view(body_md, kind="doc").rendered_html
    links = _devdocs_cross_references(rendered_html, body_md, spec_id, specs_dir)
    visibility = "" if requested_doc else " hidden"
    return (
        f'<div data-tab-content="dev-docs"{visibility}><section data-testid="devdocs-view" style="display:block">'
        f'<div data-testid="devdocs-rendered">{links}</div>'
        f'<pre data-testid="devdocs-source">{escape(body_md)}</pre>'
        "</section></div>"
    )


def _devdocs_cross_references(
    rendered_html: str, body_md: str, spec_id: str, specs_dir: Path
) -> str:
    """Add stable links to rendered FR, NFR, and Story references."""
    anchors = {
        reference.lower()
        for reference in _REFERENCE.findall(body_md)
        if _has_document_anchor(body_md, reference)
    }

    def target(match: re.Match[str]) -> str:
        ref = match.group("ref")
        if ref.lower() in anchors:
            href = f"#{ref.lower()}"
        elif (specs_dir / spec_id / "acceptance.md").is_file():
            href = f"?spec={spec_id}&doc=acceptance#{ref.lower()}"
        else:
            href = f"#{ref.lower()}"
        return (
            f'<a data-testid="devdocs-cross-ref-{ref}" href="{escape(href, quote=True)}">'
            f"{ref}</a>"
        )

    rendered_html = re.sub(
        r'<a class="xref-link" href="#[^"]+" data-ref="(?P<ref>(?:FR|NFR)-\d{3,4})">[^<]+</a>',
        target,
        rendered_html,
    )
    return re.sub(r"\b(?P<ref>US-\d{3,4})\b", target, rendered_html)


def _has_document_anchor(body_md: str, reference: str) -> bool:
    """Return whether ``reference`` names an explicit or Markdown heading anchor."""
    anchor = re.escape(reference.lower())
    return bool(
        re.search(rf'id=["\']{anchor}["\']', body_md, re.IGNORECASE)
        or re.search(rf"^#+\s+{anchor}\b", body_md, re.IGNORECASE | re.MULTILINE)
    )


def _wiki(pages: list[str]) -> str:
    names = ["README", "design docs", *pages]
    unique = list(dict.fromkeys(names))
    links = "".join(
        f'<button type="button" data-testid="wiki-page-{escape(name)}" '
        f'data-wiki-page="{escape(name)}">{escape(name)}</button>'
        for name in unique
    )
    unknown = (
        '<button type="button" data-testid="wiki-unknown-page" '
        'data-wiki-page="unknown-page" aria-disabled="true" data-unknown="true">unknown-page</button>'
    )
    return (
        '<section data-sidebar-kind="wiki" hidden><strong>Wiki</strong>'
        '<div data-testid="wiki-tree">' + links + unknown + "</div></section>"
    )


def _end_user_docs(root: Path) -> str:
    """Render the End User Docs navigation shell."""
    docs_root = root / ".louke" / "end-user-docs"
    buttons = []
    if docs_root.is_dir():
        for path in sorted(docs_root.rglob("*.md")):
            if path.is_file() and not path.is_symlink():
                relative = path.relative_to(root).as_posix()
                buttons.append(
                    f'<button type="button" data-testid="enduserdocs-file-{escape(path.name)}" '
                    f'data-enduserdocs-path="{escape(relative)}">{escape(path.name)}</button>'
                )
    return (
        '<section data-sidebar-kind="end-user-docs" hidden><strong>End User Docs</strong>'
        '<div data-testid="enduserdocs-tree">' + "".join(buttons) + "</div></section>"
    )


def _runs_payload(root: Path) -> dict:
    """Load the optional persisted Runs read model, tolerating bad input."""
    try:
        payload = json.loads((root / ".louke" / "project" / "runs.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {"current": [], "history": [], "graphs": {}}
    return (
        payload
        if isinstance(payload, dict)
        else {"current": [], "history": [], "graphs": {}}
    )


def _runs_sidebar(root: Path) -> str:
    """Render current and historical Projects navigation for Runs."""
    payload = _runs_payload(root)
    groups = []
    for title, key in (("Current project", "current"), ("History", "history")):
        items = "".join(
            f'<button type="button" data-testid="runs-project-{escape(str(item.get("project_id", "")))}" data-run-id="{escape(str(item.get("run_id", "")))}">{escape(str(item.get("project_name", item.get("project_id", ""))))}</button>'
            for item in payload.get(key, [])
            if isinstance(item, dict)
        )
        groups.append(f"<strong>{title}</strong><div>{items}</div>")
    return (
        '<section data-sidebar-kind="runs" data-testid="runs-sidebar" hidden>'
        + "".join(groups)
        + '<a href="/projects/new">Create new project</a></section>'
    )


def _runs_content(root: Path) -> str:
    """Render graph nodes and a read-only artifact detail drawer."""
    payload = _runs_payload(root)
    graph = next(iter(payload.get("graphs", {}).values()), {})
    nodes = graph.get("nodes", []) if isinstance(graph, dict) else []
    node_html = "".join(
        f'<button type="button" data-testid="runs-node-{escape(str(node.get("stage_id", "")))}" data-stage-id="{escape(str(node.get("stage_id", "")))}">{escape(str(node.get("label", node.get("stage_id", ""))))} <span data-testid="badge-{escape(str((node.get("result") or {}).get("outcome", (node.get("result") or {}).get("verdict", "unknown"))))}"></span>'
        f"{_unknown_marker(node)}</button>"
        for node in nodes
        if isinstance(node, dict)
    )
    return f'<div data-tab-content="runs" hidden><section data-testid="runs-graph">{node_html or "Select a run to view its workflow graph"}</section><aside data-testid="stage-artifact-detail" hidden></aside></div>'


def _unknown_marker(node: dict) -> str:
    """Return the explicit fallback marker for an unrecognised result kind."""
    kind = str((node.get("result") or {}).get("kind", ""))
    if kind in {"author", "review", "gate"}:
        return ""
    return '<span data-testid="stage-unknown-fallback">unknown: true</span>'


def _page(
    toolbar: str,
    devdocs: str,
    devdocs_view: str,
    end_user_docs: str,
    wiki: str,
    runs_sidebar: str,
    chat_sidebar: str,
    chat_content: str,
    runs_content: str,
) -> str:
    settings = """<section data-settings-pane="menu"><button type="button" data-testid="settings-menu-version" aria-disabled="true" data-setting="version">版本更新</button><button type="button" data-testid="settings-menu-server" aria-disabled="true" data-setting="server">服务器配置</button><button type="button" data-testid="settings-menu-model" aria-disabled="true" data-setting="model">S/A/B 模型绑定</button></section><section data-settings-pane="detail" data-testid="settings-detail">待 v0.15</section>"""
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>Louke Workbench</title>
<style>body{{margin:0;font:14px system-ui,sans-serif}}#workbench{{display:flex;height:100vh}}[data-louke-region]{{box-sizing:border-box}}[data-louke-region=toolbar]{{width:40px;display:flex;flex-direction:column;gap:4px;padding:4px;background:#20242b}}[data-louke-region=toolbar] button{{width:32px;height:32px;padding:0;border:0;background:transparent;color:white;cursor:pointer}}[data-louke-region=toolbar] button:nth-child(6){{margin-top:auto}}[data-louke-region=sidebar]{{width:280px;padding:16px;border-right:1px solid #ddd}}[data-louke-region=main]{{flex:1;padding:12px}}[role=tablist]{{display:flex;gap:4px;border-bottom:1px solid #ddd}}[role=tab]{{padding:8px;border:0;background:#eee}}[aria-selected=true]{{background:#d8e8ff}}[data-settings-pane]{{display:inline-flex;flex-direction:column;gap:8px;padding:16px}}[aria-disabled=true]{{opacity:.55;cursor:pointer}}[data-testid=wiki-unknown-page]{{color:#888}}</style></head><body><div id="workbench">
<div data-testid="workbench-toolbar" data-louke-region="toolbar" role="toolbar" aria-label="Workbench">{toolbar}</div>
 <aside data-testid="workbench-sidebar" data-louke-region="sidebar" role="complementary" data-sidebar-kind="chat">{chat_sidebar}{devdocs}{end_user_docs}{wiki}{runs_sidebar}</aside>
 <main data-testid="workbench-main" data-louke-region="main"><div role="tablist" aria-label="Open workbench tabs"><button role="tab" data-testid="workbench-tab" data-tab-key="chat" aria-selected="true">Chat</button><button role="tab" data-testid="workbench-tab" data-tab-key="dev-docs" aria-selected="false" hidden>Dev Docs</button><button role="tab" data-testid="workbench-tab" data-tab-key="runs" aria-selected="false" hidden>Runs</button></div>{chat_content}{devdocs_view}{runs_content}</main>
<div id="accounts-menu" data-testid="accounts-menu" role="menu" hidden><button role="menuitem" data-testid="accounts-logout">Logout</button></div></div>
<script>
const tabs=new Set(['chat']); let activeTab='chat'; const labels={{chat:'Chat','dev-docs':'Dev Docs','end-user-docs':'End User Docs',wiki:'Wiki',runs:'Runs',settings:'Settings'}};
function ensureTab(tabKey){{if(tabs.has(tabKey))return;tabs.add(tabKey);const tab=document.createElement('button');tab.type='button';tab.role='tab';tab.dataset.testid='workbench-tab';tab.dataset.tabKey=tabKey;tab.textContent=labels[tabKey]||tabKey;tab.setAttribute('aria-selected','false');document.querySelector('[role="tablist"]').append(tab);}}
 function showMain(tabKey){{const main=document.querySelector('[data-louke-region="main"]');let content=main.querySelector('[data-tab-content="'+tabKey+'"]');if(!content){{content=document.createElement('div');content.dataset.tabContent=tabKey;main.append(content);}}content.hidden=false;if(tabKey==='settings')content.innerHTML={settings!r};else if(tabKey==='wiki')content.textContent='README';else if(tabKey==='dev-docs')content.textContent='Dev Docs';else if(tabKey==='end-user-docs')content.innerHTML='<div data-testid="enduserdocs-panel"><div data-testid="enduserdocs-preview"></div><textarea data-testid="enduserdocs-editor"></textarea><button type="button" data-testid="enduserdocs-save" disabled></button><span data-testid="enduserdocs-sha-display"></span><div data-testid="enduserdocs-toast" role="status" hidden></div><div data-testid="enduserdocs-conflict" hidden><strong>文件已被外部修改</strong><button type="button" data-enduserdocs-reload>重新加载并放弃我的编辑</button><button type="button" data-enduserdocs-force>仍要覆盖</button></div></div>';}}
 const saveLabel='S'+'ave'; let currentDoc=null; let currentMtime=null; let loadedBody='';
 function docPreview(body){{const preview=document.querySelector('[data-testid="enduserdocs-preview"]');preview.textContent=body;}}
 function setDocDirty(){{const editor=document.querySelector('[data-testid="enduserdocs-editor"]');const button=document.querySelector('[data-testid="enduserdocs-save"]');if(!editor||!button)return;button.disabled=editor.value===loadedBody;button.textContent=saveLabel+(button.disabled?'':' *');docPreview(editor.value);}}
 async function loadDoc(path){{openTab('end-user-docs');const response=await fetch('/api/files?path='+encodeURIComponent(path));if(!response.ok)return;const doc=await response.json();currentDoc=path;currentMtime=doc.mtime;loadedBody=doc.body_md;const editor=document.querySelector('[data-testid="enduserdocs-editor"]');editor.value=loadedBody;document.querySelector('[data-testid="enduserdocs-sha-display"]').textContent=doc.sha256;setDocDirty();}}
 async function saveDoc(force){{const editor=document.querySelector('[data-testid="enduserdocs-editor"]');const response=await fetch('/api/files',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{path:currentDoc,body_md:editor.value,expected_mtime:currentMtime,force:!!force}})}});const payload=await response.json();if(response.status===409){{const dialog=document.querySelector('[data-testid="enduserdocs-conflict"]');dialog.hidden=false;return;}}if(!response.ok){{const toast=document.querySelector('[data-testid="enduserdocs-toast"]');toast.textContent=payload.code+': '+payload.message;toast.hidden=false;return;}}loadedBody=editor.value;currentMtime=payload.version_token;document.querySelector('[data-testid="enduserdocs-sha-display"]').textContent=payload.sha256;setDocDirty();}}
function renderSidebar(activity){{const sidebar=document.querySelector('[data-louke-region="sidebar"]');sidebar.dataset.sidebarKind=activity;sidebar.querySelectorAll('section[data-sidebar-kind]').forEach(s=>s.hidden=s.dataset.sidebarKind!==activity);}}
 const transcripts={{}}; let activeAgent='Maestro';
 document.querySelectorAll('[data-chat-agent]').forEach(button=>{{transcripts[button.dataset.chatAgent]=document.querySelector('[data-testid="chat-transcript-'+button.dataset.chatAgent.toLowerCase()+'"]');}});
 function showToast(message){{const toast=document.querySelector('[data-testid="chat-toast"]');toast.textContent=message;toast.hidden=false;}}
 function selectAgent(agent){{if(!transcripts[agent]){{showToast('未知 Agent: '+agent+'; 已回退到 Maestro');agent='Maestro';}}activeAgent=agent;document.querySelectorAll('[data-chat-agent]').forEach(button=>button.setAttribute('aria-selected',String(button.dataset.chatAgent===agent)));Object.entries(transcripts).forEach(([name,node])=>node.hidden=name!==agent);const input=document.querySelector('[data-testid="chat-input"]');input.placeholder='Type a message to '+agent+'...';}}
 function openTab(activity){{ensureTab(activity);activeTab=activity;document.querySelectorAll('[data-testid="workbench-tab"]').forEach(t=>t.setAttribute('aria-selected',String(t.dataset.tabKey===activity)));if(activity!=='settings')renderSidebar(activity);showMain(activity);if(activity==='chat')selectAgent(activeAgent);}}
  document.querySelectorAll('[data-activity]').forEach(button=>button.addEventListener('click',()=>{{const activity=button.dataset.activity;if(activity==='gears')return openTab('settings');if(activity==='accounts'){{document.querySelector('[data-testid="accounts-menu"]').hidden=false;return;}}openTab(activity);}}));
  document.querySelectorAll('[data-run-id]').forEach(button=>button.addEventListener('click',()=>{{document.querySelector('[data-tab-content="runs"]').hidden=false;}}));
  document.querySelectorAll('[data-stage-id]').forEach(button=>button.addEventListener('click',async()=>{{const detail=document.querySelector('[data-testid="stage-artifact-detail"]');const run=document.querySelector('[data-run-id]')?.dataset.runId||'run-active';const item=await (await fetch('/api/ui/runs/'+run+'/stages/'+button.dataset.stageId+'/artifact')).json();detail.innerHTML='<h2>Stage artifact</h2><dl><dt>sha256</dt><dd>'+String(item.digest||'')+'</dd><dt>verdict</dt><dd>'+String(item.verdict||'')+'</dd><dt>required_reviewer</dt><dd>'+String(item.required_reviewer||'')+'</dd><dt>review_conclusion</dt><dd>'+String(item.review_conclusion||'')+'</dd></dl>';detail.hidden=false;}}));
 document.querySelector('[data-testid="chat-agent-list"]').addEventListener('click',event=>{{const button=event.target.closest('[data-chat-agent]');if(button)selectAgent(button.dataset.chatAgent);}});
 document.addEventListener('click',event=>{{const button=event.target.closest('[data-chat-agent]');if(button&&!transcripts[button.dataset.chatAgent])selectAgent(button.dataset.chatAgent);}});
 document.querySelector('[data-testid="chat-form"]').addEventListener('submit',event=>{{event.preventDefault();const input=document.querySelector('[data-testid="chat-input"]');const content=input.value;if(!content)return;const message=document.createElement('p');message.dataset.role='user';message.textContent=content;transcripts[activeAgent].append(message);input.value='';transcripts[activeAgent].scrollTop=transcripts[activeAgent].scrollHeight;}});
 selectAgent('Maestro');
document.addEventListener('click',event=>{{const item=event.target.closest('[data-setting]');if(item)document.querySelector('[data-testid="settings-detail"]').textContent='待 v0.15';}});
document.querySelector('[data-testid="accounts-logout"]').addEventListener('click',()=>fetch('/api/security/logout',{{method:'POST'}}).then(()=>location.href='/'));
 document.querySelectorAll('[data-devdocs-spec]').forEach(item=>item.addEventListener('toggle',()=>localStorage.setItem('louke.dev-docs.tree.'+item.dataset.devdocsSpec,item.open?'expanded':'collapsed')));
 document.querySelectorAll('[data-devdocs-spec]').forEach(item=>{{item.open=localStorage.getItem('louke.dev-docs.tree.'+item.dataset.devdocsSpec)==='expanded';}});
 document.querySelectorAll('[data-doc-path]').forEach(item=>item.addEventListener('click',()=>{{const parts=item.dataset.docPath.split('/');location.href='/workbench?spec='+encodeURIComponent(parts[3])+'&doc='+encodeURIComponent(parts[4].replace(/\\.md$/,''));}}));
 document.querySelectorAll('[data-wiki-page]').forEach(item=>item.addEventListener('click',()=>{{const key=item.dataset.wikiPage;if(key==='unknown-page')document.querySelector('[data-tab-content="wiki"]').innerHTML='<div data-testid="wiki-unknown-page" data-unknown="true">未知页面: '+key+' <a href="/">home</a></div>';else document.querySelector('[data-tab-content="wiki"]').textContent=key;}}));
 document.querySelectorAll('[data-enduserdocs-path]').forEach(item=>item.addEventListener('click',()=>loadDoc(item.dataset.enduserdocsPath)));
 document.addEventListener('input',event=>{{if(event.target.matches('[data-testid="enduserdocs-editor"]'))setDocDirty();}});
 document.addEventListener('click',event=>{{if(event.target.matches('[data-testid="enduserdocs-save"]'))saveDoc(false);if(event.target.matches('[data-enduserdocs-reload]'))loadDoc(currentDoc);if(event.target.matches('[data-enduserdocs-force]')&&confirm('确认覆盖外部修改？'))saveDoc(true);}});
 if(new URLSearchParams(location.search).has('doc'))openTab('dev-docs');
</script></body></html>"""
