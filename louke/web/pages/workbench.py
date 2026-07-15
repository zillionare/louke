"""Workbench shell page for the v0.13 browser chrome."""

from __future__ import annotations

from starlette.responses import HTMLResponse
from starlette.requests import Request


TOOLBAR_ITEMS = (
    ("chat", "Chat", "💬"),
    ("dev-docs", "Dev Docs", "▤"),
    ("end-user-docs", "End User Docs", "▥"),
    ("wiki", "Wiki", "◈"),
    ("runs", "Runs", "▶"),
    ("accounts", "Accounts", "●"),
    ("gears", "Settings", "⚙"),
)


def create_app() -> object:
    """Return the workbench endpoint callable for the main Starlette app."""
    return workbench


async def workbench(request: Request) -> HTMLResponse:
    """Render the single-page workbench shell with its semantic landmarks."""
    toolbar = "".join(
        f'<button type="button" data-testid="toolbar-{key}" '
        f'data-activity="{key}" aria-label="{label}" title="{label}">'
        f'<span aria-hidden="true">{icon}</span></button>'
        for key, label, icon in TOOLBAR_ITEMS
    )
    return HTMLResponse(_page(toolbar))


def _page(toolbar: str) -> str:
    """Build the shell document without introducing a client framework."""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Louke Workbench</title>
<style>
body{{margin:0;font:14px system-ui,sans-serif}}#workbench{{display:flex;height:100vh}}
[data-louke-region]{{box-sizing:border-box}}[data-louke-region=toolbar]{{width:40px;display:flex;flex-direction:column;gap:4px;padding:4px;background:#20242b}}
[data-louke-region=toolbar] button{{width:32px;height:32px;padding:0;border:0;background:transparent;color:white;cursor:pointer}}
[data-louke-region=toolbar] button:nth-child(6){{margin-top:auto}}[data-louke-region=sidebar]{{width:280px;padding:16px;border-right:1px solid #ddd}}
[data-louke-region=main]{{flex:1;padding:12px}}[role=tablist]{{display:flex;gap:4px;border-bottom:1px solid #ddd}}
[role=tab]{{padding:8px;border:0;background:#eee}}[aria-selected=true]{{background:#d8e8ff}}
</style></head><body><div id="workbench">
<div data-testid="workbench-toolbar" data-louke-region="toolbar" role="toolbar" aria-label="Workbench">{toolbar}</div>
<aside data-testid="workbench-sidebar" data-louke-region="sidebar" role="complementary" data-sidebar-kind="chat">
<section data-sidebar-kind="chat"><strong>Chat</strong><div data-testid="sidebar-maestro">🤖 Maestro</div></section>
<section data-sidebar-kind="dev-docs" hidden><strong>Dev Docs</strong><div data-testid="sidebar-specs">Specs</div></section>
<section data-sidebar-kind="end-user-docs" hidden><strong>End User Docs</strong><div data-testid="sidebar-guides">Guides</div></section>
<section data-sidebar-kind="wiki" hidden><strong>Wiki</strong><div data-testid="sidebar-home">Home</div></section>
<section data-sidebar-kind="runs" hidden><strong>Runs</strong><div data-testid="sidebar-history">History</div></section>
</aside>
<main data-testid="workbench-main" data-louke-region="main"><div role="tablist" aria-label="Open workbench tabs">
<button role="tab" data-testid="workbench-tab" data-tab-key="chat" aria-selected="true">Chat</button>
<button role="tab" data-testid="workbench-tab" data-tab-key="dev-docs" aria-selected="false">Dev Docs</button>
<button role="tab" data-testid="workbench-tab" data-tab-key="runs" aria-selected="false">Runs</button>
</div><div data-tab-content="chat">Chat workspace</div></main></div>
<script>
const tabs=new Set(['chat']); let activeTab='chat';
function renderSidebar(activity) {{
  const sidebar=document.querySelector('[data-louke-region="sidebar"]');
  sidebar.dataset.sidebarKind=activity;
  sidebar.querySelectorAll('section[data-sidebar-kind]').forEach(section => {{ section.hidden=section.dataset.sidebarKind!==activity; }});
}}
function openTab(tabKey) {{
  if (!tabs.has(tabKey)) tabs.add(tabKey);
  activeTab=tabKey;
  document.querySelectorAll('[data-testid="workbench-tab"]').forEach(tab => {{ tab.setAttribute('aria-selected', String(tab.dataset.tabKey===tabKey)); }});
  renderSidebar(tabKey);
}}
document.querySelectorAll('[data-activity]').forEach(button => button.addEventListener('click', () => {{
  const activity=button.dataset.activity;
  if (activity==='gears') return openTab('settings');
  if (activity==='accounts') return;
  openTab(activity);
}}));
</script></body></html>"""
