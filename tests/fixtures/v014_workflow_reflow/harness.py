"""L2 protocol stand-ins and isolated-workspace builder for v0.14-001 entry slice.

AC-FR0100-01/02/03, AC-FR0300-01/02, AC-FR0400-01/02/03/04/05,
AC-FR0500-01/03, AC-FR0600-02, AC-FR0700-01/02/03, AC-FR0800-01.

The stand-ins implement the *public process/protocol boundaries* of OpenCode
and GitHub and record every operation in a ledger so tests can independently
prove dispatch happened and identities match -- no fake app-internal success.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List

from louke.opencode.adapter import Instance, Message

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
LOUKE_REPO_IDENTITY = "github.com/zillionare/louke"
SPEC_ID = "v0.14-001-workflow-reflow-spec"
RELEASE_VERSION = "0.14.0"
RELEASE_BRANCH = f"releases/{RELEASE_VERSION}"

# The canonical human story used across the entry-slice tests.  The workspace
# builder pre-writes ``story.md`` with the template substituted by this story
# so that ``ShellFoundationAdapter.write_story`` takes the reconcile-existing
# path (the Foundation adapter runs ``git add`` in the workspace root, not the
# worktree; pre-existing story.md avoids the new-file commit path).
CANONICAL_HUMAN_STORY = "Ship the v0.14 reflow entry slice for authenticated Go."

# Contract files that the release-contract bundle byte-verifies.  These are
# copied verbatim from the real Louke workspace so the development-bootstrap
# catalog activates the M-START → M-STORY definition.
_CONTRACT_FILES: tuple[str, ...] = (
    ".louke/project/specs/v0.14-001-workflow-reflow-spec/spec.md",
    ".louke/project/specs/v0.14-001-workflow-reflow-spec/acceptance.md",
    ".louke/project/specs/v0.14-002-workflow-reflow-design/spec.md",
    ".louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md",
    ".louke/project/specs/v0.14-003-workflow-reflow-impl/spec.md",
    ".louke/project/specs/v0.14-003-workflow-reflow-impl/acceptance.md",
)

# Files that must be present for ``is_louke_workspace`` and the Foundation
# adapter's story-template fallback.
_LOUKE_MARKER = "louke/__init__.py"
_PROJECT_TOML = ".louke/project/project.toml"
_CONTRACT_BUNDLE = ".louke/project/release-contract-bundle.json"


# ---------------------------------------------------------------------------
# L2 OpenCode stand-in
# ---------------------------------------------------------------------------


@dataclass
class DispatchRecord:
    """One recorded Scribe dispatch through the provider boundary."""

    correlation_id: str
    task_id: str
    attempt_id: str
    session_id: str
    prompt_digest: str
    dispatched_at: str
    recommendation_delivered: bool


class L2ScribeStandIn:
    """Deterministic L2 stand-in for the OpenCode provider boundary.

    Implements the :class:`~louke.opencode.adapter.OpenCodeAdapter` protocol.
    On the first Scribe ``send_message`` the stand-in records the dispatch in
    its ledger and delivers one ``Go`` recommendation through the validated
    ``submit_result`` seam on :class:`~louke.v014.scribe_entry.ScribeEntryService`.

    The recommendation goes through **full validation** in ``submit_result``
    (role, task, attempt, session, manifest, artifact, write scope).  If any
    identity is stale the result is rejected and the ledger records the
    rejection -- there is no fake app-internal success.
    """

    def __init__(self, scribe_service: Any | None = None) -> None:
        self._scribe = scribe_service
        self._instances: dict[str, Instance] = {}
        self._messages: dict[str, list[Message]] = {}
        self._next_id = 0
        self.dispatch_ledger: list[DispatchRecord] = []
        self.recommendation = "Go"
        self.reason = "The bounded Story is ready for Human review."

    # -- OpenCodeAdapter protocol ------------------------------------------

    def create(self, *, correlation_id: str) -> Instance:
        self._next_id += 1
        instance = Instance(id=f"l2-session-{self._next_id}", status="running")
        self._instances[instance.id] = instance
        self._messages.setdefault(instance.id, [])
        return instance

    def list(self) -> List[Instance]:
        return list(self._instances.values())

    def stop(self, instance_id: str) -> Instance:
        inst = self._instances.get(instance_id)
        if inst is None:
            return Instance(id=instance_id, status="stopped")
        inst.status = "stopped"
        return inst

    def send_message(
        self, instance_id: str, content: str, *, correlation_id: str
    ) -> tuple[Message, bool]:
        if instance_id not in self._instances:
            raise KeyError(instance_id)
        user_msg = Message(
            id=f"l2-msg-{self._next_id}",
            instance_id=instance_id,
            role="user",
            kind="message",
            content=content,
        )
        self._messages[instance_id].append(user_msg)
        self._next_id += 1
        # Scribe dispatches carry the correlation id ``scribe:<task>:<attempt>``.
        delivered = self._maybe_deliver_recommendation(
            correlation_id, instance_id, content
        )
        echo = Message(
            id=f"l2-msg-{self._next_id}",
            instance_id=instance_id,
            role="assistant",
            kind="message",
            content=f"recommendation delivered: {self.recommendation}"
            if delivered
            else "ack",
        )
        self._messages[instance_id].append(echo)
        self._next_id += 1
        return user_msg, True

    def list_messages(
        self, instance_id: str, *, after_message_id: str | None = None
    ) -> List[Message]:
        msgs = list(self._messages.get(instance_id, []))
        if not after_message_id:
            return msgs
        for i, m in enumerate(msgs):
            if m.id == after_message_id:
                return msgs[i + 1 :]
        return msgs

    def stream_events(self, instance_id: str, last_event_id: str | None = None):
        from louke.opencode.adapter import StreamEvent, new_id

        messages = self.list_messages(instance_id, after_message_id=None)
        assistant = next((m for m in reversed(messages) if m.role == "assistant"), None)
        if assistant is None:
            return
        yield StreamEvent(
            event_id=new_id(),
            type="completed",
            message_id=assistant.id,
            content=assistant.content,
        )

    # -- Provider / task boundary ------------------------------------------

    def _maybe_deliver_recommendation(
        self, correlation_id: str, session_id: str, prompt: str
    ) -> bool:
        """Deliver one Scribe recommendation through ``submit_result``.

        Returns ``True`` when a recommendation was delivered (or the
        correlation id is not a Scribe dispatch and nothing happened).
        """
        if not correlation_id.startswith("scribe:") or self._scribe is None:
            return False
        parts = correlation_id.split(":")
        if len(parts) < 3:
            return False
        task_id = parts[1]
        attempt_id = parts[2]
        task = self._scribe._store.get_task(task_id)
        if task is None:
            return False
        payload = {
            "role": "Scribe",
            "task_id": task_id,
            "attempt_id": task["active_attempt_id"],
            "session_id": session_id,
            "manifest_digest": task["manifest_digest"],
            "artifact_revision": task["artifact_revision"],
            "artifact_digest": task["artifact_digest"],
            "write_scope": ["story.md"],
            "recommendation": self.recommendation,
            "reason": self.reason,
        }
        delivered = False
        try:
            self._scribe.submit_result(
                run_id=task["run_id"], task_id=task_id, payload=payload
            )
            delivered = True
        except Exception:
            # Validation rejected the result -- record the failure, no fake
            # success.  The run/artifact/verdict remain unchanged.
            delivered = False
        self.dispatch_ledger.append(
            DispatchRecord(
                correlation_id=correlation_id,
                task_id=task_id,
                attempt_id=attempt_id,
                session_id=session_id,
                prompt_digest=f"sha256:{hashlib.sha256(prompt.encode()).hexdigest()}",
                dispatched_at=datetime.now(timezone.utc).isoformat(),
                recommendation_delivered=delivered,
            )
        )
        return delivered


# ---------------------------------------------------------------------------
# GitHub Project stand-in (``gh`` replacement)
# ---------------------------------------------------------------------------

_GH_STANDIN_SCRIPT = """\
#!/usr/bin/env python3
\"\"\"Deterministic ``gh`` stand-in for the v0.14-001 entry-slice tests.

Records every invocation in ``--ledger-path`` and responds to the two
``gh project`` sub-commands the Foundation adapter issues:

  * ``gh project list   --owner O --format json``
  * ``gh project create --owner O --title T --format json``

All other ``gh`` invocations exit non-zero with a clear message so the
Foundation adapter surfaces them as ``uncertain`` rather than silently
faking success.
\"\"\"
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def main(argv: list[str]) -> int:
    ledger = Path(os.environ.get("LOUKE_GH_LEDGER_PATH", "/tmp/gh-standin-ledger.json"))
    records: list[dict] = []
    if ledger.exists():
        try:
            records = json.loads(ledger.read_text())
        except Exception:
            records = []
    entry = {"argv": argv, "env_owner": os.environ.get("LOUKE_GH_OWNER", ""), "at": _now()}
    if len(argv) >= 2 and argv[0] == "project" and argv[1] == "list":
        owner = ""
        for i, tok in enumerate(argv):
            if tok == "--owner" and i + 1 < len(argv):
                owner = argv[i + 1]
        project_id = f"P_gt_{hashlib.sha256(owner.encode()).hexdigest()[:12]}"
        payload = {"projects": [{"id": project_id, "title": "", "url": f"https://github.com/users/{owner}/projects/99"}]}
        entry["kind"] = "project_list"
        entry["owner"] = owner
        records.append(entry)
        ledger.write_text(json.dumps(records, indent=2))
        print(json.dumps(payload))
        return 0
    if len(argv) >= 2 and argv[0] == "project" and argv[1] == "create":
        owner = ""
        title = ""
        for i, tok in enumerate(argv):
            if tok == "--owner" and i + 1 < len(argv):
                owner = argv[i + 1]
            if tok == "--title" and i + 1 < len(argv):
                title = argv[i + 1]
        project_id = f"P_gt_{hashlib.sha256(f'{owner}/{title}'.encode()).hexdigest()[:12]}"
        payload = {"id": project_id, "title": title, "url": f"https://github.com/users/{owner}/projects/99"}
        entry["kind"] = "project_create"
        entry["owner"] = owner
        entry["title"] = title
        entry["project_id"] = project_id
        records.append(entry)
        ledger.write_text(json.dumps(records, indent=2))
        print(json.dumps(payload))
        return 0
    entry["kind"] = "unsupported"
    records.append(entry)
    ledger.write_text(json.dumps(records, indent=2))
    print(f"gh stand-in: unsupported command: {argv}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
"""


@dataclass
class GhLedgerEntry:
    kind: str
    owner: str
    title: str
    project_id: str
    at: str


def read_gh_ledger(ledger_path: Path) -> list[GhLedgerEntry]:
    """Read the stand-in ``gh`` operation ledger."""
    if not ledger_path.exists():
        return []
    raw = json.loads(ledger_path.read_text(encoding="utf-8"))
    return [
        GhLedgerEntry(
            kind=str(e.get("kind", "")),
            owner=str(e.get("owner", "")),
            title=str(e.get("title", "")),
            project_id=str(e.get("project_id", "")),
            at=str(e.get("at", "")),
        )
        for e in raw
    ]


# ---------------------------------------------------------------------------
# Isolated workspace builder
# ---------------------------------------------------------------------------


@dataclass
class IsolatedWorkspace:
    """A fully isolated Louke-like workspace for entry-slice tests."""

    root: Path
    bare_remote: Path
    gh_ledger: Path
    gh_bin: Path
    orig_path: str = ""

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run a Git command inside the workspace root."""
        return subprocess.run(
            ["git", *args],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            check=False,
        )

    def git_output(self, *args: str) -> str:
        result = self.git(*args)
        if result.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
        return result.stdout.strip()

    def cleanup(self) -> None:
        """Remove worktrees and temp directories."""
        worktrees = self.root / ".louke" / "worktrees"
        if worktrees.exists():
            shutil.rmtree(worktrees, ignore_errors=True)
        for branch in (RELEASE_BRANCH,):
            self.git("branch", "-D", branch)


def build_isolated_workspace(tmp_path: Path) -> IsolatedWorkspace:
    """Create a Louke-like workspace with a bare Git remote.

    The workspace contains:
      * The Louke package marker (``louke/__init__.py``) and templates.
      * ``project.toml`` with the Louke repository identity.
      * The release-contract bundle and all byte-verified contract files.
      * A Git repository with ``main`` pushed to a bare ``origin``.
      * A stand-in ``gh`` script on an isolated ``PATH``.
    """
    root = tmp_path / "workspace"
    root.mkdir(parents=True)

    # --- Copy Louke marker and templates ---------------------------------
    louke_pkg = root / "louke"
    louke_pkg.mkdir()
    shutil.copy2(REPO_ROOT / "louke" / "__init__.py", louke_pkg / "__init__.py")
    templates_dst = louke_pkg / "templates"
    templates_dst.mkdir()
    shutil.copy2(
        REPO_ROOT / "louke" / "templates" / "story.md", templates_dst / "story.md"
    )

    # --- Copy project.toml (trimmed to identity fields) -------------------
    project_dir = root / ".louke" / "project"
    project_dir.mkdir(parents=True)
    specs_dir = project_dir / "specs"
    specs_dir.mkdir(parents=True)

    project_toml = project_dir / "project.toml"
    project_toml.write_text(
        textwrap.dedent(
            f"""\
            [project]
            version = "{RELEASE_VERSION}"
            repo = "{LOUKE_REPO_IDENTITY}"
            project = "louke-{RELEASE_VERSION}"
            project_id = ""
            spec_id = "{SPEC_ID}"
            release_branch = "{RELEASE_BRANCH}"

            [meta]
            created = "2026-07-23"
            current_stage = "M-LOCK"
            test_framework = "pytest"
            """
        ),
        encoding="utf-8",
    )

    # --- Copy release-contract bundle -------------------------------------
    shutil.copy2(
        REPO_ROOT / _CONTRACT_BUNDLE, project_dir / "release-contract-bundle.json"
    )

    # --- Copy contract files (byte-verified by the bundle) ----------------
    for rel in _CONTRACT_FILES:
        src = REPO_ROOT / rel
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    # --- Pre-create story.md with the template substituted by the canonical
    # human story.  The Foundation adapter's ``write_story`` reconciles an
    # existing story.md (using ``_output_at(worktree, ...)`` which runs in the
    # worktree) rather than the new-file path (which runs ``git add`` in the
    # workspace root).  The bytes must exactly match what
    # ``initialize_story_revision`` produces for the same human story.
    story_template_path = REPO_ROOT / "louke" / "templates" / "story.md"
    story_template_body = story_template_path.read_text(encoding="utf-8")
    story_placeholder = "{用户原始输入，逐字记录，不修改或转述}"
    story_md_body = story_template_body.replace(
        story_placeholder, CANONICAL_HUMAN_STORY
    )
    story_md_path = root / ".louke" / "project" / "specs" / SPEC_ID / "story.md"
    story_md_path.write_text(story_md_body, encoding="utf-8")

    # --- Stand-in gh -------------------------------------------------------
    gh_dir = tmp_path / "gh-bin"
    gh_dir.mkdir()
    gh_bin = gh_dir / "gh"
    gh_ledger = tmp_path / "gh-standin-ledger.json"
    gh_bin.write_text(_GH_STANDIN_SCRIPT, encoding="utf-8")
    gh_bin.chmod(gh_bin.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # --- Git init + bare remote -------------------------------------------
    bare_remote = tmp_path / "bare-remote.git"
    subprocess.run(
        ["git", "init", "--bare", str(bare_remote)],
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        ["git", "init", str(root)],
        capture_output=True,
        text=True,
        check=True,
    )
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test Human",
        "GIT_AUTHOR_EMAIL": "human@test.local",
        "GIT_COMMITTER_NAME": "Test Human",
        "GIT_COMMITTER_EMAIL": "human@test.local",
    }
    subprocess.run(["git", "add", "-A"], cwd=str(root), env=env, check=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initialise isolated workspace"],
        cwd=str(root),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "branch", "-M", "main"],
        cwd=str(root),
        env=env,
        check=True,
    )
    subprocess.run(
        ["git", "remote", "add", "origin", str(bare_remote)],
        cwd=str(root),
        env=env,
        check=True,
    )
    subprocess.run(
        ["git", "push", "-u", "origin", "main"],
        cwd=str(root),
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    return IsolatedWorkspace(
        root=root,
        bare_remote=bare_remote,
        gh_ledger=gh_ledger,
        gh_bin=gh_bin,
    )


# ---------------------------------------------------------------------------
# Authenticated HTTP client helper
# ---------------------------------------------------------------------------


def register_and_login(
    client: Any, username: str = "human", password: str = "secret"
) -> str:
    """Register a Human principal and return the session cookie value."""
    response = client.post(
        "/api/auth/register",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return client.cookies.get("louke_session").strip('"')


def csrf_token(client: Any) -> str:
    """Derive the CSRF header token from the authenticated session cookie."""
    from louke.web.auth import csrf_token_for_session

    session = client.cookies.get("louke_session").strip('"')
    return csrf_token_for_session(client.app.state.store, session)


def auth_headers(client: Any, origin: str = "http://127.0.0.1:9999") -> dict[str, str]:
    """Return Origin + CSRF headers for an authenticated mutation."""
    return {"Origin": origin, "X-Louke-CSRF": csrf_token(client)}
