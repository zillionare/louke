"""Workspace security sandbox (NFR-0201).

Implements:
  - realpath containment in workspace root
  - symlink rejection
  - writable allowlist: only .louke/project/**/{story.md, spec.md, acceptance.md}
  - revision tracking (mtime + size hash) for conflict detection

Contracts: see .louke/project/specs/v0.11-001-web-ide/interfaces.md §1.4 + §4.2
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


WRITABLE_BASENAMES = {"story.md", "spec.md", "acceptance.md"}


class SecurityError(Exception):
    """Workspace security violation.

    `.code` is the stable machine error code matching interfaces.md §4.2
    (PATH_OUTSIDE_WORKSPACE / FILE_READ_ONLY / REVISION_CONFLICT).
    """

    def __init__(self, code: str, message: str = ""):
        self.code = code
        self.message = message or code
        super().__init__(self.message)


@dataclass
class FileContent:
    path: Path
    content: str
    revision: str


def _realpath_safe(p: Path) -> Path:
    """Resolve to realpath; strict=False so non-existent paths still resolve."""
    return p.resolve(strict=False)


def _revision_of(p: Path) -> str:
    """Stable revision token from mtime_ns + size + sha256 of content (first 8 hex)."""
    st = p.stat()
    h = hashlib.sha256()
    with p.open("rb") as f:
        h.update(f.read())
    return f"{int(st.st_mtime_ns)}-{st.st_size}-{h.hexdigest()[:8]}"


class WorkspaceSecurity:
    """Sandbox around workspace_root enforcing NFR-0201 file access rules."""

    def __init__(self, workspace_root: Path):
        self.root = _realpath_safe(workspace_root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _check_contained(self, path: Path) -> Path:
        """Return realpath of path if contained in root; else raise PATH_OUTSIDE_WORKSPACE."""
        rp = _realpath_safe(path)
        try:
            rp.relative_to(self.root)
        except ValueError:
            raise SecurityError(
                "PATH_OUTSIDE_WORKSPACE",
                f"{path} is outside workspace {self.root}",
            )
        return rp

    def _reject_symlink(self, path: Path) -> None:
        """Reject if path itself or any parent (within workspace) is a symlink."""
        if path.is_symlink():
            raise SecurityError(
                "PATH_OUTSIDE_WORKSPACE",
                f"symlink at {path} not allowed",
            )
        for parent in path.parents:
            if parent == self.root or not parent.is_relative_to(self.root):
                break
            if parent.is_symlink():
                raise SecurityError(
                    "PATH_OUTSIDE_WORKSPACE",
                    f"symlink at {parent} not allowed",
                )

    def read(self, path: Path) -> FileContent:
        """Read a file inside the workspace, returning content + revision.

        Rejects paths outside workspace, symlinks, and missing/non-file targets.
        """
        path = Path(path)
        rp = self._check_contained(path)
        self._reject_symlink(path)
        if not rp.exists() or not rp.is_file():
            raise SecurityError("PATH_OUTSIDE_WORKSPACE", f"{path} not found")
        content = rp.read_text(encoding="utf-8", errors="replace")
        return FileContent(path=rp, content=content, revision=_revision_of(rp))

    def write(self, path: Path, content: str, revision: str | None = None) -> str:
        """Write content to a writable-allowlisted file; return new revision.

        Allowlist: .louke/project/**/{story.md, spec.md, acceptance.md}.
        If file exists and `revision` is provided, must match current revision
        or REVISION_CONFLICT is raised.
        """
        path = Path(path)
        rp = self._check_contained(path)
        self._reject_symlink(path)
        rel = rp.relative_to(self.root)
        parts = rel.parts
        if len(parts) < 5 or parts[0] != ".louke" or parts[1] != "project":
            raise SecurityError("FILE_READ_ONLY", f"{path} not in writable allowlist")
        if rel.name not in WRITABLE_BASENAMES:
            raise SecurityError("FILE_READ_ONLY", f"{rel.name} not in writable allowlist")
        if rp.exists() and revision is not None:
            cur_rev = _revision_of(rp)
            if cur_rev != revision:
                raise SecurityError(
                    "REVISION_CONFLICT",
                    f"revision mismatch (current={cur_rev}, supplied={revision})",
                )
        rp.parent.mkdir(parents=True, exist_ok=True)
        tmp = rp.with_suffix(rp.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        os.replace(tmp, rp)
        return _revision_of(rp)
