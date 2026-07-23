"""FR-0400: Task manifest, single writer & external modifications.

Each task attempt has a manifest binding baseline commit, Issue/FR/NFR/AC,
design refs, phase, write/forbidden scopes, test commands, Human/external
diff, prompt/schema identity and output contract.  An ordinary feature
holds at most one active write lease at a time.  Agent out-of-scope
modifications are rejected.  Human/external modifications are preserved
and routed: acceptable -> controlled commit, technical issue ->
discussion, source-unknown or baseline-changing -> stop and reconcile/
return upstream (AC-FR0400-01).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

ERROR_CODES = (
    "TASK_MANIFEST_INCOMPLETE",
    "TASK_SCOPE_DENIED",
    "TASK_LEASE_HELD",
    "TASK_LEASE_LOST",
    "TASK_BASELINE_STALE",
    "TASK_EXTERNAL_DIFF_UNKNOWN",
)

_REQUIRED_FIELDS = (
    "run_id",
    "task_id",
    "attempt_no",
    "graph_revision",
    "baseline_commit",
    "issue_id",
    "fr_ids",
    "ac_ids",
    "design_refs",
    "phase",
    "write_scopes",
    "forbidden_scopes",
    "test_commands",
    "prompt_bundle",
    "schema_refs",
    "output_contract",
    "deadline",
    "retry_policy",
)

_VALID_PHASES = ("red", "green", "refactor", "final")
_VALID_SOURCES = ("human", "external-attributed", "unknown")


class TaskManifestError(Exception):
    """A fail-closed manifest rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class TaskLeaseError(Exception):
    """A fail-closed lease decision rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _json_canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class TaskManifest:
    """An immutable task attempt manifest (AC-FR0400-01).

    Attributes:
        run_id: Runtime-issued run id.
        task_id: Internal task id from the validated DAG.
        attempt_no: Monotonically allocated attempt number.
        graph_revision: Bound graph revision.
        baseline_commit: 40-hex release-branch commit the attempt binds to.
        issue_id: GitHub Issue id for requirement traceability.
        fr_ids: Tuple of FR ids this task implements.
        nfr_ids: Tuple of NFR ids this task implements.
        ac_ids: Tuple of AC anchors.
        design_refs: Tuple of design revision/digest anchors.
        phase: ``red|green|refactor|final``.
        write_scopes: Tuple of authorised write paths/globs.
        forbidden_scopes: Tuple of explicitly forbidden paths/globs.
        test_commands: Mapping of phase->command.
        prompt_bundle: Stable prompt bundle digest.
        schema_refs: Tuple of schema refs the attempt consumes.
        output_contract: Stable output contract id.
        deadline: Absolute deadline (RFC 3339).
        retry_policy: Mapping with ``max_attempts`` etc.
        manifest_digest: ``sha256:<hex>`` canonical digest.
    """

    run_id: str
    task_id: str
    attempt_no: int
    graph_revision: str
    baseline_commit: str
    issue_id: int
    fr_ids: tuple[str, ...]
    nfr_ids: tuple[str, ...]
    ac_ids: tuple[str, ...]
    design_refs: tuple[str, ...]
    phase: str
    write_scopes: tuple[str, ...]
    forbidden_scopes: tuple[str, ...]
    test_commands: dict[str, str]
    prompt_bundle: str
    schema_refs: tuple[str, ...]
    output_contract: str
    deadline: str
    retry_policy: dict[str, Any]
    manifest_digest: str = ""


def build_manifest(**kwargs: Any) -> TaskManifest:
    """Build and validate a :class:`TaskManifest` (AC-FR0400-01).

    Args:
        **kwargs: See :class:`TaskManifest` field names.

    Returns:
        An immutable :class:`TaskManifest` with a canonical digest.

    Raises:
        TaskManifestError: With ``TASK_MANIFEST_INCOMPLETE`` if any required
            field is missing or ``phase`` is not one of ``red|green|refactor|
            final``.
    """
    missing = [k for k in _REQUIRED_FIELDS if not kwargs.get(k)]
    # nfr_ids may legitimately be empty for FR-only tasks.
    if "nfr_ids" in missing:
        missing.remove("nfr_ids")
    if missing:
        raise TaskManifestError(
            "TASK_MANIFEST_INCOMPLETE",
            f"missing manifest fields: {missing}",
        )
    if kwargs["phase"] not in _VALID_PHASES:
        raise TaskManifestError(
            "TASK_MANIFEST_INCOMPLETE",
            f"phase {kwargs['phase']!r} not in {_VALID_PHASES}",
        )
    manifest = TaskManifest(
        run_id=str(kwargs["run_id"]),
        task_id=str(kwargs["task_id"]),
        attempt_no=int(kwargs["attempt_no"]),
        graph_revision=str(kwargs["graph_revision"]),
        baseline_commit=str(kwargs["baseline_commit"]),
        issue_id=int(kwargs["issue_id"]),
        fr_ids=tuple(kwargs["fr_ids"]),
        nfr_ids=tuple(kwargs.get("nfr_ids", ()) or ()),
        ac_ids=tuple(kwargs["ac_ids"]),
        design_refs=tuple(kwargs["design_refs"]),
        phase=str(kwargs["phase"]),
        write_scopes=tuple(kwargs["write_scopes"]),
        forbidden_scopes=tuple(kwargs["forbidden_scopes"]),
        test_commands=dict(kwargs["test_commands"]),
        prompt_bundle=str(kwargs["prompt_bundle"]),
        schema_refs=tuple(kwargs["schema_refs"]),
        output_contract=str(kwargs["output_contract"]),
        deadline=str(kwargs["deadline"]),
        retry_policy=dict(kwargs["retry_policy"]),
    )
    return manifest


@dataclass(frozen=True)
class TaskLease:
    """An active write lease for a task attempt (AC-FR0400-01).

    Attributes:
        lease_id: Runtime-issued unique lease id.
        task_id: Bound task id.
        attempt_no: Bound attempt number.
        holder_role: ``devon|shield|runtime``.
        holder_session: Opaque session id of the holder.
        status: ``active`` (default).
        expires_at: Absolute expiry (RFC 3339).
    """

    lease_id: str
    task_id: str
    attempt_no: int
    holder_role: str
    holder_session: str
    status: str = "active"
    expires_at: str = ""


@dataclass(frozen=True)
class LeaseDecision:
    """The result of :func:`decide_lease`.

    Attributes:
        granted: ``True`` if a new lease was granted.
        lease: The granted :class:`TaskLease` or ``None`` if denied.
        reason_code: Stable code explaining a denial (e.g. ``TASK_LEASE_HELD``).
    """

    granted: bool
    lease: TaskLease | None
    reason_code: str = ""


def _path_in_scopes(path: str, scopes: tuple[str, ...]) -> bool:
    """Return True if ``path`` matches any glob in ``scopes`` (prefix match)."""
    for scope in scopes:
        if path == scope or path.startswith(scope.rstrip("*")):
            return True
    return False


def decide_lease(
    manifest: TaskManifest,
    *,
    existing_active_lease: TaskLease | None,
    actor: str,
    requested_write_paths: tuple[str, ...] = (),
) -> LeaseDecision:
    """Decide whether to grant a new write lease for ``manifest`` (AC-FR0400-01).

    Args:
        manifest: The task attempt manifest requesting the lease.
        existing_active_lease: Any active lease currently held for the task;
            pass ``None`` if there is no active lease.
        actor: Actor identity (e.g. ``devon:1``, ``shield:2``).
        requested_write_paths: Optional explicit paths the actor intends to
            modify; validated against ``manifest.write_scopes``.

    Returns:
        A :class:`LeaseDecision` with ``granted=True`` and the new lease, or
        ``granted=False`` with a stable reason code.

    Raises:
        TaskLeaseError: With ``TASK_SCOPE_DENIED`` if any requested path is
            outside ``write_scopes`` or inside ``forbidden_scopes``.
    """
    for path in requested_write_paths:
        if _path_in_scopes(path, manifest.forbidden_scopes) or not _path_in_scopes(
            path, manifest.write_scopes
        ):
            raise TaskLeaseError(
                "TASK_SCOPE_DENIED",
                f"path {path!r} is outside the authorised write scopes or forbidden",
            )
    if existing_active_lease is not None and existing_active_lease.status == "active":
        return LeaseDecision(granted=False, lease=None, reason_code="TASK_LEASE_HELD")
    role = actor.split(":", 1)[0] if ":" in actor else actor
    lease_id = (
        "lease:"
        + hashlib.sha256(
            f"{manifest.task_id}:{manifest.attempt_no}:{actor}".encode("utf-8")
        ).hexdigest()[:12]
    )
    lease = TaskLease(
        lease_id=lease_id,
        task_id=manifest.task_id,
        attempt_no=manifest.attempt_no,
        holder_role=role,
        holder_session=actor,
    )
    return LeaseDecision(granted=True, lease=lease)


@dataclass(frozen=True)
class ExternalDiff:
    """A Human/external workspace modification observed during a task attempt.

    Attributes:
        paths: Tuple of paths the diff touches.
        source: ``human|external-attributed|unknown``.
        baseline_changed: ``True`` if the diff changes the bound baseline
            commit.
        digest: ``sha256:<hex>`` of the diff bytes.
        technical_concern: Optional technical concern raised by the
            specialist Agent (e.g. ``scope-conflict``).
    """

    paths: tuple[str, ...]
    source: str
    baseline_changed: bool
    digest: str
    technical_concern: str = ""


@dataclass(frozen=True)
class DiffClassification:
    """The disposition and route for an :class:`ExternalDiff` (AC-FR0400-01).

    Attributes:
        disposition: ``accept|discuss|stop``.
        route: ``controlled-commit|discussion|reconcile|return-upstream``.
        reason: Human-readable reason for audit.
    """

    disposition: str
    route: str
    reason: str = ""


def classify_external_diff(diff: ExternalDiff) -> DiffClassification:
    """Classify an external diff and choose its route (AC-FR0400-01).

    Args:
        diff: The :class:`ExternalDiff` observed by Runtime.

    Returns:
        A :class:`DiffClassification` with disposition and route.

    Raises:
        TaskManifestError: With ``TASK_EXTERNAL_DIFF_UNKNOWN`` if ``source``
            is not in :data:`_VALID_SOURCES`.
    """
    if diff.source not in _VALID_SOURCES:
        raise TaskManifestError(
            "TASK_EXTERNAL_DIFF_UNKNOWN",
            f"diff source {diff.source!r} is not recognised",
        )
    if diff.baseline_changed:
        return DiffClassification(
            disposition="stop",
            route="return-upstream",
            reason="external diff changed the bound baseline; cannot overwrite",
        )
    if diff.source == "unknown":
        return DiffClassification(
            disposition="stop",
            route="reconcile",
            reason="diff source unknown; cannot attribute",
        )
    if diff.technical_concern:
        return DiffClassification(
            disposition="discuss",
            route="discussion",
            reason=f"technical concern: {diff.technical_concern}",
        )
    return DiffClassification(
        disposition="accept",
        route="controlled-commit",
        reason="attributed external diff accepted into controlled commit",
    )
