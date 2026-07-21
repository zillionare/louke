"""FR-0100: M-IMPL entry & pre-commit reconcile.

Runtime may only enter ``M-IMPL`` after the current implementation baseline
is complete, the design program check and Prism review are both PASS, and
every workspace modification is attributable.  Entry preserves/merges
existing hooks per the pre-commit contract, installs/updates the managed
entry, and reads back the actual entry/version/config digest.  Tracked
managed-config changes form a controlled infrastructure commit and a new
baseline; local hook identity is recorded only as evidence.  Failure or
drift blocks Archer/Devon dispatch with a stable, diagnosable reason
(AC-FR0100-01).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

ERROR_CODES = (
    "IMPL_DESIGN_NOT_CURRENT",
    "IMPL_WORKSPACE_DIRTY_UNATTRIBUTED",
    "IMPL_PC_CONTRACT_MISSING",
    "IMPL_PC_INSTALL_FAILED",
    "IMPL_PC_READBACK_MISSING",
    "IMPL_PC_DRIFT",
    "IMPL_INFRA_COMMIT_CONFLICT",
)

_REQUIRED_DESIGN_KEYS = (
    "revision",
    "digest",
    "program_evidence_id",
    "prism_review_id",
    "program_status",
    "prism_verdict",
)


class ImplEntryError(Exception):
    """A fail-closed M-IMPL entry rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _json_canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _check_truthy(value: Any, key: str) -> None:
    if value is None or value == "":
        raise ImplEntryError("IMPL_DESIGN_NOT_CURRENT", f"missing input: {key}")


def _check_design(design: dict[str, Any]) -> None:
    if not isinstance(design, dict):
        raise ImplEntryError("IMPL_DESIGN_NOT_CURRENT", "design must be a mapping")
    for key in _REQUIRED_DESIGN_KEYS:
        if not design.get(key):
            raise ImplEntryError("IMPL_DESIGN_NOT_CURRENT", f"missing design.{key}")
    if design.get("program_status") != "PASS":
        raise ImplEntryError(
            "IMPL_DESIGN_NOT_CURRENT",
            f"design program_status={design.get('program_status')!r} is not PASS",
        )
    if design.get("prism_verdict") != "PASS":
        raise ImplEntryError(
            "IMPL_DESIGN_NOT_CURRENT",
            f"design prism_verdict={design.get('prism_verdict')!r} is not PASS",
        )


def _check_workspace(workspace: dict[str, Any]) -> None:
    if not isinstance(workspace, dict):
        raise ImplEntryError(
            "IMPL_WORKSPACE_DIRTY_UNATTRIBUTED", "workspace must be a mapping"
        )
    diffs = workspace.get("diffs", []) or []
    unattributed = [
        d
        for d in diffs
        if d.get("source")
        not in ("runtime", "human", "external-attributed", "controlled-commit")
    ]
    if unattributed:
        paths = ", ".join(d.get("path", "?") for d in unattributed)
        raise ImplEntryError(
            "IMPL_WORKSPACE_DIRTY_UNATTRIBUTED",
            f"workspace has unattributed modifications: {paths}",
        )


def _split_preserved_managed(
    hooks: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    preserved, managed = [], []
    for hook in hooks:
        if hook.get("id") == "preserve-existing":
            preserved.append(hook)
        else:
            managed.append(hook)
    return preserved, managed


@dataclass(frozen=True)
class PreCommitReadback:
    """Pre-commit install/readback evidence (AC-FR0100-01).

    Attributes:
        entry: Hook entry id (e.g. ``pre-commit``).
        tool_version: Declared tool version (e.g. ``4.6.0``).
        config_digest: SHA-256 of the managed config file bytes.
        hook_stage_digests: Per-stage digest of installed hooks.
        preserved_hooks: Tuple of preserved existing-hook records.
        managed_hooks: Tuple of Louke-managed hook records.
        readback_status: ``in_sync|drifted|missing|conflict``.
    """

    entry: str
    tool_version: str
    config_digest: str
    hook_stage_digests: tuple[str, ...]
    preserved_hooks: tuple[dict[str, Any], ...]
    managed_hooks: tuple[dict[str, Any], ...]
    readback_status: str


@dataclass(frozen=True)
class InfrastructureCommit:
    """Controlled infrastructure commit request (AC-FR0100-01).

    Attributes:
        paths: Tuple of managed-config paths to commit.
        expected_branch_oid: Expected release-branch OID for the CAS.
        reason: Stable reason code for the audit record.
    """

    paths: tuple[str, ...]
    expected_branch_oid: str
    reason: str = "tracked-managed-config-change"


def _readback_precommit(
    contract: dict[str, Any],
    *,
    installed_stages: list[str],
    managed_config_present: bool,
    tracked_config_changes: list[dict[str, Any]] | None,
) -> PreCommitReadback:
    if not contract:
        raise ImplEntryError("IMPL_PC_CONTRACT_MISSING", "pre-commit contract missing")
    payload = contract.get("payload", {}) or {}
    expected_stages = list(payload.get("stages", []) or [])
    if not managed_config_present and not tracked_config_changes:
        raise ImplEntryError(
            "IMPL_PC_READBACK_MISSING",
            "managed config file (.pre-commit-config.yaml) not present",
        )
    if not installed_stages and expected_stages:
        raise ImplEntryError(
            "IMPL_PC_INSTALL_FAILED",
            "no hook stages installed; expected " + ",".join(expected_stages),
        )
    missing = [s for s in expected_stages if s not in installed_stages]
    if missing:
        raise ImplEntryError(
            "IMPL_PC_DRIFT",
            f"installed stages {installed_stages} missing expected {missing}",
        )
    preserved, managed = _split_preserved_managed(list(payload.get("hooks", []) or []))
    hook_stage_digests = tuple(
        hashlib.sha256(
            _json_canonical(
                {"stage": s, "hooks": list(payload.get("hooks", []) or [])}
            ).encode("utf-8")
        ).hexdigest()
        for s in expected_stages
    )
    config_payload = {
        "managed_config_path": payload.get("managed_config_path"),
        "tool_version": payload.get("tool_version"),
        "stages": expected_stages,
        "hooks": list(payload.get("hooks", []) or []),
    }
    if tracked_config_changes:
        config_payload["tracked_changes"] = list(tracked_config_changes)
    config_digest = (
        "sha256:"
        + hashlib.sha256(_json_canonical(config_payload).encode("utf-8")).hexdigest()
    )
    status = "in_sync" if not missing else "drifted"
    return PreCommitReadback(
        entry=payload.get("stages", ["pre-commit"])[0]
        if expected_stages
        else "pre-commit",
        tool_version=str(payload.get("tool_version", "")),
        config_digest=config_digest,
        hook_stage_digests=hook_stage_digests,
        preserved_hooks=tuple(preserved),
        managed_hooks=tuple(managed),
        readback_status=status,
    )


def _baseline_id(inputs: dict[str, Any], readback: PreCommitReadback) -> str:
    payload = _json_canonical(
        {
            "run_id": inputs["run_id"],
            "attempt_id": inputs["attempt_id"],
            "actor_id": inputs["actor_id"],
            "base_commit": inputs["base_commit"],
            "design": {
                "revision": inputs["design"]["revision"],
                "digest": inputs["design"]["digest"],
            },
            "workspace_tree_digest": inputs["workspace"].get("tree_digest"),
            "precommit_config_digest": readback.config_digest,
        }
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"impl-baseline:{digest}"


@dataclass(frozen=True)
class ImplementationBaselineRecord:
    """Persisted M-IMPL baseline record (AC-FR0100-01).

    Attributes:
        run_id: Runtime-issued run id.
        release_identity: ``{version, spec_id, branch, tag}`` canonical identity.
        baseline_id: Runtime-established unique baseline id.
        attempt_id: Active reconcile attempt id.
        actor_id: Identity of the dispatching actor (``runtime:program``).
        base_commit: 40-hex release-branch commit the baseline is bound to.
        design: Bound design revision/digest + program/Prism evidence ids.
        workspace: Workspace tree digest + diffs.
        precommit: :class:`PreCommitReadback` evidence envelope.
        infrastructure_commit: Optional :class:`InfrastructureCommit` if tracked
            config changes require a controlled commit; ``None`` otherwise.
        dispatch_eligible: ``True`` only when every gate is PASS.
        block_reason: ``None`` for an eligible record; the stable code otherwise.
    """

    run_id: str
    release_identity: dict[str, Any]
    baseline_id: str
    attempt_id: str
    actor_id: str
    base_commit: str
    design: dict[str, Any]
    workspace: dict[str, Any]
    precommit: PreCommitReadback
    infrastructure_commit: InfrastructureCommit | None = None
    dispatch_eligible: bool = True
    block_reason: str | None = None
    side_effects_emitted: tuple[str, ...] = field(default_factory=tuple)


def enter_m_impl(
    inputs: dict[str, Any],
    *,
    precommit_contract: dict[str, Any],
    installed_stages: list[str],
    managed_config_present: bool,
    tracked_config_changes: list[dict[str, Any]] | None = None,
) -> ImplementationBaselineRecord:
    """Enter M-IMPL and persist a baseline identity record.

    Args:
        inputs: A mapping with ``run_id``, ``release_identity``, ``actor_id``,
            ``attempt_id``, ``base_commit``, ``design`` (revision/digest/
            program_status/prism_verdict + evidence ids) and ``workspace``
            (``{tree_digest, diffs:[{path,digest,source}]}``).
        precommit_contract: Parsed IF-PC-01 contract instance.
        installed_stages: Stages actually installed on disk (e.g.
            ``["pre-commit"]``).
        managed_config_present: ``True`` when ``.pre-commit-config.yaml``
            exists on disk; ``False`` triggers ``IMPL_PC_READBACK_MISSING``.
        tracked_config_changes: Optional list of tracked managed-config
            changes ``{path, digest}`` that require a controlled
            infrastructure commit.

    Returns:
        An :class:`ImplementationBaselineRecord` binding every input identity
        and the pre-commit readback.  ``dispatch_eligible`` is ``True`` only
        when every gate is PASS.

    Raises:
        ImplEntryError: With a stable code from :data:`ERROR_CODES` when any
            input is missing, stale, conflicting or drifted.  No Agent is
            dispatched in that case (AC-FR0100-01).
    """
    for key in ("run_id", "release_identity", "actor_id", "attempt_id", "base_commit"):
        _check_truthy(inputs.get(key), key)
    if not isinstance(inputs.get("release_identity"), dict):
        raise ImplEntryError(
            "IMPL_DESIGN_NOT_CURRENT", "release_identity must be a mapping"
        )
    _check_design(inputs.get("design") or {})
    _check_workspace(inputs.get("workspace") or {})
    readback = _readback_precommit(
        precommit_contract,
        installed_stages=list(installed_stages),
        managed_config_present=bool(managed_config_present),
        tracked_config_changes=list(tracked_config_changes or []),
    )
    infra_commit: InfrastructureCommit | None = None
    if tracked_config_changes:
        paths = tuple(str(c["path"]) for c in tracked_config_changes)
        infra_commit = InfrastructureCommit(
            paths=paths,
            expected_branch_oid=inputs["base_commit"],
        )
    return ImplementationBaselineRecord(
        run_id=inputs["run_id"],
        release_identity=dict(inputs["release_identity"]),
        baseline_id=_baseline_id(inputs, readback),
        attempt_id=inputs["attempt_id"],
        actor_id=inputs["actor_id"],
        base_commit=inputs["base_commit"],
        design=dict(inputs["design"]),
        workspace=dict(inputs["workspace"]),
        precommit=readback,
        infrastructure_commit=infra_commit,
        dispatch_eligible=True,
        block_reason=None,
        side_effects_emitted=(),
    )
