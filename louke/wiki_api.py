"""FR-0301: 可追溯项目 Wiki. v0.11 最小可用版: 同步生成, 不走 SSE 异步 build pipeline.

5 类 canonical wiki: story / spec / test-plan / architecture / interfaces
源: <cwd>/.louke/project/specs/*/spec.md (本期只聚合 spec.md, 未来按 wiki_type 路由)
产物: <cwd>/.louke/project/wiki/{type}.md (louke.paths.wiki_path)
"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from .paths import WIKI_TYPES, wiki_path


def _specs_root() -> Path:
    """Return <cwd>/.louke/project/specs/."""
    return Path.cwd() / ".louke" / "project" / "specs"


def _source_digest(specs_root: Path) -> str:
    """SHA256 over (relative path + content) of all spec.md files, sorted.

    Returns a stable hex digest; empty-string content still hashes deterministically
    when specs_root does not exist.
    """
    h = hashlib.sha256()
    if not specs_root.exists():
        return h.hexdigest()
    for spec_md in sorted(specs_root.glob("*/spec.md")):
        rel = str(spec_md.relative_to(specs_root.parent.parent))
        h.update(rel.encode())
        h.update(b"\0")
        h.update(spec_md.read_bytes())
    return h.hexdigest()


def _slug(heading: str) -> str:
    """Convert a markdown heading to a lowercase anchor slug."""
    s = heading.lower().replace(" ", "-").replace("/", "-")
    return re.sub(r"[^a-z0-9_-]", "", s)


def _collect_sources(specs_root: Path) -> list[dict]:
    """Return [{path, anchor}] for every heading in every spec.md, sorted."""
    sources: list[dict] = []
    if not specs_root.exists():
        return sources
    for spec_md in sorted(specs_root.glob("*/spec.md")):
        rel = str(spec_md.relative_to(specs_root.parent.parent))
        for line in spec_md.read_text(encoding="utf-8").splitlines():
            m = re.match(r"^(#{1,6})\s+(.+)$", line.strip())
            if m:
                sources.append({"path": rel, "anchor": _slug(m.group(2).strip())})
    return sources


def _build_wiki_markdown(wiki_type: str, specs_root: Path) -> tuple[str, list[dict]]:
    """Aggregate spec.md files into one markdown doc with provenance links.

    Returns (markdown, sources). Each heading is followed by a
    `[source: <rel_path>#<anchor>]` line pointing back to its origin.
    """
    lines: list[str] = [f"# {wiki_type} Wiki", ""]
    sources: list[dict] = []
    if not specs_root.exists():
        return "\n".join(lines), sources
    for spec_md in sorted(specs_root.glob("*/spec.md")):
        rel = spec_md.relative_to(specs_root.parent.parent)
        spec_id = spec_md.parent.name
        lines.append(f"## {spec_id}")
        lines.append("")
        for raw in spec_md.read_text(encoding="utf-8").splitlines():
            stripped = raw.strip()
            if not stripped:
                continue
            m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if m:
                heading = m.group(2).strip()
                anchor = _slug(heading)
                lines.append(f"{m.group(1)} {heading}")
                lines.append(f"[source: {rel}#{anchor}]")
                sources.append({"path": str(rel), "anchor": anchor})
            else:
                lines.append(stripped)
        lines.append("")
    return "\n".join(lines), sources


def _has_sources(specs_root: Path) -> bool:
    """True if at least one spec.md exists under specs_root."""
    return specs_root.exists() and any(specs_root.glob("*/spec.md"))


async def get_wiki(request: Request) -> JSONResponse:
    """GET /api/wiki/{type} -> 200 WikiPage | 400 WIKI_TYPE_INVALID | 404 WIKI_SOURCE_NOT_FOUND."""
    wiki_type = request.path_params["type"]
    if wiki_type not in WIKI_TYPES:
        return JSONResponse(
            {"error_code": "WIKI_TYPE_INVALID",
             "message": f"type must be one of {sorted(WIKI_TYPES)}, got {wiki_type!r}"},
            status_code=400,
        )
    specs_root = _specs_root()
    if not _has_sources(specs_root):
        return JSONResponse(
            {"error_code": "WIKI_SOURCE_NOT_FOUND",
             "message": "no .louke/project/specs/*/spec.md found"},
            status_code=404,
        )
    md_path = wiki_path(wiki_type)
    include_content = request.query_params.get("include_content", "true").lower() != "false"
    status = "fresh" if md_path.exists() else "stale"
    body: dict[str, Any] = {
        "type": wiki_type,
        "status": status,
        "markdown": md_path.read_text(encoding="utf-8") if (include_content and md_path.exists()) else "",
        "sources": _collect_sources(specs_root),
        "updated_at": datetime.now(timezone.utc).isoformat() if md_path.exists() else None,
    }
    return JSONResponse(body)


async def put_wiki(request: Request) -> JSONResponse:
    """PUT /api/wiki/{type} -> 202 {build_id, type, status} | 400 | 404.

    Synchronous build (v0.11 minimal): computes source digest, compares to
    persisted sidecar; if unchanged returns status=unchanged without rewriting
    the wiki artifact, otherwise rebuilds and returns status=building.
    """
    wiki_type = request.path_params["type"]
    if wiki_type not in WIKI_TYPES:
        return JSONResponse(
            {"error_code": "WIKI_TYPE_INVALID",
             "message": f"type must be one of {sorted(WIKI_TYPES)}, got {wiki_type!r}"},
            status_code=400,
        )
    body = await request.json()
    trigger = body.get("trigger")
    if trigger not in ("manual", "scheduled"):
        return JSONResponse(
            {"error_code": "VALIDATION_ERROR",
             "message": "trigger must be 'manual' or 'scheduled'"},
            status_code=400,
        )
    specs_root = _specs_root()
    if not _has_sources(specs_root):
        return JSONResponse(
            {"error_code": "WIKI_SOURCE_NOT_FOUND",
             "message": "no .louke/project/specs/*/spec.md found"},
            status_code=404,
        )
    digest = _source_digest(specs_root)
    md_path = wiki_path(wiki_type)
    digest_path = md_path.with_suffix(".digest")
    stored = digest_path.read_text(encoding="utf-8").strip() if digest_path.exists() else None
    if stored == digest:
        return JSONResponse(
            {"build_id": str(uuid.uuid4()), "type": wiki_type, "status": "unchanged"},
            status_code=202,
        )
    markdown, _sources = _build_wiki_markdown(wiki_type, specs_root)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(markdown, encoding="utf-8")
    digest_path.write_text(digest, encoding="utf-8")
    return JSONResponse(
        {"build_id": str(uuid.uuid4()), "type": wiki_type, "status": "building"},
        status_code=202,
    )


app = Starlette()
app.add_route("/api/wiki/{type}", get_wiki, methods=["GET"])
app.add_route("/api/wiki/{type}", put_wiki, methods=["PUT"])
