from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .._tools.discuss import DiscussParser
from .render import render_markdown_view
from .store import ConflictError, ProjectStore, ValidationError


def get_doc_payload(store: ProjectStore, spec_id: str, doc_name: str) -> dict[str, Any]:
    body_md, version_token, metadata = store.read_doc(spec_id, doc_name)
    rendered = render_markdown_view(body_md, kind="doc", doc_name=doc_name)
    return {
        "spec_id": spec_id,
        "doc_name": doc_name,
        "path": store.relative_path(store.doc_path(spec_id, doc_name)),
        "body_md": body_md,
        "rendered_html": rendered.rendered_html,
        "version_token": version_token,
        "updated_at": metadata.updated_at,
        "last_modified_by": metadata.last_modified_by,
        "cards": rendered.cards,
        "discussion_threads": rendered.discussion_threads,
    }


def save_doc_payload(
    store: ProjectStore,
    spec_id: str,
    doc_name: str,
    body_md: str,
    version_token: str,
    actor_name: str,
    force: bool = False,
) -> dict[str, Any]:
    token, metadata = store.write_doc(
        spec_id=spec_id,
        doc_name=doc_name,
        body_md=body_md,
        version_token=version_token,
        actor_name=actor_name,
        force=force,
    )
    payload = get_doc_payload(store, spec_id, doc_name)
    payload["version_token"] = token
    payload["updated_at"] = metadata.updated_at
    payload["last_modified_by"] = metadata.last_modified_by
    return payload


def get_wiki_payload(store: ProjectStore, page: str) -> dict[str, Any]:
    path, body_md, version_token, metadata = store.read_wiki_page(page)
    rendered = render_markdown_view(body_md, kind="wiki")
    return {
        "page": page,
        "path": store.relative_path(path),
        "body_md": body_md,
        "rendered_html": rendered.rendered_html,
        "version_token": version_token,
        "updated_at": metadata.updated_at,
        "last_modified_by": metadata.last_modified_by,
    }


def save_wiki_payload(
    store: ProjectStore,
    page: str,
    body_md: str,
    version_token: str,
    actor_name: str,
) -> dict[str, Any]:
    _, token, metadata = store.write_wiki_page(
        page=page,
        body_md=body_md,
        version_token=version_token,
        actor_name=actor_name,
    )
    payload = get_wiki_payload(store, page)
    payload["version_token"] = token
    payload["updated_at"] = metadata.updated_at
    payload["last_modified_by"] = metadata.last_modified_by
    return payload


def render_preview_payload(
    kind: str, body_md: str, doc_name: str = ""
) -> dict[str, Any]:
    rendered = render_markdown_view(body_md, kind=kind, doc_name=doc_name)
    return {
        "rendered_html": rendered.rendered_html,
        "cards": rendered.cards,
        "discussion_threads": rendered.discussion_threads,
    }


def mutate_discussion(
    store: ProjectStore,
    target_kind: str,
    target_path: str,
    version_token: str,
    actor_name: str,
    action: str,
    anchor: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    if target_kind not in {"doc", "wiki"}:
        raise ValidationError("target_kind must be doc or wiki")
    parser = DiscussParser()
    path, current_body, current_token, _ = store.read_text_target(target_path)
    if current_token != version_token:
        raise ConflictError("discussion target is stale")

    if action == "start":
        anchor_line = int(anchor.get("anchor_line") or 0)
        if anchor_line <= 0:
            raise ValidationError("start discussion requires anchor.anchor_line")
        parser.add_thread(
            path,
            anchor_line=anchor_line,
            initiator=actor_name,
            body=str(payload.get("body") or ""),
        )
    elif action == "reply":
        thread_id = str(payload.get("thread_id") or "")
        if not thread_id:
            raise ValidationError("reply requires payload.thread_id")
        loc = _thread_locate_fields(payload)
        parser.add_reply(
            path,
            thread_id=thread_id,
            body=str(payload.get("body") or ""),
            speaker=actor_name,
            **loc,
        )
    elif action == "set-status":
        thread_id = str(payload.get("thread_id") or "")
        if not thread_id:
            raise ValidationError("set-status requires payload.thread_id")
        loc = _thread_locate_fields(payload)
        parser.set_status(
            path,
            thread_id=thread_id,
            new_status=str(payload.get("status") or ""),
            operator_speaker=actor_name,
            **loc,
        )
    else:
        raise ValidationError(f"unsupported discussion action: {action}")

    event_name = "document.updated" if target_kind == "doc" else "wiki.updated"
    metadata = store.record_activity(
        event_name, path, actor_name, extra={"action": f"discussion.{action}"}
    )
    if target_kind == "doc":
        spec_id, doc_name = _doc_identity_from_path(store, path)
        response = get_doc_payload(store, spec_id, doc_name)
    else:
        response = get_wiki_payload(
            store,
            path.resolve().relative_to(store.wiki_pages_dir.resolve()).as_posix()[:-3],
        )
    response["updated_at"] = metadata.updated_at
    response["last_modified_by"] = metadata.last_modified_by
    return response


def _doc_identity_from_path(store: ProjectStore, path: Path) -> tuple[str, str]:
    relative = path.resolve().relative_to(store.specs_dir.resolve())
    spec_id = relative.parts[0]
    doc_name = path.stem if path.stem != "test-plan" else "test-plan"
    if doc_name not in {"spec", "acceptance", "test-plan"}:
        raise ValidationError(f"unsupported document path: {path}")
    return spec_id, doc_name


def _thread_locate_fields(payload: dict[str, Any]) -> dict[str, Any]:
    required = {
        "anchor_line": int(payload.get("anchor_line") or 0),
        "anchor_text": str(payload.get("anchor_text") or ""),
        "root_line": int(payload.get("root_line") or 0),
        "root_text": str(payload.get("root_text") or ""),
    }
    if required["anchor_line"] <= 0 or required["root_line"] <= 0:
        raise ValidationError("discussion mutation requires thread locate fields")
    return required


_RE_FR_HEADING = re.compile(r"^(#{1,6})\s+((?:FR|NFR)-(\d{3,4}))\b", re.IGNORECASE)
_RE_TABLE_ROW = re.compile(r"^\|(.+)\|\s*$")
_STATUS_FIELDS = {"valid": "Valid", "testable": "Testable", "decided": "Decided"}


def toggle_status_payload(
    store: ProjectStore,
    spec_id: str,
    doc_name: str,
    fr_id: str,
    field: str,
    version_token: str,
    actor_name: str,
) -> dict[str, Any]:
    body_md, current_token, _ = store.read_doc(spec_id, doc_name)
    if current_token != version_token:
        raise ConflictError("document is stale; reload before toggling status")
    header_label = _STATUS_FIELDS.get(field)
    if not header_label:
        raise ValidationError(f"unknown status field: {field}")
    fr_upper = fr_id.upper()
    lines = body_md.splitlines()
    in_section = False
    table_header_idx = -1
    target_col = -1
    changed = False
    for i, line in enumerate(lines):
        heading = _RE_FR_HEADING.match(line)
        if heading:
            if in_section:
                break
            if f"{heading.group(2).upper()}" == fr_upper:
                in_section = True
            continue
        if not in_section:
            continue
        row = _RE_TABLE_ROW.match(line)
        if not row:
            continue
        cells = [c.strip() for c in row.group(1).split("|")]
        if table_header_idx == -1:
            for ci, cell in enumerate(cells):
                if cell.lower() == header_label.lower():
                    table_header_idx = i
                    target_col = ci
                    break
            continue
        if target_col >= 0 and i == table_header_idx + 2:
            cells[target_col] = "" if cells[target_col] == "✅" else "✅"
            lines[i] = "|" + "|".join(f" {c} " for c in cells) + "|"
            changed = True
            break
    if not changed:
        raise ValidationError(f"could not find status table for {fr_id} field {field}")
    new_body = "\n".join(lines)
    if body_md.endswith("\n"):
        new_body += "\n"
    token, metadata = store.write_doc(
        spec_id, doc_name, new_body, version_token, actor_name, force=True
    )
    payload = get_doc_payload(store, spec_id, doc_name)
    payload["version_token"] = token
    payload["updated_at"] = metadata.updated_at
    payload["last_modified_by"] = metadata.last_modified_by
    return payload
