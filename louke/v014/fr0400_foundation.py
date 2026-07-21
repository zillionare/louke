"""FR-0400: 新 Release 的 ``main`` 前置检查与 Foundation.

Implements the deterministic contract slice of FR-0400:

* :func:`evaluate_main_preflight` decides whether a release request may
  proceed to Foundation. The decision is PASS only when the declared remote
  refresh succeeds, the previous branch's relation to authoritative
  ``refs/remotes/<remote>/main`` is ``merged`` and the local ``main`` SHA
  equals the remote main SHA. Any other combination (refresh error, relation
  ``ahead``/``behind``/``diverged``/``unknown``, local-main mismatch) is
  ``blocked`` with non-empty remediation and ``can_create_foundation_resources
  == False``.
* :class:`FoundationReconciler` manages the per-release Foundation operation
  ledger. Each required resource kind has exactly one
  :class:`FoundationOperation` with a stable ``operation_id``. Operations move
  ``pending -> confirmed`` on success, or ``conflict`` when an existing
  resource's identity conflicts with Foundation evidence. Foundation is
  ``complete`` only when every required operation is confirmed AND the release
  branch start SHA byte-equals the authoritative remote main SHA.

The reconciler never creates external resources; it only records the
deterministic state transitions that the Driver/Git/GitHub adapters report.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional


class GitRefRelation(str, Enum):
    """Relationship of the previous development branch to authoritative main.

    Members:
        MERGED: previous branch's commits are all reachable from remote main.
        AHEAD: previous branch has commits not on remote main.
        BEHIND: previous branch is missing commits that are on remote main.
        DIVERGED: previous branch has both unique and missing commits.
        UNKNOWN: relation cannot be determined (e.g. fetch error).
    """

    MERGED = "merged"
    AHEAD = "ahead"
    BEHIND = "behind"
    DIVERGED = "diverged"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class RemoteMain:
    """Authoritative remote main identity.

    Attributes:
        full_ref: Full ref string, e.g. ``refs/remotes/origin/main``.
        sha: 40-char SHA-1 hex of the remote main commit.
    """

    full_ref: str
    sha: str


@dataclass(frozen=True)
class MainPreflightResult:
    """Decision returned by :func:`evaluate_main_preflight`.

    Attributes:
        status: ``pass`` when Foundation resources may be created;
            ``blocked`` otherwise.
        remote_main_sha: The authoritative remote main SHA when refresh
            succeeded; ``None`` otherwise.
        remediation: Non-empty human-readable remediation when ``blocked``;
            empty when ``pass``.
        can_create_foundation_resources: ``True`` only when ``status == 'pass'``.
    """

    status: str
    remote_main_sha: Optional[str]
    remediation: str
    can_create_foundation_resources: bool


def evaluate_main_preflight(
    *,
    declared_remote_refresh_error: Optional[str],
    remote_main: Optional[RemoteMain],
    previous_branch_relation: Optional[GitRefRelation],
    previous_branch_full_ref: Optional[str] = None,
    previous_branch_sha: Optional[str] = None,
    local_main_sha: Optional[str] = None,
) -> MainPreflightResult:
    """Decide whether Foundation may create release-level resources.

    Args:
        declared_remote_refresh_error: Non-empty error message when the
            declared remote refresh failed; ``None`` on success.
        remote_main: The authoritative remote main identity when refresh
            succeeded; ``None`` otherwise.
        previous_branch_relation: Relationship of the previous development
            branch to ``remote_main``. ``None`` only when refresh failed.
        previous_branch_full_ref: Full ref of the previous development branch
            (e.g. ``refs/heads/releases/0.13.1``). Included in remediation.
        previous_branch_sha: SHA of the previous development branch tip.
        local_main_sha: SHA of the local ``main`` HEAD when refresh succeeded.

    Returns:
        A :class:`MainPreflightResult`. PASS requires ``declared_remote_refresh_error
        is None`` AND ``previous_branch_relation == GitRefRelation.MERGED`` AND
        ``local_main_sha == remote_main.sha``. Any other combination is
        ``blocked`` with non-empty remediation and
        ``can_create_foundation_resources == False``.

    Side effects:
        None.
    """
    if declared_remote_refresh_error is not None:
        return MainPreflightResult(
            status="blocked",
            remote_main_sha=None,
            remediation=(
                f"declared remote refresh failed: {declared_remote_refresh_error}; "
                "retry `git fetch` and verify remote access before re-running preview"
            ),
            can_create_foundation_resources=False,
        )
    if remote_main is None:
        return MainPreflightResult(
            status="blocked",
            remote_main_sha=None,
            remediation="declared remote refresh returned no main identity",
            can_create_foundation_resources=False,
        )
    if (
        previous_branch_relation is None
        or previous_branch_relation != GitRefRelation.MERGED
    ):
        relation_value = (
            previous_branch_relation.value
            if previous_branch_relation is not None
            else "unknown"
        )
        ref_part = f" {previous_branch_full_ref}" if previous_branch_full_ref else ""
        sha_part = f" (SHA {previous_branch_sha})" if previous_branch_sha else ""
        return MainPreflightResult(
            status="blocked",
            remote_main_sha=remote_main.sha,
            remediation=(
                f"previous development branch{ref_part}{sha_part} is "
                f"{relation_value} relative to {remote_main.full_ref} "
                f"(SHA {remote_main.sha}); merge or rebase the previous "
                "branch into main before re-running preview"
            ),
            can_create_foundation_resources=False,
        )
    if local_main_sha != remote_main.sha:
        return MainPreflightResult(
            status="blocked",
            remote_main_sha=remote_main.sha,
            remediation=(
                f"local main SHA {local_main_sha} does not equal authoritative "
                f"remote main SHA {remote_main.sha} on {remote_main.full_ref}; "
                "pull or reset local main before re-running preview"
            ),
            can_create_foundation_resources=False,
        )
    return MainPreflightResult(
        status="pass",
        remote_main_sha=remote_main.sha,
        remediation="",
        can_create_foundation_resources=True,
    )


class FoundationOperationKind(str, Enum):
    """Kinds of Foundation resources that must be created exactly once.

    Members:
        LOCAL_PROJECT: Per-release local Project record.
        WORKFLOW_RUN: WorkflowRun bound to the release Project.
        GITHUB_PROJECT: Release GitHub Project (node ID + URL).
        RELEASE_BRANCH: ``refs/heads/releases/<canonical version>`` checked
            out on the controlled worktree.
        SPEC_DIRECTORY: ``.louke/project/specs/<spec-id>/`` directory.
    """

    LOCAL_PROJECT = "local_project"
    WORKFLOW_RUN = "workflow_run"
    GITHUB_PROJECT = "github_project"
    RELEASE_BRANCH = "release_branch"
    SPEC_DIRECTORY = "spec_directory"


_REQUIRED_KINDS: tuple[FoundationOperationKind, ...] = tuple(FoundationOperationKind)


@dataclass(frozen=True)
class FoundationOperation:
    """A single Foundation resource operation.

    Attributes:
        operation_id: Stable opaque identifier derived from the release
            identity and the resource kind; reused on retry/reconcile.
        kind: The :class:`FoundationOperationKind` this operation creates.
        status: ``pending`` (default), ``confirmed`` (resource exists with
            matching identity), or ``conflict`` (existing identity does not
            match Foundation evidence).
        actual_identity: Non-secret identity reported by the adapter
            (e.g. ``node_id:abc``) when the resource has been observed.
    """

    operation_id: str
    kind: FoundationOperationKind
    status: str = "pending"
    actual_identity: Optional[str] = None


@dataclass(frozen=True)
class FoundationManifest:
    """Per-release Foundation ledger.

    Attributes:
        workspace_id: Workspace the Foundation belongs to.
        release_version: Canonical release version (e.g. ``0.14.0``).
        remote_main_sha: Authoritative remote main SHA used as the
            release-branch starting point.
        operations: One :class:`FoundationOperation` per required kind.
        release_branch_start_sha: SHA the release branch starts at, when
            recorded; ``None`` until :meth:`record_release_branch_start` is
            called.
    """

    workspace_id: str
    release_version: str
    remote_main_sha: str
    operations: tuple[FoundationOperation, ...] = ()
    release_branch_start_sha: Optional[str] = None

    def operation_for(
        self, kind: FoundationOperationKind
    ) -> Optional[FoundationOperation]:
        """Return the operation registered for ``kind`` or ``None``."""
        for op in self.operations:
            if op.kind == kind:
                return op
        return None

    @property
    def is_complete(self) -> bool:
        """Return ``True`` only when every required kind is confirmed and the
        release branch start SHA equals the remote main SHA."""
        if self.release_branch_start_sha != self.remote_main_sha:
            return False
        if len(self.operations) != len(_REQUIRED_KINDS):
            return False
        for kind in _REQUIRED_KINDS:
            op = self.operation_for(kind)
            if op is None or op.status != "confirmed":
                return False
        return True


def _operation_id(
    workspace_id: str, release_version: str, kind: FoundationOperationKind
) -> str:
    """Return the stable operation id for ``(workspace, version, kind)``."""
    payload = f"{workspace_id}|{release_version}|{kind.value}"
    return f"fop_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


class FoundationReconciler:
    """Stateless helper that mutates :class:`FoundationManifest` instances.

    The reconciler never performs external IO; it only records the
    deterministic state transitions reported by adapters. External adapters
    must perform query-before-create themselves and report the actual identity
    via :meth:`confirm` or :meth:`reconcile_existing`.
    """

    def begin(
        self,
        *,
        workspace_id: str,
        release_version: str,
        remote_main: RemoteMain,
    ) -> FoundationManifest:
        """Return a fresh :class:`FoundationManifest` with one pending
        operation per required kind.

        Args:
            workspace_id: Workspace identifier.
            release_version: Canonical release version.
            remote_main: Authoritative remote main identity (the release
                branch must start from ``remote_main.sha``).

        Returns:
            A new manifest with one ``pending`` operation per
            :class:`FoundationOperationKind` and ``release_branch_start_sha=None``.
        """
        operations = tuple(
            FoundationOperation(
                operation_id=_operation_id(workspace_id, release_version, kind),
                kind=kind,
            )
            for kind in _REQUIRED_KINDS
        )
        return FoundationManifest(
            workspace_id=workspace_id,
            release_version=release_version,
            remote_main_sha=remote_main.sha,
            operations=operations,
        )

    def confirm(
        self,
        manifest: FoundationManifest,
        operation_id: str,
        *,
        actual_identity: str,
    ) -> FoundationManifest:
        """Mark the operation ``confirmed`` with ``actual_identity``.

        Args:
            manifest: The current manifest.
            operation_id: The operation to confirm.
            actual_identity: Non-secret identity reported by the adapter.

        Returns:
            A new manifest with the operation confirmed.

        Raises:
            KeyError: If ``operation_id`` does not exist in ``manifest``.
        """
        return self._replace_operation(
            manifest,
            operation_id,
            status="confirmed",
            actual_identity=actual_identity,
        )

    def reconcile_existing(
        self,
        manifest: FoundationManifest,
        operation_id: str,
        *,
        existing_identity: str,
    ) -> FoundationManifest:
        """Reconcile an existing external resource for the operation.

        If the operation is still ``pending`` the existing identity is
        accepted and the operation becomes ``confirmed`` (idempotent reuse,
        FR-0400 AC-03). If the operation was already confirmed with a
        different identity, the operation becomes ``conflict`` and the
        original identity is preserved (FR-0400 AC-05).

        Args:
            manifest: The current manifest.
            operation_id: The operation being reconciled.
            existing_identity: Non-secret identity observed externally.

        Returns:
            A new manifest with the operation either confirmed or conflict.

        Raises:
            KeyError: If ``operation_id`` does not exist in ``manifest``.
        """
        existing_op = self._find(manifest, operation_id)
        if (
            existing_op.status == "confirmed"
            and existing_op.actual_identity != existing_identity
        ):
            return self._replace_operation(
                manifest,
                operation_id,
                status="conflict",
                actual_identity=existing_op.actual_identity,
            )
        return self._replace_operation(
            manifest,
            operation_id,
            status="confirmed",
            actual_identity=existing_identity,
        )

    def record_release_branch_start(
        self,
        manifest: FoundationManifest,
        operation_id: str,
        *,
        start_sha: str,
    ) -> FoundationManifest:
        """Record the release branch's start SHA.

        When ``start_sha`` does not equal ``manifest.remote_main_sha``, the
        release-branch operation becomes ``conflict`` (FR-0400 AC-05) and no
        candidate branch is created.

        Args:
            manifest: The current manifest.
            operation_id: The RELEASE_BRANCH operation id.
            start_sha: The SHA the existing release branch starts at.

        Returns:
            A new manifest with ``release_branch_start_sha`` set and the
            operation status updated accordingly.

        Raises:
            KeyError: If ``operation_id`` does not exist or is not the
                RELEASE_BRANCH operation.
        """
        op = self._find(manifest, operation_id)
        if op.kind != FoundationOperationKind.RELEASE_BRANCH:
            raise KeyError(
                f"operation {operation_id!r} is not the RELEASE_BRANCH operation"
            )
        if start_sha != manifest.remote_main_sha:
            new_op = replace(
                op,
                status="conflict",
                actual_identity=op.actual_identity,
            )
        else:
            new_op = replace(op, status="confirmed", actual_identity=op.actual_identity)
        return replace(
            manifest,
            operations=tuple(
                new_op if op.operation_id == operation_id else op
                for op in manifest.operations
            ),
            release_branch_start_sha=start_sha,
        )

    def _find(
        self, manifest: FoundationManifest, operation_id: str
    ) -> FoundationOperation:
        for op in manifest.operations:
            if op.operation_id == operation_id:
                return op
        raise KeyError(f"operation {operation_id!r} not found in manifest")

    def _replace_operation(
        self,
        manifest: FoundationManifest,
        operation_id: str,
        *,
        status: str,
        actual_identity: Optional[str],
    ) -> FoundationManifest:
        existing = self._find(manifest, operation_id)
        new_op = replace(
            existing,
            status=status,
            actual_identity=actual_identity
            if actual_identity is not None
            else existing.actual_identity,
        )
        return replace(
            manifest,
            operations=tuple(
                new_op if op.operation_id == operation_id else op
                for op in manifest.operations
            ),
        )
