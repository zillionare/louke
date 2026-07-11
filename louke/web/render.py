from __future__ import annotations

import html
import re
from dataclasses import dataclass

import markdown

from .._tools.discuss import DiscussParser, RE_QUOTE_LINE


RE_REQUIREMENT_HEADING = re.compile(
    r"^###\s+(?P<kind>FR|NFR)-(?P<num>\d{4})\s+(?P<title>.+?)\s*$"
)
RE_TABLE_ROW = re.compile(r"^\s*\|\s*(.+?)\s*\|\s*$")
RE_RULE = re.compile(r"^\s*---+\s*$")
RE_FENCE = re.compile(r"^\s*(```|~~~)")

# FR-0700: cross-reference linkification patterns
RE_ANY_REF = re.compile(
    r"\b(?:(?P<prefix>\d+|[A-Za-z]+)-)?(?P<ref>(?:FR|NFR)-(?P<num>\d{3,4}))\b"
)
RE_HEADING_TAG = re.compile(r"<(h[1-6])([^>]*)>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
RE_FR_IN_HEADING = re.compile(r"^\s*((?:FR|NFR)-(\d{3,4}))", re.IGNORECASE)

# Wiki-style link: [[page-name]] or [[page-name|display text]].
# Supports nested pages with slashes (e.g. [[guides/getting-started]]).
# Reserved characters inside the page name: alphanumeric, dot, dash,
# underscore, slash. Display text (after '|') is anything except ']'.
RE_WIKI_LINK = re.compile(r"\[\[([A-Za-z0-9._/\-]+)(?:\|([^\]]+))?\]\]")


@dataclass
class RenderResult:
    rendered_html: str
    cards: list[dict]
    discussion_threads: list[dict]


def render_markdown_view(body_md: str, kind: str, doc_name: str = "") -> RenderResult:
    discussion_threads = extract_discussion_threads(body_md)
    # Pre-process [[wiki-links]] to standard markdown links BEFORE
    # rendering. Doing this here (rather than after) means the link
    # text is parsed as part of normal markdown and won't accidentally
    # match other post-processors (e.g. FR-XXXX detection).
    body_md = _expand_wiki_links(body_md, kind=kind)
    rendered_html = render_flow_html(body_md)
    rendered_html = _add_heading_anchors(rendered_html)
    rendered_html = _linkify_references(rendered_html)
    cards = (
        extract_requirement_cards(body_md)
        if kind == "doc" and doc_name == "spec"
        else []
    )
    return RenderResult(
        rendered_html=rendered_html,
        cards=cards,
        discussion_threads=discussion_threads,
    )


def _expand_wiki_links(body_md: str, kind: str = "") -> str:
    """Convert [[page]] / [[page|text]] to standard markdown links.

    Only runs on wiki documents to avoid breaking inline-discussion
    threads that may legitimately use [[ ]] in spec bodies. The link
    target is /wiki/<page> (or relative if a base is provided).
    """
    if kind != "wiki":
        return body_md

    def replace_wiki(m: re.Match) -> str:
        page = m.group(1)
        display = m.group(2) or page
        # Encode path components (slashes preserved) so nested pages work.
        from urllib.parse import quote

        encoded = quote(page, safe="/")
        return f"[{display}](/wiki/{encoded})"

    return RE_WIKI_LINK.sub(replace_wiki, body_md)


def _add_heading_anchors(html_str: str) -> str:
    """Inject <a id="fr-xxxx"> anchors into headings that start with FR-XXXX or NFR-XXXX."""

    def replace_heading(m: re.Match) -> str:
        tag = m.group(1)
        attrs = m.group(2)
        content = m.group(3)
        fr_match = RE_FR_IN_HEADING.match(content)
        if fr_match:
            anchor_id = fr_match.group(1).lower()
            return f'<{tag}{attrs}><a id="{anchor_id}"></a>{content}</{tag}>'
        return m.group(0)

    return RE_HEADING_TAG.sub(replace_heading, html_str)


def _linkify_references(html_str: str) -> str:
    """Replace FR-XXXX, NFR-XXXX, and prefix-FR-XXXX patterns in text with clickable links.

    Skips text inside <h1>-<h6>, <code>, <pre>, and <a> tags to avoid corrupting
    existing markup or creating self-referencing links in headings.
    """
    parts = re.split(r"(<[^>]+>)", html_str)
    in_heading = False
    in_code = False
    in_link = False
    for i, part in enumerate(parts):
        if part.startswith("<"):
            lower = part.lower()
            if re.match(r"<h[1-6]", lower):
                in_heading = True
            elif re.match(r"</h[1-6]", lower):
                in_heading = False
            elif re.match(r"<(?:code|pre)[\s>]", lower):
                in_code = True
            elif re.match(r"</(?:code|pre)>", lower):
                in_code = False
            elif re.match(r"<a[\s>]", lower):
                in_link = True
            elif re.match(r"</a>", lower):
                in_link = False
            continue
        if in_heading or in_code or in_link:
            continue
        parts[i] = RE_ANY_REF.sub(_make_ref_link, part)
    return "".join(parts)


def _make_ref_link(m: re.Match) -> str:
    prefix = m.group("prefix")
    ref = m.group("ref")
    if prefix:
        return (
            f'<a class="xref-link xref-cross" href="#" '
            f'data-spec="{html.escape(prefix)}" data-ref="{html.escape(ref)}">'
            f"{html.escape(prefix)}-{html.escape(ref)}</a>"
        )
    return (
        f'<a class="xref-link" href="#{ref.lower()}" data-ref="{html.escape(ref)}">'
        f"{html.escape(ref)}</a>"
    )


def extract_discussion_threads(body_md: str) -> list[dict]:
    parser = DiscussParser()
    result = parser._parse(body_md, body_md.splitlines())
    threads = []
    for thread in result.threads:
        threads.append(
            {
                "thread_id": thread.thread_id,
                "initiator": thread.initiator,
                "status": thread.status,
                "last_speaker": thread.last_speaker,
                "reply_count": thread.reply_count,
                "snippet": thread.snippet,
                "mentioned_agents": thread.mentioned_agents,
                "total_lines": thread.total_lines,
                "anchor_line": thread.anchor_line,
                "anchor_text": thread.anchor_text,
                "root_line": thread.root_line,
                "root_text": thread.root_text,
            }
        )
    return threads


def render_flow_html(body_md: str) -> str:
    lines = body_md.splitlines()
    normal_buffer: list[str] = []
    parts: list[str] = []
    quote_buffer: list[str] = []
    in_code_block = False
    saw_quote = False

    def flush_normal() -> None:
        nonlocal normal_buffer
        if not normal_buffer:
            return
        text = "\n".join(normal_buffer).strip("\n")
        normal_buffer = []
        if not text.strip():
            return
        parts.append(
            f'<section class="markdown-block">{_markdown_html(text)}</section>'
        )

    def flush_quote() -> None:
        nonlocal quote_buffer, saw_quote
        if not quote_buffer:
            return
        parts.append(render_discussion_block(quote_buffer))
        quote_buffer = []
        saw_quote = False

    for line in lines:
        if RE_FENCE.match(line):
            if saw_quote:
                flush_quote()
            normal_buffer.append(line)
            in_code_block = not in_code_block
            continue

        if not in_code_block and RE_QUOTE_LINE.match(line):
            saw_quote = True
            flush_normal()
            quote_buffer.append(line)
            continue

        if saw_quote:
            if line.strip() == "":
                quote_buffer.append(line)
                continue
            flush_quote()

        normal_buffer.append(line)

    flush_quote()
    flush_normal()
    return "\n".join(parts)


def render_discussion_block(lines: list[str]) -> str:
    threads: list[list[dict]] = []
    current: list[dict] = []
    for line in lines:
        match = RE_QUOTE_LINE.match(line)
        if not match:
            continue
        depth = match.group("depth").count(">")
        speaker = match.group("speaker").strip("*")
        speaker = speaker.lstrip("@")
        body = match.group("body").strip()
        status = (match.group("status") or "").lower()
        comment = {
            "depth": depth,
            "speaker": speaker,
            "status": status,
            "body": body,
        }
        if depth == 1:
            if current:
                threads.append(current)
            current = [comment]
        elif current:
            current.append(comment)
    if current:
        threads.append(current)

    parts = ['<section class="discussion-block">']
    for thread in threads:
        root = thread[0]
        status_badge = ""
        if root["status"]:
            status_badge = (
                f'<span class="discussion-status">{html.escape(root["status"])}</span>'
            )
        parts.append('<article class="discussion-thread">')
        parts.append(
            f'<header class="discussion-root">'
            f"<strong>{html.escape(root['speaker'])}</strong>{status_badge}"
            f"<p>{html.escape(root['body'])}</p>"
            f"</header>"
        )
        if len(thread) > 1:
            parts.append('<div class="discussion-replies">')
            for reply in thread[1:]:
                parts.append(
                    f'<div class="discussion-reply depth-{reply["depth"]}">'
                    f"<strong>{html.escape(reply['speaker'])}</strong>"
                    f"<p>{html.escape(reply['body'])}</p>"
                    f"</div>"
                )
            parts.append("</div>")
        parts.append("</article>")
    parts.append("</section>")
    return "\n".join(parts)


def extract_requirement_cards(body_md: str) -> list[dict]:
    lines = body_md.splitlines()
    cards: list[dict] = []
    current: dict | None = None
    section_lines: list[str] = []

    def flush() -> None:
        nonlocal current, section_lines
        if current is None:
            return
        current["summary"] = extract_summary(section_lines)
        current.update(extract_status_flags(section_lines))
        cards.append(current)
        current = None
        section_lines = []

    for line in lines:
        heading = RE_REQUIREMENT_HEADING.match(line)
        if heading:
            flush()
            current = {
                "id": f"{heading.group('kind')}-{heading.group('num')}",
                "kind": heading.group("kind"),
                "title": heading.group("title").strip(),
            }
            section_lines = []
            continue
        if current is not None:
            section_lines.append(line)
    flush()
    return cards


def extract_summary(lines: list[str]) -> str:
    for line in lines:
        text = line.strip()
        if (
            not text
            or text.startswith("|")
            or text.startswith("#")
            or RE_RULE.match(text)
        ):
            continue
        return text
    return ""


def extract_status_flags(lines: list[str]) -> dict[str, bool]:
    status = {"valid": False, "testable": False, "decided": False}
    rows = [line for line in lines if RE_TABLE_ROW.match(line)]
    if len(rows) < 2:
        return status
    headers = [cell.strip() for cell in RE_TABLE_ROW.match(rows[0]).group(1).split("|")]
    values = (
        [cell.strip() for cell in RE_TABLE_ROW.match(rows[2]).group(1).split("|")]
        if len(rows) > 2
        else []
    )
    mapping = dict(zip(headers, values))
    status["valid"] = mapping.get("Valid", "") == "✅"
    status["testable"] = mapping.get("Testable", "") == "✅"
    status["decided"] = mapping.get("Decided", "") == "✅"
    return status


def _markdown_html(text: str) -> str:
    return markdown.markdown(
        text,
        extensions=["extra", "sane_lists", "toc"],
        output_format="html5",
    )


_RE_RESOLVED_MARKER = re.compile(
    r"\[resolved\]|\[已决定\]|\[已解决\]|\[Decided\]|\[decided\]"
    r"|\u2713\s*resolved",
    re.IGNORECASE,
)
_RE_DISCUSSION_MARKER = re.compile(
    r"\[T-\d{3,4}\]|\*\*\[?[A-Za-z][\w@]*\]?\*\*:"
    r"|^\s*>+\s",
    re.MULTILINE,
)


def is_resolved_text(text: str) -> bool:
    """Return True if text contains an inline-discussion resolved marker."""
    return bool(text and _RE_RESOLVED_MARKER.search(text))


def is_discussion_text(text: str) -> bool:
    """Return True if text looks like an inline-discussion line/block."""
    return bool(text and _RE_DISCUSSION_MARKER.search(text))


def scan_discussion_blocks(body_md: str) -> list[dict]:
    """Scan markdown for inline-discussion lines and return their status.

    Each entry: {"line": 1-based line number, "text": stripped line, "resolved": bool}.
    The JS filter/next-discussion uses the same matching rules (see app.py).
    """
    results: list[dict] = []
    for i, raw in enumerate(body_md.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        if is_discussion_text(line):
            results.append(
                {"line": i, "text": line, "resolved": is_resolved_text(line)}
            )
    return results
