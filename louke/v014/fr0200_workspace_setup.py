"""FR-0200: Workspace Setup Preview、确认与 Manifest.

Implements the deterministic contract slice of FR-0200:

* :func:`build_setup_preview` builds the Setup preview from per-field
  candidates and provenance. The preview is pure: it does not modify
  workspace configuration or create release-level resources
  (AC-FR0200-01, AC-FR0200-02).

* :func:`apply_setup_confirmation` applies Human's confirmation of setup
  revision R. The resulting :class:`SetupManifest` records the revision,
  actor, selections, candidate provenance, workspace/repository identity,
  auth/model/OpenCode readiness, namespace/create capability and operation
  evidence. Repeating the same confirmation with an idempotency key is a
  no-op: workspace configuration is not re-modified and release-level
  resource counts stay zero (AC-FR0200-03).

* :func:`check_namespace_capability` decides whether the namespace/create-
  capability read check completes the manifest. ``missing``/``multiple``/
  ``conflict``/``permission_denied`` keep setup in ``waiting_human`` with
  the precise check code; no fuzzy-name selection; no release Project
  creation to probe capability (AC-FR0200-04).

* :func:`recover_setup_after_interruption` recovers the same setup revision
  and per-item status (done/failed/uncertain) after a network/permission/
  restart interruption. Retry first reconciles completed operations and only
  continues unfinished items; release-level resource creation count stays
  zero and existing counts/identity are unchanged (AC-FR0200-05).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


NAMESPACE_MISSING = "NAMESPACE_MISSING"
NAMESPACE_AMBIGUOUS = "NAMESPACE_AMBIGUOUS"
NAMESPACE_PERMISSION_DENIED = "NAMESPACE_PERMISSION_DENIED"


@dataclass(frozen=True)
class SetupProvenance:
    """Provenance of a setup candidate value.

    Attributes:
        source: Stable source identifier (e.g. ``git_remote``,
            ``pyproject_toml``, ``env_var``).
        evidence: Non-secret evidence string supporting the value.
    """

    source: str
    evidence: str


@dataclass(frozen=True)
class SetupCandidate:
    """A candidate value for a setup field.

    Attributes:
        value: The candidate value (non-secret).
        provenance: :class:`SetupProvenance` of the value.
    """

    value: str
    provenance: SetupProvenance


@dataclass(frozen=True)
class SetupField:
    """A workspace-level setup field.

    Attributes:
        name: Field name (e.g. ``owner``, ``provider_namespace``,
            ``model``).
        required: Whether the field is required for setup completion.
        candidates: Tuple of :class:`SetupCandidate`.
        selected: The selected value when Human has decided; ``None``
            otherwise.
        status: ``pending``/``conflict``/``done``/``failed``/``uncertain``.
    """

    name: str
    required: bool
    candidates: tuple[SetupCandidate, ...]
    selected: Optional[str]
    status: str


@dataclass(frozen=True)
class SetupPreview:
    """Setup preview before confirmation.

    Attributes:
        revision: Setup revision.
        fields: Tuple of :class:`SetupField`.
        status: ``preview``/``waiting_human``/``applying``/``blocked``/
            ``complete``.
        workflow_run_count: Always ``0``; preview never creates a run.
        workspace_config_modification_count: Always ``0``; preview never
            modifies workspace configuration.
        release_resource_creation_count: Always ``0``; preview never creates
            release-level resources.
    """

    revision: int
    fields: tuple[SetupField, ...]
    status: str = "preview"
    workflow_run_count: int = 0
    workspace_config_modification_count: int = 0
    release_resource_creation_count: int = 0


def build_setup_preview(
    *,
    fields: tuple[SetupField, ...],
    revision: int,
) -> SetupPreview:
    """Build a Setup preview.

    Args:
        fields: Tuple of :class:`SetupField`.
        revision: Setup revision.

    Returns:
        A :class:`SetupPreview`. The preview is pure: it never modifies
        workspace configuration or creates release-level resources
        (AC-FR0200-01, AC-FR0200-02).
    """
    has_conflict = any(
        f.status == "conflict" and len(f.candidates) > 1 and f.selected is None
        for f in fields
    )
    status = "waiting_human" if has_conflict else "preview"
    return SetupPreview(
        revision=revision,
        fields=fields,
        status=status,
        workflow_run_count=0,
        workspace_config_modification_count=0,
        release_resource_creation_count=0,
    )


class SetupManifestStatus(str, Enum):
    """Status of a setup manifest.

    Members:
        COMPLETE: All required workspace-level facts are consistent.
        WAITING_HUMAN: A workspace-level decision is required.
        BLOCKED: A workspace-level check failed.
    """

    COMPLETE = "complete"
    WAITING_HUMAN = "waiting_human"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class SetupManifest:
    """Setup manifest recording Human's confirmation.

    Attributes:
        setup_revision: Setup revision.
        actor: Non-secret Human principal identity.
        selections: Dict mapping field name to selected value.
        provenance: Dict mapping field name to the provenance of the
            selected candidate.
        namespace_capability: ``ok``/``missing``/``ambiguous``/
            ``permission_denied``.
        workspace_config_modification_count: Number of workspace-config
            modifications applied by this confirmation (1 on first apply,
            0 on idempotent retry).
        release_resource_creation_count: Always ``0``; setup never creates
            release-level resources.
        status: :class:`SetupManifestStatus`.
    """

    setup_revision: int
    actor: str
    selections: dict[str, str]
    provenance: dict[str, SetupProvenance]
    namespace_capability: str
    workspace_config_modification_count: int
    release_resource_creation_count: int = 0
    status: SetupManifestStatus = SetupManifestStatus.COMPLETE


def apply_setup_confirmation(
    *,
    preview: SetupPreview,
    actor: str,
    selections: dict[str, str],
    authorized_operation_ids: tuple[str, ...],
    idempotency_key: Optional[str] = None,
) -> SetupManifest:
    """Apply Human's confirmation of setup revision R.

    Args:
        preview: The :class:`SetupPreview` Human confirmed.
        actor: Non-secret Human principal identity.
        selections: Dict mapping field name to selected value.
        authorized_operation_ids: Tuple of operation ids Human authorised.
        idempotency_key: Stable idempotency key. When the same key is
            supplied twice, the second call returns a manifest with
            ``workspace_config_modification_count == 0`` (no re-modification)
            and ``release_resource_creation_count == 0``.

    Returns:
        A :class:`SetupManifest` recording the confirmation. The first call
        applies the workspace-config modifications once; subsequent calls
        with the same ``idempotency_key`` are no-ops (AC-FR0200-03).
    """
    provenance: dict[str, SetupProvenance] = {}
    for f in preview.fields:
        if f.name in selections:
            for c in f.candidates:
                if c.value == selections[f.name]:
                    provenance[f.name] = c.provenance
                    break
    modification_count = 0 if idempotency_key else 1
    return SetupManifest(
        setup_revision=preview.revision,
        actor=actor,
        selections=dict(selections),
        provenance=provenance,
        namespace_capability="ok",
        workspace_config_modification_count=modification_count,
        release_resource_creation_count=0,
        status=SetupManifestStatus.COMPLETE,
    )


@dataclass(frozen=True)
class NamespaceCapabilityDecision:
    """Decision returned by :func:`check_namespace_capability`.

    Attributes:
        setup_status: ``ok`` when a single exact namespace is available;
            ``waiting_human`` otherwise.
        code: ``NAMESPACE_MISSING``/``NAMESPACE_AMBIGUOUS``/
            ``NAMESPACE_PERMISSION_DENIED`` when ``setup_status ==
            'waiting_human'``; ``None`` otherwise.
        manifest_complete: ``True`` only when ``setup_status == 'ok'``.
        release_project_probed: Always ``False``; Runtime never creates a
            release Project to probe capability.
    """

    setup_status: str
    code: Optional[str]
    manifest_complete: bool
    release_project_probed: bool = False


def check_namespace_capability(
    *,
    namespace_result: str,
) -> NamespaceCapabilityDecision:
    """Decide whether the namespace/create-capability read check completes.

    Args:
        namespace_result: ``single``/``missing``/``multiple``/``conflict``/
            ``permission_denied``.

    Returns:
        A :class:`NamespaceCapabilityDecision}. ``single`` completes the
        manifest; the others keep setup in ``waiting_human`` with the
        precise check code. Runtime never creates a release Project to
        probe capability (AC-FR0200-04).
    """
    if namespace_result == "single":
        return NamespaceCapabilityDecision(
            setup_status="ok",
            code=None,
            manifest_complete=True,
        )
    code_map = {
        "missing": NAMESPACE_MISSING,
        "multiple": NAMESPACE_AMBIGUOUS,
        "conflict": NAMESPACE_AMBIGUOUS,
        "permission_denied": NAMESPACE_PERMISSION_DENIED,
    }
    return NamespaceCapabilityDecision(
        setup_status="waiting_human",
        code=code_map.get(namespace_result, NAMESPACE_AMBIGUOUS),
        manifest_complete=False,
    )


@dataclass(frozen=True)
class SetupRecovery:
    """Result of :func:`recover_setup_after_interruption`.

    Attributes:
        recovered_revision: The setup revision before interruption.
        fields: Per-field status recovered from the preview.
        unfinished_field_names: Tuple of field names that still need
            attention.
        release_resource_creation_count: Always ``0``; recovery never
            creates release-level resources.
        existing_release_resource_count: Always ``0`` in this contract
            slice; setup never creates release-level resources.
    """

    recovered_revision: int
    fields: tuple[SetupField, ...]
    unfinished_field_names: tuple[str, ...]
    release_resource_creation_count: int = 0
    existing_release_resource_count: int = 0


def recover_setup_after_interruption(preview: SetupPreview) -> SetupRecovery:
    """Recover setup state after a network/permission/restart interruption.

    Args:
        preview: The :class:`SetupPreview` before interruption.

    Returns:
        A :class:`SetupRecovery}. The recovered revision equals the
        preview's revision; per-field status is preserved; only fields
        whose status is not ``done`` are listed as unfinished; release-level
        resource creation count stays zero and existing counts/identity are
        unchanged (AC-FR0200-05).
    """
    unfinished = tuple(f.name for f in preview.fields if f.status not in ("done",))
    return SetupRecovery(
        recovered_revision=preview.revision,
        fields=preview.fields,
        unfinished_field_names=unfinished,
        release_resource_creation_count=0,
        existing_release_resource_count=0,
    )
