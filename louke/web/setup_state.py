"""v2 Setup manifest with compare-and-swap transitions.

AC-FR0001-01, AC-FR0001-02, AC-FR0101-01, AC-FR0101-02,
AC-FR0301-01, AC-FR0301-02, AC-NFR0001-01

Replaces the old six-step ``SetupJourney`` with a three-state
manifest: ``pending_user`` -> ``pending_model`` -> ``complete``.

The manifest is persisted at ``.louke/web-setup-state.json`` with
schema version 2. Every transition uses compare-and-swap on the
monotonic ``revision`` field so concurrent requests cannot create
duplicate identities or skip the model probe.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

MANIFEST_VERSION = 2
MANIFEST_FILENAME = "web-setup-state.json"


class SetupStateError(ValueError):
    """Raised when the manifest is corrupt, unknown, or violates a contract."""


class SetupStateMismatch(SetupStateError):
    """Raised when a CAS transition receives a stale ``expected_revision``."""


class SetupStatus(str, Enum):
    """The three allowed manifest states."""

    PENDING_USER = "pending_user"
    PENDING_MODEL = "pending_model"
    COMPLETE = "complete"


@dataclass(frozen=True)
class ModelCheck:
    """A redacted snapshot of the most recent model probe.

    Args:
        check_id: Stable identifier for the probe attempt.
        revision: Check-scoped revision (separate from manifest revision).
        state: One of ``queued|running|passed|failed|uncertain``.
        model_id: The model id that succeeded, or ``None``.
        diagnosis: Non-secret diagnostic dict, or ``None``.
        observed_at: ISO-8601 timestamp of the observation.
    """

    check_id: str
    revision: int
    state: str
    model_id: str | None = None
    diagnosis: dict[str, Any] | None = None
    observed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serialisable representation."""
        return {
            "check_id": self.check_id,
            "revision": self.revision,
            "state": self.state,
            "model_id": self.model_id,
            "diagnosis": self.diagnosis,
            "observed_at": self.observed_at,
        }


@dataclass(frozen=True)
class SetupManifest:
    """Immutable projection of the persisted Setup manifest.

    Args:
        workspace_id: The workspace this manifest belongs to.
        revision: Monotonic non-negative integer; bumped on every mutation.
        status: One of :class:`SetupStatus`.
        first_principal_id: The first user's principal id, or ``None``.
        model_check: The most recent model probe snapshot, or ``None``.
        completed_at: ISO-8601 timestamp when Setup completed, or ``None``.
    """

    workspace_id: str
    revision: int
    status: SetupStatus
    first_principal_id: str | None = None
    model_check: ModelCheck | None = None
    completed_at: str | None = None

    @property
    def is_complete(self) -> bool:
        """Return True iff the manifest is in the ``complete`` state."""
        return self.status == SetupStatus.COMPLETE

    def advance_to_pending_model(
        self,
        *,
        first_principal_id: str,
        expected_revision: int,
    ) -> SetupManifest:
        """Record the first user and advance to ``pending_model``.

        Args:
            first_principal_id: The principal id of the newly created user.
            expected_revision: The revision the caller observed; must match.

        Returns:
            A new manifest with ``status=pending_model`` and ``revision+1``.

        Raises:
            SetupStateMismatch: If ``expected_revision`` does not match.
            SetupStateError: If a different principal was already recorded.
        """
        if expected_revision != self.revision:
            raise SetupStateMismatch(
                f"stale revision: expected {expected_revision}, current {self.revision}"
            )
        if (
            self.first_principal_id is not None
            and self.first_principal_id != first_principal_id
        ):
            raise SetupStateError(
                f"principal mismatch: manifest has "
                f"{self.first_principal_id!r}, caller sent "
                f"{first_principal_id!r}"
            )
        if self.status == SetupStatus.COMPLETE:
            raise SetupStateError("cannot advance past complete")
        if (
            self.status == SetupStatus.PENDING_MODEL
            and self.first_principal_id == first_principal_id
        ):
            return self
        return SetupManifest(
            workspace_id=self.workspace_id,
            revision=self.revision + 1,
            status=SetupStatus.PENDING_MODEL,
            first_principal_id=first_principal_id,
            model_check=self.model_check,
            completed_at=None,
        )

    def complete(
        self,
        *,
        model_check_state: str,
        model_check_id: str,
        model_check_revision: int,
        model_id: str | None,
        diagnosis: dict[str, Any] | None,
        observed_at: str,
        expected_revision: int,
    ) -> SetupManifest:
        """Atomically complete Setup after a passed model probe.

        Args:
            model_check_state: Must be ``"passed"``.
            model_check_id: Stable identifier for the probe.
            model_check_revision: Check-scoped revision.
            model_id: The model that succeeded.
            diagnosis: Non-secret diagnostic, or ``None``.
            observed_at: ISO-8601 timestamp.
            expected_revision: The revision the caller observed.

        Returns:
            A new manifest with ``status=complete`` and ``revision+1``.

        Raises:
            SetupStateMismatch: If ``expected_revision`` does not match.
            SetupStateError: If ``model_check_state != "passed"`` or
                no first user has been recorded.
        """
        if expected_revision != self.revision:
            raise SetupStateMismatch(
                f"stale revision: expected {expected_revision}, current {self.revision}"
            )
        if self.first_principal_id is None:
            raise SetupStateError("cannot complete without a first principal")
        if model_check_state != "passed":
            raise SetupStateError(
                f"model_check.state must be 'passed'; got {model_check_state!r}"
            )
        check = ModelCheck(
            check_id=model_check_id,
            revision=model_check_revision,
            state=model_check_state,
            model_id=model_id,
            diagnosis=diagnosis,
            observed_at=observed_at,
        )
        return SetupManifest(
            workspace_id=self.workspace_id,
            revision=self.revision + 1,
            status=SetupStatus.COMPLETE,
            first_principal_id=self.first_principal_id,
            model_check=check,
            completed_at=observed_at,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serialisable representation."""
        return {
            "version": MANIFEST_VERSION,
            "workspace_id": self.workspace_id,
            "revision": self.revision,
            "status": self.status.value,
            "first_principal_id": self.first_principal_id,
            "model_check": self.model_check.to_dict() if self.model_check else None,
            "completed_at": self.completed_at,
        }


def _default_manifest(workspace_id: str) -> SetupManifest:
    """Return the initial manifest for a blank workspace."""
    return SetupManifest(
        workspace_id=workspace_id,
        revision=0,
        status=SetupStatus.PENDING_USER,
    )


def read_manifest(workspace_root: Path, *, workspace_id: str) -> SetupManifest:
    """Read and validate the persisted Setup manifest.

    Args:
        workspace_root: The workspace root directory (containing ``.louke/``).
        workspace_id: The expected workspace id; mismatch fails closed.

    Returns:
        The validated :class:`SetupManifest`.

    Raises:
        SetupStateError: If the file is corrupt, has an unknown schema
            version, or the ``workspace_id`` does not match.
    """
    state_path = workspace_root / ".louke" / MANIFEST_FILENAME
    if not state_path.exists():
        return _default_manifest(workspace_id)
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SetupStateError(f"corrupt setup manifest at {state_path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise SetupStateError("setup manifest payload must be an object")
    version = raw.get("version")
    if version != MANIFEST_VERSION:
        raise SetupStateError(
            f"unknown setup manifest version: {version!r}; expected {MANIFEST_VERSION}"
        )
    manifest_workspace_id = raw.get("workspace_id")
    if manifest_workspace_id != workspace_id:
        raise SetupStateError(
            f"workspace_id mismatch: manifest has "
            f"{manifest_workspace_id!r}, expected {workspace_id!r}"
        )
    status_str = raw.get("status", "pending_user")
    try:
        status = SetupStatus(status_str)
    except ValueError as exc:
        raise SetupStateError(f"unknown status: {status_str!r}") from exc
    mc_raw = raw.get("model_check")
    model_check = None
    if mc_raw is not None and isinstance(mc_raw, dict):
        model_check = ModelCheck(
            check_id=mc_raw.get("check_id", ""),
            revision=mc_raw.get("revision", 0),
            state=mc_raw.get("state", ""),
            model_id=mc_raw.get("model_id"),
            diagnosis=mc_raw.get("diagnosis"),
            observed_at=mc_raw.get("observed_at", ""),
        )
    return SetupManifest(
        workspace_id=workspace_id,
        revision=raw.get("revision", 0),
        status=status,
        first_principal_id=raw.get("first_principal_id"),
        model_check=model_check,
        completed_at=raw.get("completed_at"),
    )


def try_read_manifest(workspace_root: Path) -> SetupManifest | None:
    """Best-effort manifest read for gate checks; ``None`` on any error.

    Unlike :func:`read_manifest`, this function does not require a
    ``workspace_id`` and returns ``None`` instead of raising. Missing
    files return a default ``pending_user`` manifest (not ``None``),
    so callers only need to check the status.

    Args:
        workspace_root: The workspace root directory.

    Returns:
        The manifest, or ``None`` if the file is corrupt, has an
        unknown schema, or cannot be parsed.
    """
    state_path = workspace_root / ".louke" / MANIFEST_FILENAME
    if not state_path.exists():
        return _default_manifest("")
    try:
        raw = json.loads(state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(raw, dict):
        return None
    if raw.get("version") != MANIFEST_VERSION:
        return None
    status_str = raw.get("status", "pending_user")
    try:
        status = SetupStatus(status_str)
    except ValueError:
        return None
    mc_raw = raw.get("model_check")
    model_check = None
    if mc_raw is not None and isinstance(mc_raw, dict):
        model_check = ModelCheck(
            check_id=mc_raw.get("check_id", ""),
            revision=mc_raw.get("revision", 0),
            state=mc_raw.get("state", ""),
            model_id=mc_raw.get("model_id"),
            diagnosis=mc_raw.get("diagnosis"),
            observed_at=mc_raw.get("observed_at", ""),
        )
    return SetupManifest(
        workspace_id=raw.get("workspace_id", ""),
        revision=raw.get("revision", 0),
        status=status,
        first_principal_id=raw.get("first_principal_id"),
        model_check=model_check,
        completed_at=raw.get("completed_at"),
    )


def write_manifest(workspace_root: Path, manifest: SetupManifest) -> None:
    """Atomically persist the Setup manifest.

    Args:
        workspace_root: The workspace root directory.
        manifest: The manifest to persist.
    """
    louke_dir = workspace_root / ".louke"
    louke_dir.mkdir(parents=True, exist_ok=True)
    state_path = louke_dir / MANIFEST_FILENAME
    body = json.dumps(manifest.to_dict(), sort_keys=True, indent=2) + "\n"
    fd, tmp = tempfile.mkstemp(dir=str(louke_dir), prefix=".setup-state-")
    try:
        with open(fd, "w", encoding="utf-8") as fh:
            fh.write(body)
        Path(tmp).replace(state_path)
    except Exception:
        Path(tmp).unlink(missing_ok=True)
        raise


def migrate_v1_state(
    v1_state: dict[str, Any],
    *,
    first_principal_id: str | None,
) -> dict[str, Any]:
    """Migrate a legacy v1 Setup state dict to the v2 schema.

    Args:
        v1_state: The old ``{version:1, current_step, completed_steps, ...}``.
        first_principal_id: The first user's principal id, or ``None``.

    Returns:
        A v2-compatible dict with ``version=2``. If a first user exists
        but there is no evidence of a passed model probe, the status
        is ``pending_model``; otherwise ``pending_user``.
    """
    if first_principal_id is not None:
        return {
            "version": MANIFEST_VERSION,
            "workspace_id": "",
            "revision": 1,
            "status": SetupStatus.PENDING_MODEL.value,
            "first_principal_id": first_principal_id,
            "model_check": None,
            "completed_at": None,
        }
    return {
        "version": MANIFEST_VERSION,
        "workspace_id": "",
        "revision": 0,
        "status": SetupStatus.PENDING_USER.value,
        "first_principal_id": None,
        "model_check": None,
        "completed_at": None,
    }
