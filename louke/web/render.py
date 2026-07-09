from __future__ import annotations

import html
import re
from dataclasses import dataclass

import markdown

from .._tools.discuss import DiscussParser, RE_QUOTE_LINE


RE_REQUIREMENT_HEADING = re.compile(r"^###\s+(?P<kind>FR|NFR)-(?P<num>\d{4})\s+(?P<title>.+?)\s*$")
RE_TABLE_ROW = re.compile(r"^\s*\|\s*(.+?)\s*\|\s*$")
RE_RULE = re.compile(r"^\s*---+\s*$")
RE_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass
class RenderResult:
    rendered_html: str
    cards: list[dict]
    discussion_threads: list[dict]


def render_markdown_view(body_md: str, kind: str, doc_name: str = "") -> RenderResult:
    discussion_threads = extract_discussion_threads(body_md)
    rendered_html = render_flow_html(body_md)
    cards = extract_requirement_cards(body_md) if kind == "doc" and doc_name == "spec" else []
    return RenderResult(
        rendered_html=rendered_html,
        cards=cards,
        discussion_threads=discussion_threads,
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
        parts.append(f'<section class="markdown-block">{_markdown_html(text)}</section>')

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
            status_badge = f'<span class="discussion-status">{html.escape(root["status"])}</span>'
        parts.append('<article class="discussion-thread">')
        parts.append(
            f'<header class="discussion-root">'
            f'<strong>{html.escape(root["speaker"])}</strong>{status_badge}'
            f'<p>{html.escape(root["body"])}</p>'
            f"</header>"
        )
        if len(thread) > 1:
            parts.append('<div class="discussion-replies">')
            for reply in thread[1:]:
                parts.append(
                    f'<div class="discussion-reply depth-{reply["depth"]}">'
                    f'<strong>{html.escape(reply["speaker"])}</strong>'
                    f'<p>{html.escape(reply["body"])}</p>'
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
                "id": f'{heading.group("kind")}-{heading.group("num")}',
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
        if not text or text.startswith("|") or text.startswith("#") or RE_RULE.match(text):
            continue
        return text
    return ""


def extract_status_flags(lines: list[str]) -> dict[str, bool]:
    status = {"valid": False, "testable": False, "decided": False}
    rows = [line for line in lines if RE_TABLE_ROW.match(line)]
    if len(rows) < 2:
        return status
    headers = [cell.strip() for cell in RE_TABLE_ROW.match(rows[0]).group(1).split("|")]
    values = [cell.strip() for cell in RE_TABLE_ROW.match(rows[2]).group(1).split("|")] if len(rows) > 2 else []
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
