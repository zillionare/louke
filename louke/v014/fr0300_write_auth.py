"""FR-0300: design write authorisation & artifact ownership.

Runtime issues Archer a single-write authorisation manifest listing the
editable design docs, machine contracts and affected canonical prompts, and
forbidding Git/stage/GitHub side effects.  Each round attributes diffs to a
specific actor; out-of-scope or unattributed changes cannot be silently
absorbed into the design baseline (AC-FR0300-01).
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass

ERROR_CODES = (
    "WRITE_SCOPE_DENIED",
    "DESIGN_DIFF_UNATTRIBUTED",
    "DESIGN_DIFF_DIGEST_MISMATCH",
)

_DEFAULT_FORBIDDEN_EFFECTS = (
    "git-side-effect",
    "stage-side-effect",
    "github-side-effect",
    "active-opencode-write",
    "business-code-write",
    "test-code-write",
    "project-toml-write",
    "review-artifact-write",
    "commit",
    "push",
    "dispatch",
    "activation",
    "stage-progression",
    "runtime-state-write",
    "external-side-effect",
)

_FORBIDDEN_PATH_PREFIXES = (
    ".git/",
    ".github/workflows/ci.yml",  # user CI - cannot be modified by Archer
    ".github/workflows/release.yml",  # user release - cannot be modified
)


class DesignWriteAuthError(Exception):
    """A fail-closed design-write rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def _is_under_forbidden_prefix(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in _FORBIDDEN_PATH_PREFIXES)


def _matches_any_glob(path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


@dataclass(frozen=True)
class WriteAuthorisationManifest:
    """Single-write authorisation manifest issued to Archer (AC-FR0300-01).

    Attributes:
        spec_id: Spec identifier the manifest is scoped to.
        design_doc_paths: Explicit list of editable design documents.
        contract_paths: Explicit list of editable contract instance files.
        prompt_paths: Explicit list of editable canonical prompt sources.
        extra_globs: Additional allowed-path globs (e.g. ``design-artifacts/**``).
        forbidden_effects: Side effects Archer must not trigger.
    """

    spec_id: str
    design_doc_paths: tuple[str, ...]
    contract_paths: tuple[str, ...]
    prompt_paths: tuple[str, ...]
    extra_globs: tuple[str, ...] = ()
    forbidden_effects: tuple[str, ...] = _DEFAULT_FORBIDDEN_EFFECTS

    def allowed_paths(self) -> tuple[str, ...]:
        """Return the explicit allowed-path list (excluding globs)."""
        return self.design_doc_paths + self.contract_paths + self.prompt_paths

    def to_json(self) -> str:
        """Serialise to canonical JSON for the task-manifest allowlist."""
        payload = {
            "spec_id": self.spec_id,
            "design_doc_paths": list(self.design_doc_paths),
            "contract_paths": list(self.contract_paths),
            "prompt_paths": list(self.prompt_paths),
            "extra_globs": list(self.extra_globs),
            "forbidden_effects": list(self.forbidden_effects),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class DiffAttribution:
    """A diff attribution record (AC-FR0300-01).

    Attributes:
        path: Edited path relative to the workspace root.
        actor_id: Identity of the editing actor (e.g. ``archer:att-1``).
        base_digest: ``sha256:<hex>`` of the file bytes before the edit.
        current_digest: ``sha256:<hex>`` of the file bytes after the edit.
        in_scope: ``True`` if the edit falls within the authorised write set.
        block_reason: ``None`` when in-scope, otherwise a stable code from
            :data:`ERROR_CODES`.
    """

    path: str
    actor_id: str
    base_digest: str
    current_digest: str
    in_scope: bool
    block_reason: str | None = None


def build_write_manifest(
    *,
    spec_id: str,
    design_doc_paths: list[str],
    contract_paths: list[str],
    prompt_paths: list[str],
    extra_globs: list[str] | None = None,
    forbidden_effects: tuple[str, ...] = _DEFAULT_FORBIDDEN_EFFECTS,
) -> WriteAuthorisationManifest:
    """Build a single-write authorisation manifest for Archer.

    Args:
        spec_id: Spec identifier the manifest is scoped to.
        design_doc_paths: Editable design documents (test-plan/architecture/
            interfaces).
        contract_paths: Editable contract instance candidate files.
        prompt_paths: Editable canonical prompt sources.
        extra_globs: Additional allowed-path globs (e.g.
            ``design-artifacts/**``).
        forbidden_effects: Side effects Archer must not trigger; defaults to
            :data:`_DEFAULT_FORBIDDEN_EFFECTS`.

    Returns:
        A :class:`WriteAuthorisationManifest` instance.
    """
    return WriteAuthorisationManifest(
        spec_id=spec_id,
        design_doc_paths=tuple(design_doc_paths),
        contract_paths=tuple(contract_paths),
        prompt_paths=tuple(prompt_paths),
        extra_globs=tuple(extra_globs or ()),
        forbidden_effects=forbidden_effects,
    )


def is_diff_in_scope(manifest: WriteAuthorisationManifest, path: str) -> bool:
    """Return ``True`` if ``path`` falls within the authorised write set."""
    if _is_under_forbidden_prefix(path):
        return False
    if path in manifest.allowed_paths():
        return True
    if _matches_any_glob(path, manifest.extra_globs):
        return True
    return False


def attribute_diff(
    manifest: WriteAuthorisationManifest,
    *,
    path: str,
    actor_id: str,
    base_digest: str,
    current_digest: str,
) -> DiffAttribution:
    """Attribute a diff to ``actor_id`` and verify scope.

    Args:
        manifest: The authorisation manifest issued for this round.
        path: Edited path relative to the workspace root.
        actor_id: Identity of the editing actor.
        base_digest: ``sha256:<hex>`` of the file bytes before the edit.
        current_digest: ``sha256:<hex>`` of the file bytes after the edit.

    Returns:
        A :class:`DiffAttribution` with ``in_scope=True`` when the diff falls
        within the authorised write set.

    Raises:
        DesignWriteAuthError: With ``WRITE_SCOPE_DENIED`` if the path is
            out-of-scope, the actor id is empty, or the path is a forbidden
            Git/Stage/GitHub side-effect target.
    """
    if not actor_id:
        raise DesignWriteAuthError(
            "DESIGN_DIFF_UNATTRIBUTED",
            f"diff at {path} has no actor_id; cannot be absorbed into baseline",
        )
    if _is_under_forbidden_prefix(path):
        raise DesignWriteAuthError(
            "WRITE_SCOPE_DENIED",
            f"path {path} is a forbidden Git/Stage/GitHub side-effect target",
        )
    if not is_diff_in_scope(manifest, path):
        raise DesignWriteAuthError(
            "WRITE_SCOPE_DENIED",
            f"path {path} is outside the authorised write set",
        )
    for digest in (base_digest, current_digest):
        if (
            not digest
            or not digest.startswith("sha256:")
            or len(digest) != len("sha256:") + 64
        ):
            raise DesignWriteAuthError(
                "DESIGN_DIFF_DIGEST_MISMATCH",
                f"digest {digest!r} at {path} is not a valid sha256 digest",
            )
    return DiffAttribution(
        path=path,
        actor_id=actor_id,
        base_digest=base_digest,
        current_digest=current_digest,
        in_scope=True,
        block_reason=None,
    )
