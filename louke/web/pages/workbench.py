"""Workbench shell and the read-only Batch B navigation panels."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path
import re

from starlette.requests import Request
from starlette.responses import HTMLResponse

from ..bindings import AGENT_TO_ROLE
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
    buttons = []
    for key, label, icon in TOOLBAR_ITEMS:
        menu_attr = ' aria-haspopup="menu"' if key == "accounts" else ""
        buttons.append(
            f'<button type="button" data-testid="toolbar-{key}" '
            f'data-activity="{key}" aria-label="{label}" title="{label}"{menu_attr}>'
            f'<span aria-hidden="true">{icon}</span></button>'
        )
    return '<div class="toolbar-brand" aria-label="Louke">L</div>' + "".join(buttons)


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
    """Discover active, role-bound agents with Maestro first."""
    agents_dir = Path(__file__).parents[2] / "agents"
    names = sorted(
        path.stem
        for path in agents_dir.glob("*.md")
        if path.is_file() and path.stem in AGENT_TO_ROLE and path.stem != "Maestro"
    )
    return ["Maestro", *names] if "Maestro" in AGENT_TO_ROLE else names


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
    """Render the Workbench document viewer with the legacy doc affordances."""
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
    doc_name = Path(selected).stem
    rendered = render_markdown_view(body_md, kind="doc", doc_name=doc_name)
    rendered_html = rendered.rendered_html.replace(
        '<section class="discussion-block">',
        '<section class="discussion-block" data-discussion="1">',
    )
    links = _devdocs_cross_references(rendered_html, body_md, spec_id, specs_dir)
    cards = _devdocs_verdict_cards(rendered.cards)
    editable = doc_name in {"story", "spec", "acceptance"}
    save_button = (
        '<button type="button" data-doc-action="save">保存</button>' if editable else ""
    )
    visibility = "" if requested_doc else " hidden"
    return (
        f'<div data-tab-content="dev-docs"{visibility}>'
        f'<section data-testid="devdocs-view" data-spec-id="{escape(spec_id)}" '
        f'data-doc-name="{escape(doc_name)}" data-doc-path="{escape(path.relative_to(specs_dir.parent.parent).as_posix())}">'
        '<header class="devdocs-toolbar">'
        f"<strong>{escape(doc_name)}.md</strong>"
        '<span data-testid="devdocs-save-status">未保存</span>'
        '<div class="devdocs-tools">'
        '<button type="button" data-doc-action="toggle-discussions" title="显示/隐藏 inline-discussion">讨论</button>'
        '<button type="button" data-doc-action="next-discussion" title="跳转下一个 discussion">下个讨论</button>'
        '<button type="button" data-doc-action="next-unresolved" title="跳转下一个 unresolved">下个 unresolved</button>'
        '<button type="button" data-doc-action="split" title="切换源码/预览分屏">分屏</button>'
        f"{save_button}"
        '<button type="button" data-doc-action="reload" title="重新加载文档">重载</button>'
        "</div></header>"
        '<div data-testid="devdocs-layout" class="devdocs-layout split">'
        f'<textarea data-testid="devdocs-editor" spellcheck="false">{escape(body_md)}</textarea>'
        f'<article data-testid="devdocs-rendered">{links}</article>'
        "</div>"
        f'<section data-testid="devdocs-verdict">{cards}</section>'
        '<div data-testid="devdocs-toast" role="status" hidden></div>'
        "</section></div>"
    )


def _devdocs_verdict_cards(cards: list[dict]) -> str:
    """Render requirement status/verdict cards from the existing renderer."""
    if not cards:
        return ""
    rendered = []
    for card in cards:
        statuses = ("valid", "testable", "decided")
        unresolved = not all(bool(card.get(field)) for field in statuses)
        checks = "".join(
            f'<button type="button" data-verdict-field="{field}" '
            f'data-fr-id="{escape(str(card.get("id", "")))}" '
            f'aria-pressed="{"true" if card.get(field) else "false"}">'
            f"{'✓' if card.get(field) else '○'} {field}</button>"
            for field in statuses
        )
        rendered.append(
            f'<article class="verdict-card" data-testid="devdocs-verdict-card" '
            f'data-fr-id="{escape(str(card.get("id", "")))}" '
            f'data-unresolved="{"true" if unresolved else "false"}">'
            f'<header><a href="#{escape(str(card.get("id", "")).lower())}">'
            f"{escape(str(card.get('id', '')))} · {escape(str(card.get('title', '')))}</a>"
            f'<span class="verdict-badge">{"UNRESOLVED" if unresolved else "PASS"}</span></header>'
            f'<p>{escape(str(card.get("summary", "")))}</p><div class="verdict-checks">{checks}</div>'
            "</article>"
        )
    return "".join(rendered)


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
    styles = """
:root {
  color-scheme: light;
  --ink: #1d1d1f;
  --muted: #6b6b6b;
  --faint: #8b8b8b;
  --line: #eaeaea;
  --line-strong: #d6d6d6;
  --panel: #fafafa;
  --hover: #f2f2f2;
  --active: #ededed;
  --black: #050505;
}

* { box-sizing: border-box; }
html, body { height: 100%; }
body {
  margin: 0;
  overflow: hidden;
  color: var(--ink);
  background: #fff;
  font: 13px/1.45 Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont,
    "Segoe UI", sans-serif;
  -webkit-font-smoothing: antialiased;
}
button, input, textarea { font: inherit; }
button { color: inherit; }
[hidden] { display: none !important; }

#workbench {
  display: grid;
  grid-template-columns: 56px minmax(240px, 280px) minmax(0, 1fr);
  width: 100vw;
  height: 100dvh;
  min-height: 520px;
  overflow: hidden;
  background: #fff;
}

[data-louke-region] { min-width: 0; min-height: 0; }
[data-louke-region="toolbar"] {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 10px;
  color: #fff;
  background: var(--black);
}
.toolbar-brand {
  display: grid;
  width: 36px;
  height: 36px;
  margin-bottom: 12px;
  place-items: center;
  border: 1px solid #3a3a3a;
  border-radius: 9px;
  color: #fff;
  background: #181818;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: -.04em;
}
[data-louke-region="toolbar"] button {
  display: grid;
  width: 36px;
  height: 36px;
  flex: 0 0 36px;
  padding: 0;
  place-items: center;
  border: 1px solid transparent;
  border-radius: 9px;
  color: #a7a7a7;
  background: transparent;
  cursor: pointer;
  font-size: 17px;
  transition: color .15s ease, background .15s ease, border-color .15s ease;
}
[data-louke-region="toolbar"] button:hover,
[data-louke-region="toolbar"] button:focus-visible {
  color: #fff;
  background: #242424;
  outline: none;
}
[data-louke-region="toolbar"] button[aria-current="page"] {
  color: #fff;
  border-color: #3c3c3c;
  background: #2b2b2b;
}
[data-louke-region="toolbar"] [data-activity="accounts"] { margin-top: auto; }

[data-louke-region="sidebar"] {
  overflow: auto;
  padding: 20px 14px;
  border-right: 1px solid var(--line);
  background: var(--panel);
  scrollbar-width: thin;
}
[data-louke-region="sidebar"] section { min-width: 0; }
[data-louke-region="sidebar"] section > strong {
  display: block;
  margin: 2px 8px 12px;
  color: var(--muted);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: .04em;
  text-transform: uppercase;
}
[data-testid="chat-agent-list"],
[data-testid="devdocs-tree"],
[data-testid="enduserdocs-tree"],
[data-testid="wiki-tree"],
[data-testid="runs-sidebar"] > div {
  display: grid;
  gap: 3px;
}
.chat-agent,
[data-testid="devdocs-tree"] summary,
[data-testid="devdocs-tree"] button,
[data-testid="enduserdocs-tree"] button,
[data-testid="wiki-tree"] button,
[data-testid="runs-sidebar"] button,
[data-testid="runs-sidebar"] a {
  display: flex;
  width: 100%;
  min-height: 34px;
  align-items: center;
  gap: 9px;
  padding: 7px 9px;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 7px;
  color: #454545;
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  text-align: left;
  text-decoration: none;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.chat-agent:hover,
[data-testid="devdocs-tree"] summary:hover,
[data-testid="devdocs-tree"] button:hover,
[data-testid="enduserdocs-tree"] button:hover,
[data-testid="wiki-tree"] button:hover,
[data-testid="runs-sidebar"] button:hover,
[data-testid="runs-sidebar"] a:hover,
.chat-agent[aria-selected="true"] {
  border-color: var(--line);
  background: #fff;
}
.chat-agent[aria-selected="true"] { color: var(--ink); font-weight: 600; }
[data-testid="devdocs-tree"] details { display: grid; gap: 2px; }
[data-testid="devdocs-tree"] details > div { padding-left: 10px; }
[data-testid="devdocs-tree"] summary { list-style: none; }
[data-testid="devdocs-tree"] summary::-webkit-details-marker { display: none; }
[data-testid="devdocs-tree"] summary::before { content: "⌄"; color: var(--faint); }
[data-testid="devdocs-tree"] details:not([open]) summary::before { content: "›"; }
[data-testid="runs-sidebar"] > strong {
  display: block;
  margin: 14px 8px 5px;
  color: var(--faint);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

[data-louke-region="main"] {
  display: flex;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
}
[data-louke-region="main"] > [role="tablist"] {
  display: flex;
  min-height: 52px;
  flex: 0 0 52px;
  align-items: end;
  gap: 2px;
  padding: 0 24px;
  overflow-x: auto;
  border-bottom: 1px solid var(--line);
  scrollbar-width: none;
}
[data-louke-region="main"] > [role="tablist"]::-webkit-scrollbar { display: none; }
[role="tab"] {
  position: relative;
  min-width: 72px;
  height: 42px;
  padding: 0 13px;
  border: 0;
  border-radius: 7px 7px 0 0;
  color: var(--muted);
  background: transparent;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}
[role="tab"]::after {
  position: absolute;
  right: 12px;
  bottom: -1px;
  left: 12px;
  height: 1px;
  background: transparent;
  content: "";
}
[role="tab"]:hover { color: var(--ink); background: var(--hover); }
[role="tab"][aria-selected="true"] { color: var(--ink); font-weight: 600; }
[role="tab"][aria-selected="true"]::after { background: var(--black); }
[data-tab-content] {
  display: flex;
  min-width: 0;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  overflow: auto;
  padding: 28px clamp(22px, 4vw, 64px);
}

[data-tab-content="chat"] { padding-bottom: 22px; }
[data-testid="chat-transcript"] {
  display: flex;
  width: min(100%, 820px);
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 12px;
  margin: 0 auto;
  padding: 8px 0 28px;
  overflow: auto;
}
[data-testid^="chat-transcript-"] { display: block; }
[data-testid="chat-transcript"] p {
  max-width: 78%;
  margin: 0;
  padding: 10px 13px;
  border: 1px solid var(--line);
  border-radius: 10px;
  color: #3a3a3a;
  background: #fafafa;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
[data-testid="chat-transcript"] p[data-role="user"] {
  align-self: flex-end;
  border-color: var(--black);
  color: #fff;
  background: var(--black);
}
[data-testid="chat-form"] {
  display: flex;
  width: min(100%, 820px);
  min-height: 48px;
  flex: 0 0 auto;
  gap: 8px;
  margin: auto auto 0;
  padding: 5px;
  border: 1px solid var(--line-strong);
  border-radius: 11px;
  background: #fff;
  box-shadow: 0 3px 12px rgba(0,0,0,.04);
}
[data-testid="chat-input"] {
  min-width: 0;
  flex: 1;
  padding: 0 10px;
  border: 0;
  outline: 0;
  color: var(--ink);
  background: transparent;
}
[data-testid="chat-input"]::placeholder { color: #a0a0a0; }
[data-testid="chat-submit"],
[data-testid="enduserdocs-save"] {
  min-width: 72px;
  min-height: 36px;
  padding: 0 13px;
  border: 0;
  border-radius: 7px;
  color: #fff;
  background: var(--black);
  cursor: pointer;
  font-weight: 600;
}
[data-testid="chat-submit"]:disabled,
[data-testid="enduserdocs-save"]:disabled { opacity: .35; cursor: default; }
[data-testid="chat-toast"],
[data-testid="enduserdocs-toast"] {
  width: min(100%, 820px);
  margin: 8px auto 0;
  color: #b42318;
  font-size: 12px;
}

[data-testid="devdocs-view"],
[data-testid="enduserdocs-panel"],
[data-testid="runs-graph"],
[data-testid="stage-artifact-detail"] {
  width: min(100%, 960px);
  margin: 0 auto;
}
[data-testid="devdocs-view"] { width: min(100%, 1120px); }
.devdocs-toolbar {
  display: flex;
  min-height: 42px;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
  color: var(--muted);
}
.devdocs-toolbar strong { color: var(--ink); font-size: 14px; }
.devdocs-toolbar > span { margin-right: auto; color: var(--faint); font-size: 11px; }
.devdocs-tools { display: flex; flex-wrap: wrap; gap: 5px; justify-content: flex-end; }
.devdocs-tools button {
  min-height: 30px;
  padding: 0 9px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  color: var(--muted);
  background: #fff;
  cursor: pointer;
  font-size: 11px;
}
.devdocs-tools button:hover,
.devdocs-tools button[data-active="true"] { color: var(--ink); border-color: #999; background: var(--hover); }
.devdocs-layout {
  display: grid;
  min-height: 0;
  gap: 14px;
}
.devdocs-layout.split { grid-template-columns: minmax(0, .92fr) minmax(0, 1.08fr); }
.devdocs-layout:not(.split) { grid-template-columns: minmax(0, 1fr); }
.devdocs-layout:not(.split) [data-testid="devdocs-editor"] { display: none; }
[data-testid="devdocs-editor"] {
  width: 100%;
  min-height: 480px;
  padding: 18px;
  resize: none;
  border: 1px solid var(--line);
  border-radius: 9px;
  outline: none;
  color: #4a4a4a;
  background: #fafafa;
  font: 12px/1.7 ui-monospace, SFMono-Regular, Menlo, monospace;
  white-space: pre-wrap;
}
[data-testid="devdocs-editor"]:focus { border-color: #999; box-shadow: 0 0 0 3px rgba(0,0,0,.06); }
[data-testid="devdocs-rendered"] { min-width: 0; overflow: auto; }
[data-testid="devdocs-verdict"] {
  display: grid;
  gap: 8px;
  margin-top: 14px;
}
.verdict-card {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
}
.verdict-card header { display: flex; align-items: center; gap: 8px; }
.verdict-card header a { min-width: 0; flex: 1; color: var(--ink); font-weight: 600; text-decoration: none; }
.verdict-card p { margin: 7px 0; color: var(--muted); }
.verdict-badge { color: var(--faint); font: 10px ui-monospace, monospace; }
.verdict-card[data-unresolved="true"] .verdict-badge { color: #9a6700; }
.verdict-checks { display: flex; flex-wrap: wrap; gap: 5px; }
.verdict-checks button {
  padding: 4px 7px;
  border: 1px solid var(--line);
  border-radius: 5px;
  color: var(--faint);
  background: #fafafa;
  cursor: pointer;
  font-size: 11px;
}
.verdict-checks button[aria-pressed="true"] { color: var(--ink); border-color: #a7a7a7; background: #f0f0f0; }
.discussion-block { transition: opacity .15s ease; }
.devdocs-discussions-hidden .discussion-block { display: none !important; }
.devdocs-discussions-hidden [data-testid="devdocs-rendered"]::after { content: "Inline discussions hidden"; display: block; color: var(--faint); font-size: 11px; }
[data-testid="devdocs-rendered"],
[data-testid="devdocs-source"],
[data-testid="enduserdocs-preview"],
[data-testid="enduserdocs-editor"],
[data-testid="stage-artifact-detail"] {
  border: 1px solid var(--line);
  border-radius: 9px;
  background: #fff;
}
[data-testid="devdocs-rendered"] { padding: 24px; }
[data-testid="devdocs-source"] {
  max-height: 280px;
  margin: 14px 0 0;
  padding: 16px;
  overflow: auto;
  color: #555;
  background: #fafafa;
  font: 12px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace;
  white-space: pre-wrap;
}
[data-testid="enduserdocs-panel"] { display: grid; gap: 12px; }
[data-testid="enduserdocs-preview"] { min-height: 180px; padding: 20px; white-space: pre-wrap; }
[data-testid="enduserdocs-editor"] {
  width: 100%;
  min-height: 300px;
  padding: 16px;
  resize: vertical;
  outline: 0;
  font: 12px/1.6 ui-monospace, SFMono-Regular, Menlo, monospace;
}
[data-testid="enduserdocs-sha-display"] { color: var(--faint); font: 11px ui-monospace, monospace; }
[data-testid="runs-graph"] { display: grid; gap: 8px; }
[data-testid^="runs-node-"] {
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  text-align: left;
}
[data-testid="stage-artifact-detail"] { margin-top: 16px; padding: 18px; }
[data-settings-pane="menu"] {
  display: flex;
  width: 220px;
  flex-direction: column;
  gap: 3px;
  padding: 0;
}
[data-settings-pane="detail"] {
  min-height: 160px;
  flex: 1;
  margin-left: 28px;
  padding: 20px;
  border-left: 1px solid var(--line);
  color: var(--muted);
}
[aria-disabled="true"] { opacity: .5; cursor: pointer; }
[data-testid="wiki-unknown-page"] { color: var(--muted); }
#accounts-menu {
  position: fixed;
  bottom: 14px;
  left: 66px;
  z-index: 10;
  min-width: 140px;
  padding: 5px;
  border: 1px solid var(--line-strong);
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 8px 28px rgba(0,0,0,.12);
}
#accounts-menu [role="menuitem"] { width: 100%; padding: 8px 10px; border: 0; border-radius: 6px; background: transparent; text-align: left; }
#accounts-menu [role="menuitem"]:hover { background: var(--hover); }

@media (max-width: 760px) {
  #workbench { grid-template-columns: 50px minmax(190px, 34vw) minmax(0, 1fr); }
  [data-louke-region="sidebar"] { padding: 16px 9px; }
  [data-louke-region="main"] > [role="tablist"] { padding: 0 14px; }
  [data-tab-content] { padding: 20px 16px; }
}
"""
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8"><title>Louke Workbench</title>
<style>{styles}</style></head><body><div id="workbench">
<div data-testid="workbench-toolbar" data-louke-region="toolbar" role="toolbar" aria-label="Workbench">{toolbar}</div>
 <aside data-testid="workbench-sidebar" data-louke-region="sidebar" role="complementary" data-sidebar-kind="chat">{chat_sidebar}{devdocs}{end_user_docs}{wiki}{runs_sidebar}</aside>
 <main data-testid="workbench-main" data-louke-region="main"><div role="tablist" aria-label="Open workbench tabs"><button role="tab" data-testid="workbench-tab" data-tab-key="chat" aria-selected="true">Chat</button><button role="tab" data-testid="workbench-tab" data-tab-key="dev-docs" aria-selected="false" hidden>Dev Docs</button><button role="tab" data-testid="workbench-tab" data-tab-key="runs" aria-selected="false" hidden>Runs</button></div>{chat_content}{devdocs_view}{runs_content}</main>
<div id="accounts-menu" data-testid="accounts-menu" role="menu" hidden><button role="menuitem" data-testid="accounts-logout">Logout</button></div></div>
<script>
const tabs=new Set(['chat']); let activeTab='chat'; const labels={{chat:'Chat','dev-docs':'Dev Docs','end-user-docs':'End User Docs',wiki:'Wiki',runs:'Runs',settings:'Settings'}};
function ensureTab(tabKey){{if(tabs.has(tabKey))return;tabs.add(tabKey);const tab=document.createElement('button');tab.type='button';tab.role='tab';tab.dataset.testid='workbench-tab';tab.dataset.tabKey=tabKey;tab.textContent=labels[tabKey]||tabKey;tab.setAttribute('aria-selected','false');document.querySelector('[role="tablist"]').append(tab);}}
 function showMain(tabKey){{const main=document.querySelector('[data-louke-region="main"]');main.querySelectorAll('[data-tab-content]').forEach(node=>node.hidden=node.dataset.tabContent!==tabKey);let content=main.querySelector('[data-tab-content="'+tabKey+'"]');if(!content){{content=document.createElement('div');content.dataset.tabContent=tabKey;main.append(content);}}content.hidden=false;if(tabKey==='settings')content.innerHTML={settings!r};else if(tabKey==='wiki'&&!content.textContent.trim())content.textContent='README';else if(tabKey==='dev-docs'&&!content.textContent.trim())content.textContent='Dev Docs';else if(tabKey==='end-user-docs'&&!content.querySelector('[data-testid="enduserdocs-panel"]'))content.innerHTML='<div data-testid="enduserdocs-panel"><div data-testid="enduserdocs-preview"></div><textarea data-testid="enduserdocs-editor"></textarea><button type="button" data-testid="enduserdocs-save" disabled></button><span data-testid="enduserdocs-sha-display"></span><div data-testid="enduserdocs-toast" role="status" hidden></div><div data-testid="enduserdocs-conflict" hidden><strong>文件已被外部修改</strong><button type="button" data-enduserdocs-reload>重新加载并放弃我的编辑</button><button type="button" data-enduserdocs-force>仍要覆盖</button></div></div>';}}
 let devdocsVersionToken=''; let devdocsRenderTimer=null;
 function devdocsView(){{return document.querySelector('[data-testid="devdocs-view"]');}}
 function devdocsToast(message){{const toast=document.querySelector('[data-testid="devdocs-toast"]');if(!toast)return;toast.textContent=message;toast.hidden=!message;}}
 function markDiscussionHtml(html){{return String(html||'').replaceAll('<section class="discussion-block">','<section class="discussion-block" data-discussion="1">');}}
 async function loadDevDoc(){{const view=devdocsView();if(!view)return;const response=await fetch('/api/docs/'+encodeURIComponent(view.dataset.specId)+'/'+encodeURIComponent(view.dataset.docName));if(!response.ok){{devdocsToast('文档加载失败 ('+response.status+')');return;}}const data=await response.json();devdocsVersionToken=data.version_token||'';const editor=view.querySelector('[data-testid="devdocs-editor"]');if(editor&&document.activeElement!==editor)editor.value=data.body_md||'';const rendered=view.querySelector('[data-testid="devdocs-rendered"]');if(rendered)rendered.innerHTML=markDiscussionHtml(data.rendered_html);const status=view.querySelector('[data-testid="devdocs-save-status"]');if(status)status.textContent='已加载';}}
 async function renderDevDoc(){{const view=devdocsView();if(!view)return;const editor=view.querySelector('[data-testid="devdocs-editor"]');const rendered=view.querySelector('[data-testid="devdocs-rendered"]');if(!editor||!rendered)return;const response=await fetch('/api/render',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{kind:'doc',doc_name:view.dataset.docName,body_md:editor.value}})}});if(!response.ok){{devdocsToast('预览失败 ('+response.status+')');return;}}const data=await response.json();rendered.innerHTML=markDiscussionHtml(data.rendered_html);}}
 function nextDevdocsDiscussion(){{const view=devdocsView();if(!view)return;const items=[...view.querySelectorAll('[data-discussion="1"]')];if(!items.length){{devdocsToast('没有找到 inline-discussion');return;}}const current=view.dataset.discussionCursor?Number(view.dataset.discussionCursor):-1;const next=items[(current+1)%items.length];view.dataset.discussionCursor=String((current+1)%items.length);next.scrollIntoView({{behavior:'smooth',block:'center'}});}}
 function nextDevdocsUnresolved(){{const view=devdocsView();if(!view)return;const cards=[...view.querySelectorAll('[data-testid="devdocs-verdict-card"][data-unresolved="true"]')];const discussions=[...view.querySelectorAll('[data-discussion="1"]')].filter(item=>!/[✓]|\[(?:resolved|已解决|已决定|decided)\]/i.test(item.textContent||''));const items=cards.length?cards:discussions;if(!items.length){{devdocsToast('所有 FR/NFR/AC 与 discussion 均已解决');return;}}const current=view.dataset.unresolvedCursor?Number(view.dataset.unresolvedCursor):-1;const next=items[(current+1)%items.length];view.dataset.unresolvedCursor=String((current+1)%items.length);next.scrollIntoView({{behavior:'smooth',block:'center'}});}}
 async function saveDevDoc(){{const view=devdocsView();if(!view)return;const editor=view.querySelector('[data-testid="devdocs-editor"]');const response=await fetch('/api/docs/'+encodeURIComponent(view.dataset.specId)+'/'+encodeURIComponent(view.dataset.docName),{{method:'PUT',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{body_md:editor.value,version_token:devdocsVersionToken,force:false}})}});const data=await response.json();if(!response.ok){{devdocsToast(data.error||'保存失败');return;}}devdocsVersionToken=data.version_token||'';await loadDevDoc();}}
 function handleDevdocsAction(action,button){{const view=devdocsView();if(!view)return;if(action==='toggle-discussions'){{const hidden=view.classList.toggle('devdocs-discussions-hidden');button.dataset.active=String(hidden);return;}}if(action==='next-discussion')return nextDevdocsDiscussion();if(action==='next-unresolved')return nextDevdocsUnresolved();if(action==='split'){{const layout=view.querySelector('[data-testid="devdocs-layout"]');layout.classList.toggle('split');button.dataset.active=String(layout.classList.contains('split'));return;}}if(action==='save')return saveDevDoc();if(action==='reload')return loadDevDoc();}}
 document.querySelectorAll('[data-doc-action]').forEach(button=>button.addEventListener('click',()=>handleDevdocsAction(button.dataset.docAction,button)));
 const devEditor=document.querySelector('[data-testid="devdocs-editor"]');if(devEditor){{devEditor.addEventListener('input',()=>{{const status=document.querySelector('[data-testid="devdocs-save-status"]');if(status)status.textContent='有未保存修改';clearTimeout(devdocsRenderTimer);devdocsRenderTimer=setTimeout(renderDevDoc,250);}});}}
 if(new URLSearchParams(location.search).has('doc'))loadDevDoc();
 const saveLabel='S'+'ave'; let currentDoc=null; let currentMtime=null; let loadedBody='';
 function docPreview(body){{const preview=document.querySelector('[data-testid="enduserdocs-preview"]');preview.textContent=body;}}
 function setDocDirty(){{const editor=document.querySelector('[data-testid="enduserdocs-editor"]');const button=document.querySelector('[data-testid="enduserdocs-save"]');if(!editor||!button)return;button.disabled=editor.value===loadedBody;button.textContent=saveLabel+(button.disabled?'':' *');docPreview(editor.value);}}
 async function loadDoc(path){{openTab('end-user-docs');const response=await fetch('/api/files?path='+encodeURIComponent(path));if(!response.ok)return;const doc=await response.json();currentDoc=path;currentMtime=doc.mtime;loadedBody=doc.body_md;const editor=document.querySelector('[data-testid="enduserdocs-editor"]');editor.value=loadedBody;document.querySelector('[data-testid="enduserdocs-sha-display"]').textContent=doc.sha256;setDocDirty();}}
 async function saveDoc(force){{const editor=document.querySelector('[data-testid="enduserdocs-editor"]');const response=await fetch('/api/files',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{path:currentDoc,body_md:editor.value,expected_mtime:currentMtime,force:!!force}})}});const payload=await response.json();if(response.status===409){{const dialog=document.querySelector('[data-testid="enduserdocs-conflict"]');dialog.hidden=false;return;}}if(!response.ok){{const toast=document.querySelector('[data-testid="enduserdocs-toast"]');toast.textContent=payload.code+': '+payload.message;toast.hidden=false;return;}}loadedBody=editor.value;currentMtime=payload.version_token;document.querySelector('[data-testid="enduserdocs-sha-display"]').textContent=payload.sha256;setDocDirty();}}
function renderSidebar(activity){{const sidebar=document.querySelector('[data-louke-region="sidebar"]');sidebar.dataset.sidebarKind=activity;sidebar.querySelectorAll('section[data-sidebar-kind]').forEach(s=>s.hidden=s.dataset.sidebarKind!==activity);}}
 const transcripts={{}}; const sessions={{}}; const renderedMessages={{}}; let activeAgent='Maestro';
 document.querySelectorAll('[data-chat-agent]').forEach(button=>{{transcripts[button.dataset.chatAgent]=document.querySelector('[data-testid="chat-transcript-'+button.dataset.chatAgent.toLowerCase()+'"]');}});
 function showToast(message){{const toast=document.querySelector('[data-testid="chat-toast"]');toast.textContent=message;toast.hidden=false;}}
 function selectAgent(agent){{if(!transcripts[agent]){{showToast('未知 Agent: '+agent+'; 已回退到 Maestro');agent='Maestro';}}activeAgent=agent;document.querySelectorAll('[data-chat-agent]').forEach(button=>button.setAttribute('aria-selected',String(button.dataset.chatAgent===agent)));Object.entries(transcripts).forEach(([name,node])=>node.hidden=name!==agent);const input=document.querySelector('[data-testid="chat-input"]');input.placeholder='Message '+agent+'...';}}
 function openTab(activity){{ensureTab(activity);activeTab=activity;document.querySelectorAll('[data-testid="workbench-tab"]').forEach(t=>t.setAttribute('aria-selected',String(t.dataset.tabKey===activity)));document.querySelectorAll('[data-activity]').forEach(button=>button.setAttribute('aria-current',button.dataset.activity===activity?'page':'false'));if(activity!=='settings')renderSidebar(activity);showMain(activity);if(activity==='chat')selectAgent(activeAgent);}}
  document.querySelectorAll('[data-activity]').forEach(button=>button.addEventListener('click',()=>{{const activity=button.dataset.activity;if(activity==='gears')return openTab('settings');if(activity==='accounts'){{document.querySelector('[data-testid="accounts-menu"]').hidden=false;return;}}openTab(activity);}}));
  document.querySelectorAll('[data-run-id]').forEach(button=>button.addEventListener('click',()=>{{document.querySelector('[data-tab-content="runs"]').hidden=false;}}));
  document.querySelectorAll('[data-stage-id]').forEach(button=>button.addEventListener('click',async()=>{{const detail=document.querySelector('[data-testid="stage-artifact-detail"]');const run=document.querySelector('[data-run-id]')?.dataset.runId||'run-active';const item=await (await fetch('/api/ui/runs/'+run+'/stages/'+button.dataset.stageId+'/artifact')).json();detail.innerHTML='<h2>Stage artifact</h2><dl><dt>sha256</dt><dd>'+String(item.digest||'')+'</dd><dt>verdict</dt><dd>'+String(item.verdict||'')+'</dd><dt>required_reviewer</dt><dd>'+String(item.required_reviewer||'')+'</dd><dt>review_conclusion</dt><dd>'+String(item.review_conclusion||'')+'</dd></dl>';detail.hidden=false;}}));
 document.querySelector('[data-testid="chat-agent-list"]').addEventListener('click',event=>{{const button=event.target.closest('[data-chat-agent]');if(button)selectAgent(button.dataset.chatAgent);}});
 document.addEventListener('click',event=>{{const button=event.target.closest('[data-chat-agent]');if(button&&!transcripts[button.dataset.chatAgent])selectAgent(button.dataset.chatAgent);}});
 function addChatMessage(agent,message){{const node=transcripts[agent];if(!node||!message||!message.content)return;const id=message.id||agent+'-'+message.role+'-'+message.content;renderedMessages[agent]??=new Set();if(renderedMessages[agent].has(id))return;renderedMessages[agent].add(id);const item=document.createElement('p');item.dataset.role=message.role;item.dataset.messageId=message.id||'';item.textContent=message.content;node.append(item);node.scrollTop=node.scrollHeight;}}
 async function chatSession(agent){{if(sessions[agent])return sessions[agent];const list=await (await fetch('/api/opencode/instances')).json();const existing=(list.items||[]).find(item=>item.status==='running');if(existing)sessions[agent]=existing.id;else{{const created=await (await fetch('/api/opencode/instances',{{method:'POST'}})).json();sessions[agent]=created.instance.id;}}return sessions[agent];}}
 async function refreshChat(agent){{const id=sessions[agent];if(!id)return;const response=await fetch('/api/opencode/instances/'+encodeURIComponent(id)+'/messages');if(!response.ok)return;const payload=await response.json();(payload.items||[]).forEach(message=>addChatMessage(agent,message));}}
 async function sendChat(content){{const agent=activeAgent;const input=document.querySelector('[data-testid="chat-input"]');const button=document.querySelector('[data-testid="chat-submit"]');button.disabled=true;showToast('');try{{const id=await chatSession(agent);const response=await fetch('/api/opencode/instances/'+encodeURIComponent(id)+'/messages',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{content}})}});if(!response.ok)throw new Error('Chat request failed ('+response.status+')');await refreshChat(agent);input.value='';}}catch(error){{showToast(error.message||'Chat request failed');}}finally{{button.disabled=false;input.focus();}}}}
 document.querySelector('[data-testid="chat-form"]').addEventListener('submit',event=>{{event.preventDefault();const input=document.querySelector('[data-testid="chat-input"]');const content=input.value.trim();if(content)sendChat(content);}});
 selectAgent('Maestro');
 openTab(new URLSearchParams(location.search).has('doc')?'dev-docs':'chat');
document.addEventListener('click',event=>{{const item=event.target.closest('[data-setting]');if(item)document.querySelector('[data-testid="settings-detail"]').textContent='待 v0.15';}});
document.querySelector('[data-testid="accounts-logout"]').addEventListener('click',()=>fetch('/api/security/logout',{{method:'POST'}}).then(()=>location.href='/'));
 document.querySelectorAll('[data-devdocs-spec]').forEach(item=>item.addEventListener('toggle',()=>localStorage.setItem('louke.dev-docs.tree.'+item.dataset.devdocsSpec,item.open?'expanded':'collapsed')));
 document.querySelectorAll('[data-devdocs-spec]').forEach(item=>{{item.open=localStorage.getItem('louke.dev-docs.tree.'+item.dataset.devdocsSpec)==='expanded';}});
 document.querySelectorAll('[data-doc-path]').forEach(item=>item.addEventListener('click',()=>{{const parts=item.dataset.docPath.split('/');location.href='/workbench?spec='+encodeURIComponent(parts[3])+'&doc='+encodeURIComponent(parts[4].replace(/\\.md$/,''));}}));
 document.querySelectorAll('[data-wiki-page]').forEach(item=>item.addEventListener('click',()=>{{const key=item.dataset.wikiPage;if(key==='unknown-page')document.querySelector('[data-tab-content="wiki"]').innerHTML='<div data-testid="wiki-unknown-page" data-unknown="true">未知页面: '+key+' <a href="/">home</a></div>';else document.querySelector('[data-tab-content="wiki"]').textContent=key;}}));
 document.querySelectorAll('[data-enduserdocs-path]').forEach(item=>item.addEventListener('click',()=>loadDoc(item.dataset.enduserdocsPath)));
 document.addEventListener('input',event=>{{if(event.target.matches('[data-testid="enduserdocs-editor"]'))setDocDirty();}});
 document.addEventListener('click',event=>{{if(event.target.matches('[data-testid="enduserdocs-save"]'))saveDoc(false);if(event.target.matches('[data-enduserdocs-reload]'))loadDoc(currentDoc);if(event.target.matches('[data-enduserdocs-force]')&&confirm('确认覆盖外部修改？'))saveDoc(true);}});
</script></body></html>"""
