"""FR-0701: workspace file tree + git diff HTTP API.

Mounted at /api/files. Reuses WorkspaceSecurity for read-side containment
(NFR-0201). Writes are intentionally not yet in this issue (see FR-0801).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse

from .security import WorkspaceSecurity


# FR-0801: canonical design doc basenames discoverable under .louke/project/**
DESIGN_DOC_BASENAMES = {
    "story.md",
    "spec.md",
    "acceptance.md",
    "architecture.md",
    "interfaces.md",
}


app = Starlette()


def _is_binary(p: Path) -> bool:
    """Return True if the file looks binary (NUL byte in first 8192 bytes).

    Uses a chunked read to avoid loading large files into memory. On OSError
    (unreadable / missing) returns False so callers can still report the entry.
    """
    try:
        with p.open("rb") as f:
            return b"\x00" in f.read(8192)
    except OSError:
        return False


def _ws_root() -> Path:
    """Workspace root = cwd."""
    return Path.cwd().resolve()


def _workspace() -> WorkspaceSecurity:
    return WorkspaceSecurity(_ws_root())


def _resolve_under_ws(rel: str) -> Path:
    """Resolve relative path against workspace, no traversal.

    Uses WorkspaceSecurity.read to leverage containment + symlink rejection.
    Raises PermissionError-like via the SecurityError surface; we translate.
    """
    p = Path(rel)
    if p.is_absolute():
        # Reject absolute / traversal
        try:
            p.relative_to(_ws_root())
        except ValueError:
            from .security import SecurityError

            raise SecurityError("PATH_OUTSIDE_WORKSPACE", f"absolute path {p}")
    # Try a containment read; will raise SecurityError if outside or symlink
    return _workspace().read(p).path


def _git_status(ws: Path) -> dict[str, bool]:
    """Return {relpath: changed?} based on porcelain status."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(ws), "status", "--porcelain"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {}
    result = {}
    for line in out.splitlines():
        if not line.strip():
            continue
        # format: "XY path" with leading two chars + space
        if len(line) > 3:
            path = line[3:].strip()
            result[path] = True
    return result


def _git_diff(ws: Path, rel: str) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(ws), "diff", "--", rel],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _file_entry(ws: Path, p: Path) -> dict:
    rel = p.relative_to(ws)
    try:
        binary = False
        with p.open("rb") as f:
            chunk = f.read(8192)
            if b"\x00" in chunk:
                binary = True
        line_count = sum(1 for _ in p.open("rb")) if not binary else 0
    except OSError:
        binary, line_count = False, 0
    return {
        "path": str(rel),
        "kind": "directory" if p.is_dir() else "file",
        "changed": False,
        "binary": binary,
        "line_count": line_count,
        "readable": os.access(p, os.R_OK),
        "writable": False,  # see FR-0801; this issue is read-only
        "approval_required": line_count > 500,
    }


async def list_files(request: Request):
    view = request.query_params.get("view", "tree")
    rel = request.query_params.get("path", "")
    approved = request.query_params.get("approved", "false").lower() == "true"

    ws = _ws_root()
    from .security import SecurityError

    try:
        if view == "content":
            if not rel:
                return JSONResponse(
                    {"error_code": "VALIDATION_ERROR", "message": "path required"},
                    status_code=400,
                )
            from .security import WorkspaceSecurity

            ws_sec = WorkspaceSecurity(ws)
            full = (ws / Path(rel)).resolve()
            try:
                full.relative_to(ws)
            except ValueError:
                return JSONResponse(
                    {
                        "error_code": "PATH_OUTSIDE_WORKSPACE",
                        "message": f"{rel} outside workspace",
                    },
                    status_code=403,
                )
            if _is_binary(full):
                return JSONResponse(
                    {
                        "error_code": "BINARY_NOT_PREVIEWABLE",
                        "message": "binary file not previewable",
                    },
                    status_code=403,
                )
            fc = ws_sec.read(Path(rel))
            line_count = fc.content.count("\n") + 1
            if line_count > 500 and not approved:
                return JSONResponse(
                    {
                        "error_code": "APPROVAL_REQUIRED",
                        "message": f"file is {line_count} lines, requires approved=true",
                    },
                    status_code=403,
                )
            format_ = "markdown" if fc.path.suffix.lower() == ".md" else "text"
            return JSONResponse(
                {
                    "path": str(fc.path.relative_to(ws)),
                    "content": fc.content,
                    "format": format_,
                    "line_count": line_count,
                    "revision": fc.revision,
                    "rendered_html": None,
                }
            )
        if view == "documents":
            entries = []
            for dirpath, _dirnames, filenames in os.walk(ws):
                rel_dir = Path(dirpath).relative_to(ws)
                for fname in filenames:
                    full = Path(dirpath) / fname
                    rel_path = fname if str(rel_dir) == "." else str(rel_dir / fname)
                    if not fname.endswith(".md"):
                        continue
                    if _is_binary(full):
                        continue
                    in_louke = rel_path.startswith(".louke/project/")
                    is_root_readme = rel_path == "README.md"
                    in_docs = rel_path.startswith("docs/")
                    if not (in_louke or is_root_readme or in_docs):
                        continue
                    if in_louke and fname not in DESIGN_DOC_BASENAMES:
                        continue
                    entries.append(_file_entry(ws, full))
            return JSONResponse({"view": "documents", "entries": entries})
        if view in ("tree", "changes"):
            # tree / changes views return FileEntry[]
            target = ws / rel if rel else ws
            target_rp = target.resolve()
            try:
                target_rp.relative_to(ws)
            except ValueError:
                return JSONResponse(
                    {
                        "error_code": "PATH_OUTSIDE_WORKSPACE",
                        "message": f"{rel} outside workspace",
                    },
                    status_code=403,
                )
            entries = []
            if target_rp.is_dir():
                for child in sorted(target_rp.iterdir()):
                    if child.is_dir():
                        entries.append(_file_entry(ws, child))
                    else:
                        entries.append(_file_entry(ws, child))
            else:
                entries = [_file_entry(ws, target_rp)]
            if view == "changes":
                changed = _git_status(ws)
                for e in entries:
                    e["changed"] = (
                        e["path"] in changed or e["path"].lstrip("./") in changed
                    )
            return JSONResponse({"view": view, "entries": entries})
        return JSONResponse(
            {"error_code": "VALIDATION_ERROR", "message": f"unknown view {view!r}"},
            status_code=400,
        )
    except SecurityError as e:
        return JSONResponse(
            {"error_code": e.code, "message": e.message}, status_code=403
        )


async def diff_file(request: Request):
    rel = request.query_params.get("path", "")
    if not rel:
        return JSONResponse(
            {"error_code": "VALIDATION_ERROR", "message": "path required"},
            status_code=400,
        )
    ws = _ws_root()
    # Containment check via WorkspaceSecurity (catches PATH_OUTSIDE_WORKSPACE / symlink)
    from .security import SecurityError, WorkspaceSecurity

    try:
        WorkspaceSecurity(ws).read(Path(rel))
    except SecurityError as e:
        return JSONResponse(
            {"error_code": e.code, "message": e.message}, status_code=403
        )
    diff = _git_diff(ws, rel)
    if not diff:
        # 可能是未 git 跟踪 / 未变更。返回空 diff,200 而非 409,让 e2e 自己判断。
        return JSONResponse({"path": rel, "diff": ""})
    return JSONResponse({"path": rel, "diff": diff})


# Note: starlette 路由不接受 query 中的方法 (例 GET + query view=tree)
# 我们用单一 GET entrypoint + 内部 view 分发,符合实际 REST 习惯
app.add_route("/api/files", list_files, methods=["GET"])
app.add_route("/api/files/diff", diff_file, methods=["GET"])
