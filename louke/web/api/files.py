"""Canonical End User Docs file API."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from starlette.requests import Request
from starlette.responses import JSONResponse


_NAME = re.compile(r"^[A-Za-z0-9_-]+$")
_MAX_BYTES = 1024 * 1024


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse({"code": code, "message": message}, status_code=status)


def _root(request: Request) -> Path:
    return request.app.state.store.root / ".louke" / "end-user-docs"


def _relative_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    prefix = Path(".louke/end-user-docs")
    if path.is_absolute() or ".." in path.parts or path.parts[:2] != prefix.parts:
        return None
    relative = Path(*path.parts[2:])
    if not relative.parts or relative.suffix != ".md":
        return None
    if any(not _NAME.fullmatch(part) for part in relative.parts[:-1]):
        return None
    if not _NAME.fullmatch(relative.stem):
        return None
    return relative


def _mtime(path: Path) -> str:
    return str(path.stat().st_mtime_ns)


def _payload(path: Path, relative: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": (Path(".louke/end-user-docs") / relative).as_posix(),
        "body_md": data.decode("utf-8"),
        "sha256": hashlib.sha256(data).hexdigest(),
        "mtime": _mtime(path),
    }


async def files(request: Request) -> JSONResponse:
    """Handle End User Docs listing, reading, and atomic saves."""
    path_value = request.query_params.get("path")
    root = _root(request)
    if request.method == "GET":
        if path_value == ".louke/end-user-docs":
            if not root.is_dir():
                return _error("NOT_FOUND", "End User Docs root was not found", 404)
            tree = []
            for item in sorted(root.rglob("*.md")):
                if not item.is_file() or item.is_symlink():
                    continue
                relative = item.relative_to(root)
                if (
                    _relative_path(f".louke/end-user-docs/{relative.as_posix()}")
                    is None
                ):
                    continue
                data = item.read_bytes()
                tree.append(
                    {
                        "name": item.name,
                        "path": f".louke/end-user-docs/{relative.as_posix()}",
                        "is_dir": False,
                        "size": len(data),
                        "sha256": hashlib.sha256(data).hexdigest(),
                    }
                )
            return JSONResponse({"tree": tree})
        relative = _relative_path(path_value)
        if relative is None:
            return _error("VALIDATION_FAILED", "invalid End User Docs path", 400)
        target = root / relative
        if not target.is_file() or target.is_symlink():
            return _error("NOT_FOUND", "document was not found", 404)
        try:
            return JSONResponse(_payload(target, relative))
        except UnicodeDecodeError:
            return _error("VALIDATION_FAILED", "document is not UTF-8", 400)

    try:
        body = await request.json()
    except ValueError:
        return _error("VALIDATION_FAILED", "request body must be JSON", 400)
    relative = _relative_path(body.get("path")) if isinstance(body, dict) else None
    if relative is None:
        return _error("PATH_NOT_ALLOWED", "path is outside End User Docs", 403)
    content = body.get("body_md")
    if not isinstance(content, str):
        return _error("VALIDATION_FAILED", "body_md must be a string", 400)
    data = content.encode("utf-8")
    if len(data) > _MAX_BYTES:
        return _error("TOO_LARGE", "document exceeds 1 MiB", 413)
    target = root / relative
    if target.is_symlink() or (target.exists() and not target.is_file()):
        return _error("PATH_NOT_ALLOWED", "target is not a regular file", 403)
    expected = body.get("expected_mtime")
    force = body.get("force") is True
    if target.exists() and not force and str(expected) != _mtime(target):
        return _error("CONFLICT", "document was modified externally", 409)
    root.mkdir(parents=True, exist_ok=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as temporary:
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_name = temporary.name
        os.replace(temporary_name, target)
    except OSError as exc:
        if "temporary_name" in locals():
            Path(temporary_name).unlink(missing_ok=True)
        return _error("VALIDATION_FAILED", f"could not save document: {exc}", 400)
    saved = target.read_bytes()
    saved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return JSONResponse(
        {
            "sha256": hashlib.sha256(saved).hexdigest(),
            "saved_at": saved_at,
            "version_token": _mtime(target),
        }
    )
