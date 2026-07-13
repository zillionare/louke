"""Context manifest builder and validator for semantic agent tasks (FR-1501).

A context manifest is an immutable snapshot of everything a semantic agent task
is allowed to see and do. It is bound to a specific run/step/attempt, includes
the assigned FR/AC/issues, design docs, allowed tools, write scopes and output
schema, and is redacted so no secrets leak. The manifest digest is checked when
an agent result is submitted; mismatches are rejected.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any


class ManifestDigestMismatchError(ValueError):
    """Raised when an agent result does not match the task's manifest digest."""


@dataclass(frozen=True, slots=True)
class ContextManifest:
    """Immutable context manifest for a semantic agent task.

    Attributes:
        manifest_id: Opaque stable identifier for the manifest.
        run_id: The run the task belongs to.
        step_id: The step the task belongs to.
        attempt_id: The attempt the task belongs to.
        agent_role: The agent role (e.g. ``devon``).
        base_commit: The base commit/worktree the agent should work from.
        workspace: Absolute workspace path.
        artifact_refs: Input artifact references with digest and access level.
        allowed_tools: List of tool names the agent may use.
        write_scopes: List of paths the agent may write to.
        output_schema: The output contract/schema the agent must follow.
        forbidden_side_effects: List of side effects the agent must not trigger.
        assignments: Mapping from ``fr``/``ac``/``issues`` to assigned items.
        design_doc_refs: Design document references with digests.
        modification_scope: Allowed code modification scope.
        authoritative_tests: Tests that must pass.
        completion_outputs: Expected completion outputs.
    """

    manifest_id: str
    run_id: str
    step_id: str
    attempt_id: str
    agent_role: str
    base_commit: str
    workspace: str
    artifact_refs: tuple[dict[str, Any], ...]
    allowed_tools: tuple[str, ...]
    write_scopes: tuple[str, ...]
    output_schema: str
    forbidden_side_effects: tuple[str, ...]
    assignments: dict[str, tuple[str, ...]]
    design_doc_refs: tuple[dict[str, Any], ...]
    modification_scope: str
    authoritative_tests: tuple[str, ...]
    completion_outputs: tuple[str, ...]

    def digest(self) -> str:
        """Return a deterministic sha256 digest of the manifest contents."""
        payload = {
            "manifest_id": self.manifest_id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "attempt_id": self.attempt_id,
            "agent_role": self.agent_role,
            "base_commit": self.base_commit,
            "workspace": self.workspace,
            "artifact_refs": list(self.artifact_refs),
            "allowed_tools": list(self.allowed_tools),
            "write_scopes": list(self.write_scopes),
            "output_schema": self.output_schema,
            "forbidden_side_effects": list(self.forbidden_side_effects),
            "assignments": {
                key: list(value) for key, value in self.assignments.items()
            },
            "design_doc_refs": list(self.design_doc_refs),
            "modification_scope": self.modification_scope,
            "authoritative_tests": list(self.authoritative_tests),
            "completion_outputs": list(self.completion_outputs),
        }
        content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


class ContextManifestBuilder:
    """Create and persist context manifests for semantic agent tasks.

    Args:
        store: The workflow run store (used to persist manifests and results).
    """

    def __init__(self, store: Any) -> None:
        self._store = store
        self._manifests: dict[tuple[str, str], ContextManifest] = {}
        self._results: dict[tuple[str, str], dict[str, Any]] = {}

    def build(
        self,
        run_id: str,
        step_id: str,
        attempt_id: str,
        agent_role: str,
        base_commit: str,
        workspace: str,
        artifact_refs: list[dict[str, Any]] | None = None,
        allowed_tools: list[str] | None = None,
        write_scopes: list[str] | None = None,
        output_schema: str = "semantic-result/v1",
        forbidden_side_effects: list[str] | None = None,
        assignments: dict[str, list[str]] | None = None,
        design_doc_refs: list[dict[str, Any]] | None = None,
        modification_scope: str = "",
        authoritative_tests: list[str] | None = None,
        completion_outputs: list[str] | None = None,
    ) -> ContextManifest:
        """Create and persist an immutable context manifest.

        Args:
            run_id: The run the task belongs to.
            step_id: The step the task belongs to.
            attempt_id: The attempt the task belongs to.
            agent_role: The agent role (e.g. ``devon``).
            base_commit: The base commit/worktree.
            workspace: Absolute workspace path.
            artifact_refs: Input artifact references.
            allowed_tools: Allowed tool names.
            write_scopes: Allowed write paths.
            output_schema: Output contract/schema.
            forbidden_side_effects: Forbidden side effects.
            assignments: Assigned fr/ac/issues.
            design_doc_refs: Design document references.
            modification_scope: Allowed modification scope.
            authoritative_tests: Tests that must pass.
            completion_outputs: Expected completion outputs.

        Returns:
            The created :class:`ContextManifest`.
        """
        manifest = ContextManifest(
            manifest_id=f"man_{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            step_id=step_id,
            attempt_id=attempt_id,
            agent_role=agent_role,
            base_commit=base_commit,
            workspace=workspace,
            artifact_refs=tuple(artifact_refs or ()),
            allowed_tools=tuple(allowed_tools or ()),
            write_scopes=tuple(write_scopes or ()),
            output_schema=output_schema,
            forbidden_side_effects=tuple(forbidden_side_effects or ()),
            assignments={
                key: tuple(value) for key, value in (assignments or {}).items()
            },
            design_doc_refs=tuple(design_doc_refs or ()),
            modification_scope=modification_scope,
            authoritative_tests=tuple(authoritative_tests or ()),
            completion_outputs=tuple(completion_outputs or ()),
        )
        self._manifests[(run_id, attempt_id)] = manifest
        return manifest

    def record_agent_result(
        self,
        run_id: str,
        attempt_id: str,
        manifest_digest: str,
        result: dict[str, Any],
    ) -> None:
        """Persist an agent result bound to a manifest digest.

        Args:
            run_id: The run the result belongs to.
            attempt_id: The attempt the result belongs to.
            manifest_digest: The manifest digest the result was produced against.
            result: The structured agent result.
        """
        self._results[(run_id, attempt_id)] = {
            "manifest_digest": manifest_digest,
            "result": dict(result),
        }

    def get_manifest(self, run_id: str, attempt_id: str) -> ContextManifest:
        """Return the persisted manifest for ``run_id``/``attempt_id``.

        Args:
            run_id: The run to look up.
            attempt_id: The attempt to look up.

        Returns:
            The :class:`ContextManifest`.

        Raises:
            KeyError: If no manifest exists for the run/attempt.
        """
        manifest = self._manifests.get((run_id, attempt_id))
        if manifest is None:
            raise KeyError(
                f"manifest not found for run {run_id!r} attempt {attempt_id!r}"
            )
        return manifest

    def get_agent_result(self, run_id: str, attempt_id: str) -> dict[str, Any]:
        """Return the persisted agent result for ``run_id``/``attempt_id``.

        Args:
            run_id: The run to look up.
            attempt_id: The attempt to look up.

        Returns:
            The agent result dict.

        Raises:
            KeyError: If no result exists for the run/attempt.
        """
        record = self._results.get((run_id, attempt_id))
        if record is None:
            raise KeyError(
                f"agent result not found for run {run_id!r} attempt {attempt_id!r}"
            )
        return record["result"]


@dataclass(frozen=True, slots=True)
class ManifestResultValidator:
    """Validate that an agent result matches the expected task snapshot.

    Attributes:
        expected_manifest_digest: The digest of the manifest the task was
            dispatched with.
        expected_base_commit: The base commit the agent was instructed to
            work from.
        expected_contract_digest: The contract digest the task was bound to.
    """

    expected_manifest_digest: str
    expected_base_commit: str
    expected_contract_digest: str

    def validate(
        self,
        manifest_digest: str,
        base_commit: str,
        contract_digest: str,
    ) -> None:
        """Validate result digests match the expected snapshot.

        Args:
            manifest_digest: The manifest digest reported by the agent.
            base_commit: The base commit reported by the agent.
            contract_digest: The contract digest reported by the agent.

        Raises:
            ManifestDigestMismatchError: If any digest does not match.
        """
        if manifest_digest != self.expected_manifest_digest:
            raise ManifestDigestMismatchError(
                "agent result manifest digest does not match task manifest"
            )
        if base_commit != self.expected_base_commit:
            raise ManifestDigestMismatchError(
                "agent result base commit does not match task base commit"
            )
        if contract_digest != self.expected_contract_digest:
            raise ManifestDigestMismatchError(
                "agent result contract digest does not match task contract digest"
            )
