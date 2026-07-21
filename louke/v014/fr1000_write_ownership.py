"""FR-1000: 文档 Write Ownership、CAS 与脏编辑保护.

Implements the deterministic contract slice of FR-1000:

* :class:`WriteLeaseRegistry` is the authority for per-document write
  leases and dirty flags. At most one active lease may exist per document;
  a second acquirer receives a :class:`WriteLease` with
  ``status == BLOCKED`` and the current holder exposed (AC-FR1000-01).

* :func:`register_dirty` records the Human browser's unsaved-edit state.
  When dirty is registered for a document, :func:`acquire_write_lease`
  rejects Agent acquirers with :class:`DirtyBlocksHandoff`
  (``HUMAN_DIRTY_BLOCKS_HANDOFF``); the page must prompt save/discard
  (AC-FR1000-02).

* :func:`apply_concurrent_save` is the CAS save path. Two saves with the
  same ``expected_revision``/``version_token`` race via a barrier; exactly
  one wins (commits its bytes and bumps the revision), the other receives
  :class:`SaveConflict` with code ``DOCUMENT_WRITE_CONFLICT`` and the
  current revision/token. The loser never silently overwrites the winner
  (AC-FR1000-01).

* :func:`decide_non_holder_patch_handling` decides what to do when a
  non-holder has modified a controlled document. Only when the baseline
  bytes are available AND the patch is exactly isolatable AND the source is
  identifiable does Runtime remove just the violating patch and notify the
  Agent to re-read. Otherwise the run is ``needs_attention`` and no
  repository-wide revert is performed (AC-FR1000-03).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Optional


DOCUMENT_WRITE_CONFLICT = "DOCUMENT_WRITE_CONFLICT"
HUMAN_DIRTY_BLOCKS_HANDOFF = "HUMAN_DIRTY_BLOCKS_HANDOFF"


class LeaseStatus(str, Enum):
    """Status of a write lease acquisition request.

    Members:
        ACTIVE: The lease was granted to the caller.
        BLOCKED: The lease was not granted; another holder or a Human dirty
            flag blocks acquisition.
    """

    ACTIVE = "active"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class LeaseHolder:
    """Identity of a lease holder.

    Attributes:
        kind: ``human`` or ``agent``; never inferred from payload.
        id: Non-secret actor identity (e.g. ``human:alice``).
        role: ``author`` or ``reviewer``.
    """

    kind: str
    id: str
    role: str


@dataclass(frozen=True)
class WriteLease:
    """A write lease granted for a single document.

    Attributes:
        lease_id: Opaque stable lease identifier.
        holder: :class:`LeaseHolder` the lease was granted to.
        document: Document path the lease is scoped to (e.g. ``story.md``).
        base_revision: Artifact revision the lease is based on.
        version_token: Opaque version token the lease is bound to.
        status: ``ACTIVE`` when granted; ``BLOCKED`` when another holder or
            a Human dirty flag blocks acquisition.
        current_holder: When ``status == BLOCKED``, the holder that currently
            owns the lease; ``None`` otherwise.
        task_id: When the holder is an Agent, the task id the lease is
            scoped to; ``None`` for Human holders.
    """

    lease_id: str
    holder: LeaseHolder
    document: str
    base_revision: int
    version_token: str
    status: LeaseStatus
    current_holder: Optional[LeaseHolder] = None
    task_id: Optional[str] = None


@dataclass
class WriteLeaseRegistry:
    """In-memory registry of per-document write leases and dirty flags.

    The registry is thread-safe; concurrent acquires and saves serialise on
    an internal lock. At most one active lease may exist per document.
    """

    _leases: dict[str, WriteLease] = None  # type: ignore[assignment]
    _dirty: dict[str, bool] = None  # type: ignore[assignment]
    _lock: threading.RLock = None  # type: ignore[assignment]
    _next_lease_id: int = 1

    def __post_init__(self) -> None:
        if self._leases is None:
            self._leases = {}
        if self._dirty is None:
            self._dirty = {}
        if self._lock is None:
            self._lock = threading.RLock()

    def active_lease_for(self, document: str) -> Optional[WriteLease]:
        """Return the active lease for ``document`` or ``None``."""
        with self._lock:
            lease = self._leases.get(document)
            if lease is None or lease.status != LeaseStatus.ACTIVE:
                return None
            return lease

    def grant(self, lease: WriteLease) -> None:
        """Record a pre-built active lease (test helper)."""
        with self._lock:
            self._leases[lease.document] = lease

    def acquire(
        self,
        *,
        holder: LeaseHolder,
        document: str,
        base_revision: int,
        version_token: str,
        task_id: Optional[str],
    ) -> WriteLease:
        """Try to acquire a lease for ``document``.

        Args:
            holder: The :class:`LeaseHolder` requesting the lease.
            document: Document path the lease is scoped to.
            base_revision: Artifact revision the lease is based on.
            version_token: Opaque version token the lease is bound to.
            task_id: Task id when the holder is an Agent; ``None`` for
                Human holders.

        Returns:
            A :class:`WriteLease`. ``status == ACTIVE`` when granted;
            ``status == BLOCKED`` when an existing lease or a Human dirty
            flag blocks acquisition.

        Raises:
            DirtyBlocksHandoff: When the holder is an Agent and a Human dirty
                flag is registered for ``document``.
        """
        with self._lock:
            existing = self._leases.get(document)
            if existing is not None and existing.status == LeaseStatus.ACTIVE:
                return WriteLease(
                    lease_id="",
                    holder=holder,
                    document=document,
                    base_revision=base_revision,
                    version_token=version_token,
                    status=LeaseStatus.BLOCKED,
                    current_holder=existing.holder,
                    task_id=task_id,
                )
            if holder.kind == "agent" and self._dirty.get(document, False):
                raise DirtyBlocksHandoff(
                    code=HUMAN_DIRTY_BLOCKS_HANDOFF,
                    remediation=(
                        "Human browser has unsaved edits; prompt save or "
                        "discard before granting the Agent a write lease"
                    ),
                )
            lease_id = f"lease_{self._next_lease_id}"
            self._next_lease_id += 1
            lease = WriteLease(
                lease_id=lease_id,
                holder=holder,
                document=document,
                base_revision=base_revision,
                version_token=version_token,
                status=LeaseStatus.ACTIVE,
                task_id=task_id,
            )
            self._leases[document] = lease
            return lease

    def release(self, lease_id: str) -> None:
        """Release the lease with ``lease_id``; idempotent."""
        with self._lock:
            for document, lease in list(self._leases.items()):
                if lease.lease_id == lease_id and lease.status == LeaseStatus.ACTIVE:
                    self._leases.pop(document, None)
                    return

    def set_dirty(self, document: str, dirty: bool) -> None:
        """Register or clear the Human dirty flag for ``document``."""
        with self._lock:
            if dirty:
                self._dirty[document] = True
            else:
                self._dirty.pop(document, None)


def acquire_write_lease(
    *,
    registry: WriteLeaseRegistry,
    holder: LeaseHolder,
    document: str,
    base_revision: int,
    version_token: str,
    task_id: Optional[str],
) -> WriteLease:
    """Acquire a write lease from ``registry``. See
    :meth:`WriteLeaseRegistry.acquire`."""
    return registry.acquire(
        holder=holder,
        document=document,
        base_revision=base_revision,
        version_token=version_token,
        task_id=task_id,
    )


def release_write_lease(*, registry: WriteLeaseRegistry, lease_id: str) -> None:
    """Release a write lease. See :meth:`WriteLeaseRegistry.release`."""
    registry.release(lease_id)


def register_dirty(
    *,
    registry: WriteLeaseRegistry,
    document: str,
    client_id: str,
    expected_artifact_revision: int,
    dirty: bool,
) -> None:
    """Register or clear the Human dirty flag for ``document``.

    Args:
        registry: The :class:`WriteLeaseRegistry` to update.
        document: Document path the dirty flag is for.
        client_id: Browser client id registering the flag.
        expected_artifact_revision: Artifact revision the dirty flag was
            observed at.
        dirty: ``True`` to register dirty; ``False`` to clear.

    Side effects:
        Mutates ``registry``: the dirty flag for ``document`` is set or
        cleared. ``dirty=False`` only clears the flag; it does not save
        body bytes (IF-API-07 contract).
    """
    registry.set_dirty(document, dirty)


class DirtyBlocksHandoff(Exception):
    """Raised when an Agent lease is blocked by a Human dirty flag.

    Attributes:
        code: Always :data:`HUMAN_DIRTY_BLOCKS_HANDOFF`.
        remediation: Non-empty remediation instructing the page to prompt
            save/discard.
    """

    def __init__(self, *, code: str, remediation: str) -> None:
        super().__init__(f"{code}: {remediation}")
        self.code = code
        self.remediation = remediation


@dataclass(frozen=True)
class SaveResult:
    """Result of :func:`apply_concurrent_save`.

    Attributes:
        ok: ``True`` when the save was committed; ``False`` when a CAS
            conflict was detected.
        committed_bytes: The committed bytes when ``ok``; ``None`` otherwise.
        conflict_code: ``DOCUMENT_WRITE_CONFLICT`` when ``not ok``; ``None``
            otherwise.
        current_revision: The current artifact revision after the save
            attempt.
        current_version_token: The current version token after the save
            attempt; ``None`` when ``ok``.
    """

    ok: bool
    committed_bytes: Optional[bytes]
    conflict_code: Optional[str]
    current_revision: int
    current_version_token: Optional[str]


class SaveConflict(Exception):
    """Raised when a save cannot proceed due to a CAS conflict.

    Attributes:
        code: ``DOCUMENT_WRITE_CONFLICT``.
        current_revision: The current artifact revision.
        current_version_token: The current version token.
    """

    def __init__(self, *, current_revision: int, current_version_token: str) -> None:
        super().__init__(
            f"{DOCUMENT_WRITE_CONFLICT}: current revision {current_revision}"
        )
        self.code = DOCUMENT_WRITE_CONFLICT
        self.current_revision = current_revision
        self.current_version_token = current_version_token


def apply_concurrent_save(
    *,
    registry: WriteLeaseRegistry,
    document: str,
    body_md: str,
    expected_revision: int,
    version_token: str,
    lease_id: str,
    actor: str,
) -> SaveResult:
    """Apply a CAS save under the registry's lock.

    Args:
        registry: The :class:`WriteLeaseRegistry` to mutate.
        document: Document path being saved.
        body_md: New body bytes.
        expected_revision: Artifact revision the caller last observed.
        version_token: Version token the caller last observed.
        lease_id: Lease id authorising the save.
        actor: Non-secret actor identity (unused for CAS but recorded for
            evidence by the caller).

    Returns:
        A :class:`SaveResult`. ``ok is True`` when the save was committed;
        ``ok is False`` with ``conflict_code == DOCUMENT_WRITE_CONFLICT``
        otherwise.

    Side effects:
        Mutates ``registry``: when the save succeeds, the active lease is
        released and the current revision is bumped. The body bytes are
        returned to the caller for persistence by the DOC/GIT adapters.
    """
    with registry._lock:  # noqa: SLF001 - CAS must serialise on the registry lock
        lease = registry._leases.get(document)  # noqa: SLF001
        if (
            lease is None
            or lease.status != LeaseStatus.ACTIVE
            or lease.lease_id != lease_id
            or lease.base_revision != expected_revision
            or lease.version_token != version_token
        ):
            current = registry._leases.get(document)  # noqa: SLF001
            current_revision = (
                current.base_revision + 1 if current is not None else expected_revision
            )
            return SaveResult(
                ok=False,
                committed_bytes=None,
                conflict_code=DOCUMENT_WRITE_CONFLICT,
                current_revision=current_revision,
                current_version_token=(
                    current.version_token if current is not None else version_token
                ),
            )
        # Winner: commit, bump revision, release lease.
        committed_bytes = body_md.encode("utf-8")
        new_revision = expected_revision + 1
        new_token = f"tok_{new_revision}"
        # Release the active lease; subsequent saves with the old token lose.
        registry._leases.pop(document, None)  # noqa: SLF001
        return SaveResult(
            ok=True,
            committed_bytes=committed_bytes,
            conflict_code=None,
            current_revision=new_revision,
            current_version_token=new_token,
        )


@dataclass(frozen=True)
class NonHolderPatchDecision:
    """Decision returned by :func:`decide_non_holder_patch_handling`.

    Attributes:
        action: ``remove_violating_patch`` when the violating patch can be
            safely removed; ``needs_attention`` otherwise.
        run_status: ``ok`` when the patch was removed; ``needs_attention``
            otherwise.
        notify_agent_to_reread: ``True`` when the Agent must re-read the
            current revision.
        repository_wide_revert: Always ``False``; Runtime never performs a
            repository-wide revert.
    """

    action: str
    run_status: str
    notify_agent_to_reread: bool
    repository_wide_revert: bool


def decide_non_holder_patch_handling(
    *,
    baseline_bytes_available: bool,
    patch_isolatable: bool,
    source_identifiable: bool,
) -> NonHolderPatchDecision:
    """Decide how to handle a non-holder's modification of a controlled doc.

    Args:
        baseline_bytes_available: Whether the most-recent accepted revision's
            bytes can be obtained from public revision evidence.
        patch_isolatable: Whether the violating patch can be exactly
            isolated from the other workspace/index bytes.
        source_identifiable: Whether the source of the violating patch can
            be identified.

    Returns:
        A :class:`NonHolderPatchDecision`. Only when all three preconditions
        are ``True`` is the patch removed and the Agent notified to re-read;
        otherwise the run is ``needs_attention``. ``repository_wide_revert``
        is always ``False``.
    """
    if baseline_bytes_available and patch_isolatable and source_identifiable:
        return NonHolderPatchDecision(
            action="remove_violating_patch",
            run_status="ok",
            notify_agent_to_reread=True,
            repository_wide_revert=False,
        )
    return NonHolderPatchDecision(
        action="needs_attention",
        run_status="needs_attention",
        notify_agent_to_reread=False,
        repository_wide_revert=False,
    )
