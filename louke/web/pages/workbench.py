"""Workbench shell and the read-only Batch B navigation panels."""

from __future__ import annotations

from html import escape
from pathlib import Path

from starlette.requests import Request
from starlette.responses import HTMLResponse


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
    return HTMLResponse(_page(_toolbar(), _devdocs(specs), _wiki(wiki_pages)))


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
    result = []
    for directory in sorted(path for path in specs_dir.iterdir() if path.is_dir()):
        files = sorted(
            path.relative_to(root).as_posix()
            for path in directory.glob("*.md")
            if path.is_file()
        )
        result.append((directory.name, files))
    return result


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
            f"<summary>{escape(spec_id)}</summary><div>{children}</div></details>"
        )
    return (
        '<section data-sidebar-kind="dev-docs" hidden><strong>Dev Docs</strong>'
        '<div data-testid="devdocs-tree">' + "".join(groups) + "</div></section>"
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


def _page(toolbar: str, devdocs: str, wiki: str) -> str:
    settings = """<section data-settings-pane="menu"><button type="button" data-testid="settings-menu-version" aria-disabled="true" data-setting="version">版本更新</button><button type="button" data-testid="settings-menu-server" aria-disabled="true" data-setting="server">服务器配置</button><button type="button" data-testid="settings-menu-model" aria-disabled="true" data-setting="model">S/A/B 模型绑定</button></section><section data-settings-pane="detail" data-testid="settings-detail">待 v0.15</section>"""
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>Louke Workbench</title>
<style>body{{margin:0;font:14px system-ui,sans-serif}}#workbench{{display:flex;height:100vh}}[data-louke-region]{{box-sizing:border-box}}[data-louke-region=toolbar]{{width:40px;display:flex;flex-direction:column;gap:4px;padding:4px;background:#20242b}}[data-louke-region=toolbar] button{{width:32px;height:32px;padding:0;border:0;background:transparent;color:white;cursor:pointer}}[data-louke-region=toolbar] button:nth-child(6){{margin-top:auto}}[data-louke-region=sidebar]{{width:280px;padding:16px;border-right:1px solid #ddd}}[data-louke-region=main]{{flex:1;padding:12px}}[role=tablist]{{display:flex;gap:4px;border-bottom:1px solid #ddd}}[role=tab]{{padding:8px;border:0;background:#eee}}[aria-selected=true]{{background:#d8e8ff}}[data-settings-pane]{{display:inline-flex;flex-direction:column;gap:8px;padding:16px}}[aria-disabled=true]{{opacity:.55;cursor:pointer}}[data-testid=wiki-unknown-page]{{color:#888}}</style></head><body><div id="workbench">
<div data-testid="workbench-toolbar" data-louke-region="toolbar" role="toolbar" aria-label="Workbench">{toolbar}</div>
<aside data-testid="workbench-sidebar" data-louke-region="sidebar" role="complementary" data-sidebar-kind="chat"><section data-sidebar-kind="chat"><strong>Chat</strong><div data-testid="sidebar-maestro">🤖 Maestro</div></section>{devdocs}<section data-sidebar-kind="end-user-docs" hidden><strong>End User Docs</strong></section>{wiki}<section data-sidebar-kind="runs" hidden><strong>Runs</strong></section></aside>
<main data-testid="workbench-main" data-louke-region="main"><div role="tablist" aria-label="Open workbench tabs"><button role="tab" data-testid="workbench-tab" data-tab-key="chat" aria-selected="true">Chat</button><button role="tab" data-testid="workbench-tab" data-tab-key="dev-docs" aria-selected="false" hidden>Dev Docs</button><button role="tab" data-testid="workbench-tab" data-tab-key="runs" aria-selected="false" hidden>Runs</button></div><div data-tab-content="chat">Chat workspace</div></main>
<div id="accounts-menu" data-testid="accounts-menu" role="menu" hidden><button role="menuitem" data-testid="accounts-logout">Logout</button></div></div>
<script>
const tabs=new Set(['chat']); let activeTab='chat'; const labels={{chat:'Chat','dev-docs':'Dev Docs','end-user-docs':'End User Docs',wiki:'Wiki',runs:'Runs',settings:'Settings'}};
function ensureTab(tabKey){{if(tabs.has(tabKey))return;tabs.add(tabKey);const tab=document.createElement('button');tab.type='button';tab.role='tab';tab.dataset.testid='workbench-tab';tab.dataset.tabKey=tabKey;tab.textContent=labels[tabKey]||tabKey;tab.setAttribute('aria-selected','false');document.querySelector('[role="tablist"]').append(tab);}}
function showMain(tabKey){{const main=document.querySelector('[data-louke-region="main"]');let content=main.querySelector('[data-tab-content="'+tabKey+'"]');if(!content){{content=document.createElement('div');content.dataset.tabContent=tabKey;main.append(content);}}if(tabKey==='settings')content.innerHTML={settings!r};else if(tabKey==='wiki')content.textContent='README';else if(tabKey==='dev-docs')content.textContent='Dev Docs';}}
function renderSidebar(activity){{const sidebar=document.querySelector('[data-louke-region="sidebar"]');sidebar.dataset.sidebarKind=activity;sidebar.querySelectorAll('section[data-sidebar-kind]').forEach(s=>s.hidden=s.dataset.sidebarKind!==activity);}}
function openTab(activity){{ensureTab(activity);activeTab=activity;document.querySelectorAll('[data-testid="workbench-tab"]').forEach(t=>t.setAttribute('aria-selected',String(t.dataset.tabKey===activity)));if(activity!=='settings')renderSidebar(activity);showMain(activity);}}
document.querySelectorAll('[data-activity]').forEach(button=>button.addEventListener('click',()=>{{const activity=button.dataset.activity;if(activity==='gears')return openTab('settings');if(activity==='accounts'){{document.querySelector('[data-testid="accounts-menu"]').hidden=false;return;}}openTab(activity);}}));
document.addEventListener('click',event=>{{const item=event.target.closest('[data-setting]');if(item)document.querySelector('[data-testid="settings-detail"]').textContent='待 v0.15';}});
document.querySelector('[data-testid="accounts-logout"]').addEventListener('click',()=>fetch('/api/security/logout',{{method:'POST'}}).then(()=>location.href='/'));
document.querySelectorAll('[data-devdocs-spec]').forEach(item=>item.addEventListener('toggle',()=>localStorage.setItem('louke.dev-docs.tree.'+item.dataset.devdocsSpec,item.open?'expanded':'collapsed')));
document.querySelectorAll('[data-devdocs-spec]').forEach(item=>{{item.open=localStorage.getItem('louke.dev-docs.tree.'+item.dataset.devdocsSpec)==='expanded';}});
document.querySelectorAll('[data-wiki-page]').forEach(item=>item.addEventListener('click',()=>{{const key=item.dataset.wikiPage;if(key==='unknown-page')document.querySelector('[data-tab-content="wiki"]').innerHTML='<div data-testid="wiki-unknown-page" data-unknown="true">未知页面: '+key+' <a href="/">home</a></div>';else document.querySelector('[data-tab-content="wiki"]').textContent=key;}}));
</script></body></html>"""
