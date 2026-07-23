"""FR-0100: M-DESIGN entry & revision identity.

The Runtime may only enter ``M-DESIGN`` when the approved requirements
digests, base commit and host-project facts snapshot are all current.  Entry
must persist a record binding ``run``/``release``/``revision``/``attempt``/
``actor`` plus every input identity; any missing, stale or conflicting input
blocks Archer dispatch with a stable fail-closed reason.  No Git/GitHub or
stage side effects are emitted (AC-FR0100-01).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ERROR_CODES = (
    "DESIGN_INPUT_MISSING",
    "DESIGN_INPUT_STALE",
    "BASE_COMMIT_CONFLICT",
    "WRITE_SCOPE_DENIED",
)

_REQUIRED_REQUIREMENT_KEYS = ("story", "spec", "acceptance")


class DesignEntryError(Exception):
    """A fail-closed M-DESIGN entry rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _check_truthy(value: Any, key: str) -> None:
    if value is None or value == "":
        raise DesignEntryError("DESIGN_INPUT_MISSING", f"missing input: {key}")


def _check_requirements(reqs: dict[str, str]) -> None:
    for key in _REQUIRED_REQUIREMENT_KEYS:
        digest = reqs.get(key)
        if not digest or not digest.startswith("sha256:"):
            raise DesignEntryError(
                "DESIGN_INPUT_MISSING",
                f"missing approval digest: requirements.{key}",
            )


def _check_digest_format(digest: str, key: str) -> None:
    if (
        not digest
        or not digest.startswith("sha256:")
        or len(digest) != len("sha256:") + 64
    ):
        raise DesignEntryError("DESIGN_INPUT_MISSING", f"invalid digest: {key}")


def _load_candidate_manifest(spec_root: Path) -> dict[str, Any]:
    path = (
        Path(spec_root) / "design-artifacts" / "design-artifact-manifest.candidate.json"
    )
    if not path.is_file():
        raise DesignEntryError(
            "DESIGN_INPUT_MISSING",
            f"candidate manifest not found: {path}",
        )
    return json.loads(path.read_bytes())


def _load_facts_snapshot(spec_root: Path) -> dict[str, Any]:
    path = (
        Path(spec_root)
        / "design-artifacts"
        / "inputs"
        / "host-project-facts.snapshot.json"
    )
    if not path.is_file():
        raise DesignEntryError(
            "DESIGN_INPUT_MISSING",
            f"host-project-facts snapshot not found: {path}",
        )
    return json.loads(path.read_bytes())


def _check_against_candidate(inputs: dict[str, Any], spec_root: Path) -> None:
    """Verify inputs against the candidate manifest and facts snapshot.

    Raises ``DESIGN_INPUT_STALE`` if the caller-supplied facts/task digests do
    not match the candidate artifacts, or ``BASE_COMMIT_CONFLICT`` if the
    base commit does not equal the one recorded in the facts snapshot.
    """
    manifest = _load_candidate_manifest(spec_root)
    facts_snapshot = _load_facts_snapshot(spec_root)
    facts_digest = next(
        (
            a["digest"]
            for a in manifest.get("input_artifacts", [])
            if a.get("kind") == "host-project-facts-snapshot"
        ),
        None,
    )
    task_digest = next(
        (
            a["digest"]
            for a in manifest.get("input_artifacts", [])
            if a.get("kind") == "archer-author-task-manifest"
        ),
        None,
    )
    if facts_digest and inputs.get("project_facts_digest") != facts_digest:
        raise DesignEntryError(
            "DESIGN_INPUT_STALE",
            "project_facts_digest does not match the candidate snapshot",
        )
    if task_digest and inputs.get("task_manifest_digest") != task_digest:
        raise DesignEntryError(
            "DESIGN_INPUT_STALE",
            "task_manifest_digest does not match the candidate manifest",
        )
    facts_base_commit = facts_snapshot.get("base_commit")
    if facts_base_commit and inputs.get("base_commit") != facts_base_commit:
        raise DesignEntryError(
            "BASE_COMMIT_CONFLICT",
            f"base_commit {inputs.get('base_commit')} != facts {facts_base_commit}",
        )


def _check_against_prior_attempts(
    inputs: dict[str, Any], prior: Iterable["DesignRevisionRecord"]
) -> None:
    attempt_id = inputs.get("attempt_id")
    for prior_record in prior:
        if prior_record.attempt_id == attempt_id:
            raise DesignEntryError(
                "DESIGN_INPUT_STALE",
                f"attempt {attempt_id} already dispatched as "
                f"{prior_record.design_revision_id}; create a new attempt",
            )


def _revision_id(inputs: dict[str, Any]) -> str:
    """Compute a deterministic revision id from the bound inputs.

    The revision id is SHA-256 of the canonical compact-JSON over run/release/
    attempt/actor/requirements/base/facts/task-manifest, ensuring equal inputs
    produce equal revision ids (AC-FR0100-01 determinism).
    """
    payload = json_canonical(
        {
            "run_id": inputs["run_id"],
            "release_identity": inputs["release_identity"],
            "attempt_id": inputs["attempt_id"],
            "actor_id": inputs["actor_id"],
            "requirements": inputs["requirements"],
            "base_commit": inputs["base_commit"],
            "project_facts_digest": inputs["project_facts_digest"],
            "task_manifest_digest": inputs["task_manifest_digest"],
        }
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"design-revision:{digest}"


def json_canonical(value: Any) -> str:
    """Return compact sorted-key JSON for deterministic digests."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class DesignRevisionRecord:
    """Persisted M-DESIGN revision record (AC-FR0100-01).

    Attributes:
        run_id: Runtime-issued run id.
        release_identity: ``{version, spec_id, branch, tag}`` canonical identity.
        design_revision_id: Runtime-established unique revision id.
        attempt_id: Active Archer attempt id.
        actor_id: Identity of the dispatching actor.
        requirements: ``{story, spec, acceptance}`` digests.
        base_commit: 40-hex git commit the revision is bound to.
        project_facts_digest: SHA-256 of the host-project-facts snapshot bytes.
        task_manifest_digest: SHA-256 of the Archer task manifest bytes.
        side_effects_emitted: Always empty - entry performs no side effects.
        block_reason: ``None`` for a successful record; the stable code if
            entry was blocked (use :class:`DesignEntryError` instead).
    """

    run_id: str
    release_identity: dict[str, Any]
    design_revision_id: str
    attempt_id: str
    actor_id: str
    requirements: dict[str, str]
    base_commit: str
    project_facts_digest: str
    task_manifest_digest: str
    side_effects_emitted: tuple[str, ...] = ()
    block_reason: str | None = None


def enter_m_design(
    inputs: dict[str, Any],
    *,
    spec_root: Path | None = None,
    prior_attempts: Iterable[DesignRevisionRecord] = (),
) -> DesignRevisionRecord:
    """Enter M-DESIGN and persist a revision identity record.

    Args:
        inputs: A mapping with ``run_id``, ``release_identity``, ``actor_id``,
            ``attempt_id``, ``requirements`` (``{story,spec,acceptance}``
            digests), ``base_commit``, ``project_facts_digest`` and
            ``task_manifest_digest``.
        spec_root: Optional path to the spec directory.  When provided the
            function loads the candidate manifest and host-project-facts
            snapshot and verifies the caller-supplied digests and base commit
            against them, fail-closed with ``DESIGN_INPUT_STALE`` or
            ``BASE_COMMIT_CONFLICT``.
        prior_attempts: Already-dispatched revision records for this run;
            duplicate attempt ids are rejected (AC-FR0100-01 freshness).

    Returns:
        A :class:`DesignRevisionRecord` binding every input identity.

    Raises:
        DesignEntryError: With a stable ``DESIGN_INPUT_MISSING``,
            ``DESIGN_INPUT_STALE`` or ``BASE_COMMIT_CONFLICT`` code when any
            input is missing, stale or conflicting.  No Archer task is
            dispatched in that case.
    """
    for key in ("run_id", "release_identity", "actor_id", "attempt_id"):
        _check_truthy(inputs.get(key), key)
    if not isinstance(inputs.get("release_identity"), dict):
        raise DesignEntryError(
            "DESIGN_INPUT_MISSING", "release_identity must be a mapping"
        )
    requirements = inputs.get("requirements")
    if not isinstance(requirements, dict):
        raise DesignEntryError("DESIGN_INPUT_MISSING", "requirements must be a mapping")
    _check_requirements(requirements)
    _check_digest_format(inputs.get("project_facts_digest", ""), "project_facts_digest")
    _check_digest_format(inputs.get("task_manifest_digest", ""), "task_manifest_digest")
    _check_truthy(inputs.get("base_commit"), "base_commit")
    if spec_root is not None:
        _check_against_candidate(inputs, spec_root)
    _check_against_prior_attempts(inputs, prior_attempts)
    return DesignRevisionRecord(
        run_id=inputs["run_id"],
        release_identity=dict(inputs["release_identity"]),
        design_revision_id=_revision_id(inputs),
        attempt_id=inputs["attempt_id"],
        actor_id=inputs["actor_id"],
        requirements=dict(requirements),
        base_commit=inputs["base_commit"],
        project_facts_digest=inputs["project_facts_digest"],
        task_manifest_digest=inputs["task_manifest_digest"],
        side_effects_emitted=(),
        block_reason=None,
    )
