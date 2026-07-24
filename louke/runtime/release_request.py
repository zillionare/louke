"""FR-0300: Web Release 请求与单活跃主 Release.

Implements the deterministic contract slice of FR-0300:

* `preview_release_request` validates the human-supplied story and release
  version, computes a stable request digest, and produces a
  :class:`ReleasePreview` that carries zero release-level side effects. When
  an active main release is already present, the preview records the blocking
  reason but still performs no external mutation.
* `confirm_release_request` is the single routing authority for a confirmed
  release request. When the workspace has an active main release, the request
  is idempotently routed to the canonical :class:`BacklogStore` keyed by
  ``(workspace_id, request_digest)``; concurrent and repeated confirms for the
  same identity return the same entry_id. When there is no active main
  release, the request proceeds to `preflight` and no Backlog entry is
  written.

The module deliberately does not create Project, WorkflowRun, release GitHub
Project, release branch or Spec directory resources; those belong to FR-0400
Foundation and are only created after the single-active-main check and the
`main` preflight check have both passed.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from packaging.version import InvalidVersion, Version


# ---------------------------------------------------------------------------
# Identity and digest
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReleaseRequestIdentity:
    """Stable identity for a release request.

    Attributes:
        workspace_id: Opaque workspace identifier the request belongs to.
        story: Non-empty one-sentence release设想 supplied by the human.
        release_version: Canonical release version (e.g. ``0.14.0``).
    """

    workspace_id: str
    story: str
    release_version: str

    def __post_init__(self) -> None:
        """Reject incomplete identities before they can be hashed or stored.

        Args:
            None. Dataclass fields are validated after construction.

        Returns:
            ``None`` when all identity fields are non-empty strings.

        Raises:
            ValueError: If ``workspace_id``, ``story`` or ``release_version``
                is empty after trimming.
        """
        fields = {
            "workspace_id": self.workspace_id,
            "story": self.story,
            "release_version": self.release_version,
        }
        for field, value in fields.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")

    @property
    def request_digest(self) -> str:
        """Return the deterministic ``sha256:<hex>`` digest of this identity.

        The digest covers ``workspace_id``, ``story`` and ``release_version``
        so that any field change produces a different digest, and identical
        identities always produce the same digest.
        """
        payload = json.dumps(
            {
                "workspace_id": self.workspace_id,
                "story": self.story,
                "release_version": self.release_version,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


class PreviewError(Exception):
    """Raised when a preview request fails input validation.

    Attributes:
        field: The input field that failed validation.
        code: Stable error code from :data:`IF-COMMON-02` (``VALIDATION_FAILED``
            or ``RELEASE_VERSION_INVALID``).
        message: Non-secret human-readable explanation.
    """

    def __init__(self, *, field: str, code: str, message: str) -> None:
        super().__init__(f"{code}: {field}: {message}")
        self.field = field
        self.code = code
        self.message = message

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.code}: {self.field}: {self.message}"


@dataclass(frozen=True)
class ReleasePreview:
    """Result of a successful preview request.

    Attributes:
        workspace_id: The workspace the preview belongs to.
        request_digest: Stable digest of the request identity.
        story: Echo of the validated story.
        release_version: Echo of the validated canonical version.
        blocked_reason: Non-empty when an active main release blocks the
            request; ``None`` otherwise.
        side_effects: Always empty for preview (FR-0300 AC-01).
    """

    workspace_id: str
    request_digest: str
    story: str
    release_version: str
    blocked_reason: Optional[str]
    side_effects: tuple[str, ...] = ()


def _is_valid_release_version(version: str) -> bool:
    """Return whether the host-provided version is safe as a Git branch leaf.

    IF-WEB-03 owns product version validity. This boundary only rejects empty,
    control, path-traversal, and Git ref-invalid values that could escape the
    controlled release branch/worktree identity.
    """
    value = version.strip().removeprefix("v")
    if not value or value in {".", ".."}:
        return False
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        return False
    if any(char.isspace() or char in "~^:?*[\\" for char in value):
        return False
    if (
        value.startswith("/")
        or value.endswith("/")
        or "//" in value
        or ".." in value
        or "/." in value
        or value.endswith(".")
        or value.endswith(".lock")
        or "@{" in value
    ):
        return False
    return True


def _canonical_release_version(version: str) -> Optional[str]:
    """Return the canonical 3-segment PEP440 form of ``version``.

    Per interfaces §IF-PREVIEW-01: one- or two-segment release tuples
    are padded to a 3-tuple canonical PEP440 version; ``local`` and
    ``dirty`` markers are rejected. Returns ``None`` when the input
    cannot be canonicalised.

    Examples::

        ``0.14``       -> ``0.14.0``
        ``v0.14``      -> ``0.14.0``
        ``0.14.1``     -> ``0.14.1``
        ``0.14+local`` -> ``None``
        ``dirty``      -> ``None``
    """
    raw = version.strip().removeprefix("v")
    if not raw:
        return None
    if "+" in raw or "dirty" in raw:
        return None
    try:
        parsed = Version(raw)
    except InvalidVersion:
        return None
    if parsed.local is not None:
        return None
    # ``Version`` normalises ``0.14`` to ``0.14`` (release segment
    # tuple ``(0, 14)``). Pad to 3 segments per the contract.
    segments = list(parsed.release)
    while len(segments) < 3:
        segments.append(0)
    canonical = ".".join(str(s) for s in segments[:3])
    return canonical


def preview_release_request(
    *,
    workspace_id: str,
    story: str,
    release_version: str,
    active_main_release_present: bool,
) -> ReleasePreview:
    """Validate inputs and produce a side-effect-free release preview.

    Args:
        workspace_id: Opaque workspace identifier.
        story: Human one-sentence设想; must be non-empty after strip.
        release_version: Canonical release version; must be structurally valid.
        active_main_release_present: Whether the workspace currently has an
            active main release.

    Returns:
        A :class:`ReleasePreview` with ``side_effects == ()``.

    Raises:
        PreviewError: If ``story`` or ``release_version`` is empty or invalid.
            The error code is ``VALIDATION_FAILED`` for empty story and
            ``RELEASE_VERSION_INVALID`` for malformed versions.

    Side effects:
        None. No release-level resources are created or modified; the Backlog
        is not touched.
    """
    if not isinstance(story, str) or not story.strip():
        raise PreviewError(
            field="story",
            code="VALIDATION_FAILED",
            message="story must be a non-empty one-sentence release设想",
        )
    if not isinstance(release_version, str) or not release_version.strip():
        raise PreviewError(
            field="release_version",
            code="RELEASE_VERSION_INVALID",
            message="release_version must be a canonical release version",
        )
    if not _is_valid_release_version(release_version):
        raise PreviewError(
            field="release_version",
            code="RELEASE_VERSION_INVALID",
            message=f"release_version is not a canonical version: {release_version!r}",
        )

    canonical_version = _canonical_release_version(release_version)
    if canonical_version is None:
        raise PreviewError(
            field="release_version",
            code="RELEASE_VERSION_INVALID",
            message=(
                f"release_version is not a canonical PEP440 version "
                f"(local/dirty markers are rejected): {release_version!r}"
            ),
        )

    identity = ReleaseRequestIdentity(
        workspace_id=workspace_id,
        story=story.strip(),
        release_version=canonical_version,
    )
    blocked_reason: Optional[str] = None
    if active_main_release_present:
        blocked_reason = (
            "workspace already has an active main release; "
            "request routed to Backlog on confirm"
        )
    return ReleasePreview(
        workspace_id=identity.workspace_id,
        request_digest=identity.request_digest,
        story=identity.story,
        release_version=identity.release_version,
        blocked_reason=blocked_reason,
        side_effects=(),
    )


# ---------------------------------------------------------------------------
# Backlog store
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BacklogEntry:
    """A canonical Backlog entry produced by FR-0300 routing.

    Attributes:
        entry_id: Stable opaque identifier keyed by
            ``(workspace_id, request_digest)``.
        workspace_id: The workspace the entry belongs to.
        request_digest: Stable digest of the request identity.
        story: Original human story.
        release_version: Original canonical release version.
        reason: Non-empty blocking reason.
        created_at: UTC RFC 3339 timestamp.
        source_identity: The original :class:`ReleaseRequestIdentity`.
        decision: Terminal decision (``parked``/``no_go``) for FR-0800;
            ``None`` for FR-0300 blocked-by-active-main entries.
    """

    entry_id: str
    workspace_id: str
    request_digest: str
    story: str
    release_version: str
    reason: str
    created_at: str
    source_identity: ReleaseRequestIdentity
    decision: Optional[str] = None


def _entry_id_for(identity: ReleaseRequestIdentity) -> str:
    """Return the stable entry id for ``identity``.

    The id is the first 24 hex characters of ``sha256(workspace_id|digest)`` so
    that repeated or concurrent confirms for the same logical identity produce
    the same id without coordinating up front.
    """
    payload = f"{identity.workspace_id}|{identity.request_digest}"
    return f"bl_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def _now_iso_utc() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).isoformat()


class BacklogStore:
    """Persistent, concurrency-safe store for :class:`BacklogEntry`.

    The store serialises to a JSON file at ``path`` so that a process restart
    recovers byte-equal entries (FR-0300 AC-03). All mutating operations take
    a process-wide lock; the on-disk file is written atomically via
    ``os.replace``.
    """

    def __init__(self, path: Optional[Path]) -> None:
        self._path = path
        self._lock = threading.RLock()
        self._entries: dict[tuple[str, str], BacklogEntry] = {}
        if path is not None:
            self._load_from_disk()

    @classmethod
    def in_memory(cls) -> "BacklogStore":
        """Return a fresh empty :class:`BacklogStore` with no on-disk path."""
        return cls(path=None)

    @classmethod
    def at_path(cls, path: Path) -> "BacklogStore":
        """Return a :class:`BacklogStore` that persists to ``path``."""
        return cls(path=path)

    def _load_from_disk(self) -> None:
        assert self._path is not None
        if not self._path.exists():
            return
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for raw in data.get("entries", []):
            identity = ReleaseRequestIdentity(
                workspace_id=raw["source_identity"]["workspace_id"],
                story=raw["source_identity"]["story"],
                release_version=raw["source_identity"]["release_version"],
            )
            entry = BacklogEntry(
                entry_id=raw["entry_id"],
                workspace_id=raw["workspace_id"],
                request_digest=raw["request_digest"],
                story=raw["story"],
                release_version=raw["release_version"],
                reason=raw["reason"],
                created_at=raw["created_at"],
                source_identity=identity,
                decision=raw.get("decision"),
            )
            self._entries[(entry.workspace_id, entry.entry_id)] = entry

    def _flush(self) -> None:
        if self._path is None:
            return
        payload = {
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "workspace_id": e.workspace_id,
                    "request_digest": e.request_digest,
                    "story": e.story,
                    "release_version": e.release_version,
                    "reason": e.reason,
                    "created_at": e.created_at,
                    "source_identity": {
                        "workspace_id": e.source_identity.workspace_id,
                        "story": e.source_identity.story,
                        "release_version": e.source_identity.release_version,
                    },
                    "decision": e.decision,
                }
                for e in self._entries.values()
            ]
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(tmp, self._path)

    def upsert(self, entry: BacklogEntry) -> BacklogEntry:
        """Idempotently insert or return the existing entry for the same key.

        Args:
            entry: The entry to insert.

        Returns:
            The entry stored for ``(workspace_id, entry_id)``. If an entry
            with the same key already exists, the existing entry is returned
            unchanged and the new entry is dropped.
        """
        with self._lock:
            key = (entry.workspace_id, entry.entry_id)
            existing = self._entries.get(key)
            if existing is not None:
                return existing
            self._entries[key] = entry
            self._flush()
            return entry

    def list_entries(self, *, workspace_id: str) -> tuple[BacklogEntry, ...]:
        """Return all entries for ``workspace_id`` ordered by ``created_at``."""
        with self._lock:
            entries = [
                e for e in self._entries.values() if e.workspace_id == workspace_id
            ]
        entries.sort(key=lambda e: (e.created_at, e.entry_id))
        return tuple(entries)


# ---------------------------------------------------------------------------
# Confirm / routing
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfirmResult:
    """Result of :func:`confirm_release_request`.

    Attributes:
        routed_to: ``backlog`` when blocked by active main release;
            ``preflight`` when the request may proceed to FR-0400.
        entry_id: The Backlog entry id when ``routed_to == 'backlog'``;
            ``None`` otherwise.
        created_resources: Always ``()`` for FR-0300; Foundation resources
            belong to FR-0400 and are not created here.
    """

    routed_to: str
    entry_id: Optional[str]
    created_resources: tuple[str, ...] = ()


def confirm_release_request(
    *,
    identity: ReleaseRequestIdentity,
    active_main_release_present: bool,
    store: BacklogStore,
) -> ConfirmResult:
    """Route a confirmed release request.

    Args:
        identity: Stable identity of the request.
        active_main_release_present: Whether the workspace has an active main
            release. When ``True`` the request is routed idempotently to the
            Backlog; when ``False`` it proceeds to preflight (FR-0400).
        store: The :class:`BacklogStore` to write to when routed to Backlog.

    Returns:
        A :class:`ConfirmResult` describing the routing decision.

    Side effects:
        When routed to Backlog, exactly one :class:`BacklogEntry` is persisted
        to ``store``; repeated or concurrent calls with the same identity
        return the same ``entry_id`` and do not create a second entry. When
        routed to preflight, no Backlog entry is written and no release-level
        resources are created.
    """
    if not active_main_release_present:
        return ConfirmResult(routed_to="preflight", entry_id=None, created_resources=())

    entry_id = _entry_id_for(identity)
    entry = BacklogEntry(
        entry_id=entry_id,
        workspace_id=identity.workspace_id,
        request_digest=identity.request_digest,
        story=identity.story,
        release_version=identity.release_version,
        reason=(
            "workspace already has an active main release; "
            "request held in Backlog until current release completes"
        ),
        created_at=_now_iso_utc(),
        source_identity=identity,
        decision=None,
    )
    stored = store.upsert(entry)
    return ConfirmResult(
        routed_to="backlog",
        entry_id=stored.entry_id,
        created_resources=(),
    )
