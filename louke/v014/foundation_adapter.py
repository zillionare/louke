"""Real Git/GitHub Foundation adapter for the v0.14 public entry."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from louke.v014.release_entry import FoundationOutcome, MainCheck


class ShellFoundationAdapter:
    """Reconcile Foundation through safe, explicit ``git`` and ``gh`` commands."""

    def __init__(self, workspace_root: str | Path, *, spec_id: str) -> None:
        self._root = Path(workspace_root).resolve()
        self._spec_id = spec_id

    def preflight(self, story: str, release_version: str) -> MainCheck:
        """Refresh origin/main and return full Git identity and relation evidence."""
        fetched, fetch_error = self._run("git", "fetch", "origin", "main")
        if not fetched:
            return MainCheck(
                status="blocked",
                remote_main={},
                previous_branch={},
                remediation=f"origin/main refresh failed: {fetch_error}",
                checked_at=_now(),
            )
        remote_ref = "refs/remotes/origin/main"
        remote_sha, remote_error = self._output("git", "rev-parse", remote_ref)
        local_sha, local_error = self._output("git", "rev-parse", "refs/heads/main")
        branch, branch_error = self._output("git", "branch", "--show-current")
        if not remote_sha or not local_sha or not branch:
            return MainCheck(
                status="blocked",
                remote_main={"full_ref": remote_ref, "sha": remote_sha},
                previous_branch={"full_ref": branch, "sha": "", "relation": "unknown"},
                local_main={"full_ref": "refs/heads/main", "sha": local_sha},
                remediation=(
                    "cannot resolve authoritative main or current branch: "
                    f"{remote_error or local_error or branch_error}"
                ),
                checked_at=_now(),
            )
        previous_ref = f"refs/heads/{branch}"
        previous_sha, _ = self._output("git", "rev-parse", previous_ref)
        relation = self._relation(previous_ref, remote_ref)
        remediation = (
            ""
            if relation == "merged" and local_sha == remote_sha
            else (
                f"current branch {previous_ref} is {relation} relative to {remote_ref}; "
                "local main must equal authoritative remote main"
            )
        )
        return MainCheck(
            status="pass" if not remediation else "blocked",
            remote_main={"full_ref": remote_ref, "sha": remote_sha},
            previous_branch={
                "full_ref": previous_ref,
                "sha": previous_sha,
                "relation": relation,
            },
            local_main={"full_ref": "refs/heads/main", "sha": local_sha},
            remediation=remediation,
            checked_at=_now(),
        )

    def provision(
        self,
        story: str,
        release_version: str,
        run_id: str,
        main_check: MainCheck,
    ) -> FoundationOutcome:
        """Create or reconcile branch, worktree, spec directory and GitHub Project."""
        if main_check.status != "pass":
            return FoundationOutcome("blocked", {}, main_check.remediation)
        resources: dict[str, Any] = {
            "local_project": {
                "id": f"prj_{hashlib.sha256(run_id.encode()).hexdigest()[:12]}"
            },
            "workflow_run": {"id": run_id},
        }
        branch = f"releases/{release_version.removeprefix('v')}"
        branch_result = self._ensure_branch(branch, main_check.remote_main["sha"])
        resources["release_branch"] = branch_result[0]
        if branch_result[1]:
            return self._uncertain(resources, branch_result[1])
        project, project_error = self._ensure_github_project(release_version)
        if project is not None:
            resources["github_project"] = project
        if project_error:
            return self._uncertain(resources, project_error)
        worktree, worktree_error = self._ensure_worktree(branch, release_version)
        resources["worktree"] = worktree
        if worktree_error:
            return self._uncertain(resources, worktree_error)
        resources["release_branch"].update(
            {
                "checked_out": True,
                "head_symbolic_ref": worktree["head_symbolic_ref"],
                "head_sha": worktree["head_sha"],
            }
        )
        spec, spec_error = self._ensure_spec_directory(Path(worktree["path"]))
        resources["spec_directory"] = spec
        if spec_error:
            return self._uncertain(resources, spec_error)
        resources["operations"] = [
            {"kind": key, "status": "confirmed", "actual_identity": value}
            for key, value in resources.items()
            if isinstance(value, dict) and "id" in value
        ]
        return FoundationOutcome("ready", resources, "")

    def _ensure_branch(self, branch: str, main_sha: str) -> tuple[dict[str, str], str]:
        """Query or create a release branch without overwriting an existing ref."""
        ref = f"refs/heads/{branch}"
        existing, _ = self._output("git", "rev-parse", ref)
        if existing:
            if existing != main_sha:
                return (
                    {"full_ref": ref, "start_sha": existing},
                    f"existing release branch starts at {existing}, expected {main_sha}",
                )
            return {"full_ref": ref, "start_sha": existing}, ""
        ok, error = self._run("git", "branch", branch, main_sha)
        return {"full_ref": ref, "start_sha": main_sha}, "" if ok else error

    def _ensure_worktree(self, branch: str, version: str) -> tuple[dict[str, str], str]:
        """Create an isolated controlled worktree and verify symbolic HEAD."""
        path = self._root / ".louke" / "worktrees" / version.removeprefix("v")
        if not path.exists():
            ok, error = self._run("git", "worktree", "add", str(path), branch)
            if not ok:
                return {"path": str(path)}, error
        symbolic, error = self._output_at(
            path, "git", "symbolic-ref", "--short", "HEAD"
        )
        head, head_error = self._output_at(path, "git", "rev-parse", "HEAD")
        expected = branch
        if symbolic != expected:
            return {"path": str(path), "head_symbolic_ref": symbolic}, (
                f"worktree symbolic HEAD {symbolic!r} is not {expected!r}"
            )
        return {"path": str(path), "head_symbolic_ref": symbolic, "head_sha": head}, (
            "" if head else head_error
        )

    def _ensure_spec_directory(self, worktree: Path) -> tuple[dict[str, str], str]:
        """Require the locked spec directory in the controlled release worktree."""
        relative = Path(".louke/project/specs") / self._spec_id
        target = worktree / relative
        if not target.is_dir():
            return {
                "path": relative.as_posix()
            }, "locked spec directory is absent on release branch"
        digest = _directory_digest(target)
        return {"path": relative.as_posix(), "digest": digest}, ""

    def _ensure_github_project(self, version: str) -> tuple[dict[str, str] | None, str]:
        """Query an exact release Project or create it through ``gh project``."""
        repo = self._project_repo()
        owner, name = repo.rsplit("/", 1)
        title = f"{name} {version.removeprefix('v')}"
        output, error = self._output(
            "gh", "project", "list", "--owner", owner, "--format", "json"
        )
        if error:
            return None, f"GitHub Project query failed: {error}"
        try:
            projects = json.loads(output).get("projects", [])
        except json.JSONDecodeError as exc:
            return None, f"GitHub Project query was not valid JSON: {exc}"
        for project in projects:
            if project.get("title") == title:
                return {
                    "node_id": str(project.get("id") or ""),
                    "url": str(project.get("url") or ""),
                }, ""
        created, create_error = self._output(
            "gh",
            "project",
            "create",
            "--owner",
            owner,
            "--title",
            title,
            "--format",
            "json",
        )
        if create_error:
            return None, f"GitHub Project create failed: {create_error}"
        try:
            payload = json.loads(created)
        except json.JSONDecodeError as exc:
            return None, f"GitHub Project create was not valid JSON: {exc}"
        return {
            "node_id": str(payload.get("id") or ""),
            "url": str(payload.get("url") or ""),
        }, ""

    def _project_repo(self) -> str:
        """Return the configured owner/repository identity without credentials."""
        project = _read_project_toml(self._root)
        repo = str(project.get("project", {}).get("repo") or "")
        return repo.removeprefix("github.com/")

    def _relation(self, previous_ref: str, remote_ref: str) -> str:
        """Classify two refs using explicit merge-base checks."""
        if self._run("git", "merge-base", "--is-ancestor", previous_ref, remote_ref)[0]:
            return "merged"
        if self._run("git", "merge-base", "--is-ancestor", remote_ref, previous_ref)[0]:
            return "ahead"
        return (
            "diverged"
            if self._run("git", "merge-base", previous_ref, remote_ref)[0]
            else "unknown"
        )

    def _run(self, *command: str) -> tuple[bool, str]:
        """Run one argument-vector command and return success plus redacted error."""
        result = subprocess.run(command, cwd=self._root, capture_output=True, text=True)
        return result.returncode == 0, (result.stderr or result.stdout).strip()

    def _output(self, *command: str) -> tuple[str, str]:
        """Run one command and return trimmed stdout plus stderr/stdout error."""
        result = subprocess.run(command, cwd=self._root, capture_output=True, text=True)
        return result.stdout.strip(), "" if result.returncode == 0 else (
            result.stderr or result.stdout
        ).strip()

    def _output_at(self, path: Path, *command: str) -> tuple[str, str]:
        """Run a command in a controlled worktree."""
        result = subprocess.run(command, cwd=path, capture_output=True, text=True)
        return result.stdout.strip(), "" if result.returncode == 0 else (
            result.stderr or result.stdout
        ).strip()

    def _uncertain(
        self, resources: dict[str, Any], remediation: str
    ) -> FoundationOutcome:
        """Preserve observed resource identities when a later operation fails."""
        return FoundationOutcome("uncertain", resources, remediation)


def _directory_digest(path: Path) -> str:
    """Hash every regular file under a Foundation spec directory."""
    digest = hashlib.sha256()
    for file_path in sorted(path.rglob("*")):
        if file_path.is_file():
            digest.update(file_path.relative_to(path).as_posix().encode())
            digest.update(file_path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def _read_project_toml(root: Path) -> dict[str, Any]:
    """Read project metadata using the repository's existing TOML helper."""
    from louke._common import _toml_load

    return _toml_load(root / ".louke/project/project.toml")


def _now() -> str:
    """Return an ISO-8601 UTC observation timestamp."""
    return datetime.now(timezone.utc).isoformat()
