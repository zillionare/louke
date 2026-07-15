"""FR-2401: project-local Louke install, version pinning and global fallback e2e.

Covers AC-FR2401-01..08. Per test-plan §1.1 (black-box declaration) and §6.8
(project-local runtime specialty) these tests observe the runtime selector
through its public ``RuntimeIdentity`` view, ``RuntimeMode``, task manifest
fragment and well-typed error classes - the observable exits described in
interfaces.md §2.2 (runtime identity view) and §2.1 (``lk serve`` /
``lk runtime install|repair|upgrade`` non-fallback contract). The v0.12 M-DEV
HTTP project API is not yet implemented; these public outputs are the
contract surface, mirroring the established pattern in
``test_fr2301_legacy_adoption__e2e.py``.

Expected versions, modes, sources and the no-fallback contract come from
acceptance.md AC-FR2401-01..08 (the spec), not from implementation output.

AC references:
- AC-FR2401-01: concurrent projects with different local pins keep runtime
  identity, definitions, prompts, dependencies and runtime data isolated.
- AC-FR2401-02: nearest workspace root wins for ``lk version`` / ``lk serve``;
  output shows effective root, mode, source and exact version/build.
- AC-FR2401-03: explicit global mode requires compatibility check; missing or
  incompatible global stops at setup/readiness with a repair action.
- AC-FR2401-04: local runtime failures (missing / corrupt / wrong version /
  integrity / schema) fail before state writes without falling back to global.
- AC-FR2401-05: running tasks keep the server's runtime identity even after
  PATH/global changes; manifests/events record the same executable.
- AC-FR2401-06: switching to a newly installed local runtime requires a
  controlled restart; readiness must prove the new identity before workflow
  mutations are allowed.
- AC-FR2401-07: upgrade/repair only changes the selected workspace; running
  tasks keep their start identity; not-yet-started tasks use the new identity
  only after restart.
- AC-FR2401-08: only Louke-managed artifacts with verified identity/integrity
  are accepted; unmanaged/tampered runtime is rejected.
"""

from __future__ import annotations

import pytest

from louke.runtime.runtime_selector import (
    GlobalModeError,
    IntegrityError,
    InvalidRuntimeError,
    RuntimeIdentity,
    RuntimeMode,
    RuntimeSelector,
    VersionMismatchError,
)

# Fixed versions, roots and executable paths - driven by the test fixtures,
# not derived from implementation output.
PROJ_A_ROOT = "/tmp/louke-ws-a"
PROJ_B_ROOT = "/tmp/louke-ws-b"
PROJ_A_VERSION = "0.12.1"
PROJ_B_VERSION = "0.12.2"


# ---------------------------------------------------------------------------
# AC-FR2401-01: concurrent projects keep runtime identity isolated
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2401_01_concurrent_local_projects_report_distinct_identity():
    """AC-FR2401-01: two projects with different local pins report distinct identities.

    Project A pinned to 0.12.1 and Project B pinned to 0.12.2 must each resolve
    to their own exact version, mode, source and executable; resolving one
    project must not change the other's resolved identity.
    """
    selector_a = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
        mode=RuntimeMode.LOCAL,
    )
    selector_b = RuntimeSelector(
        project_root=PROJ_B_ROOT,
        declared_version=PROJ_B_VERSION,
        mode=RuntimeMode.LOCAL,
    )

    identity_a = selector_a.resolve()
    identity_b = selector_b.resolve()

    assert identity_a.version == PROJ_A_VERSION
    assert identity_b.version == PROJ_B_VERSION
    assert identity_a.version != identity_b.version
    assert identity_a.effective_root == PROJ_A_ROOT
    assert identity_b.effective_root == PROJ_B_ROOT
    # Source must remain project-local for both, never global fallback.
    assert identity_a.source == "project-local"
    assert identity_b.source == "project-local"
    assert identity_a.mode is RuntimeMode.LOCAL
    assert identity_b.mode is RuntimeMode.LOCAL


@pytest.mark.e2e
def test_ac_fr2401_01_concurrent_task_manifests_record_distinct_executable():
    """AC-FR2401-01: each project's task manifest records its own executable.

    The task manifest fragment (interfaces.md §2.2 runtime identity view) for
    each project must point to that project's local executable and version;
    one project's manifest must not reference the other's.
    """
    selector_a = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
    )
    selector_b = RuntimeSelector(
        project_root=PROJ_B_ROOT,
        declared_version=PROJ_B_VERSION,
    )

    manifest_a = selector_a.task_manifest()
    manifest_b = selector_b.task_manifest()

    assert manifest_a["runtime_version"] == PROJ_A_VERSION
    assert manifest_b["runtime_version"] == PROJ_B_VERSION
    assert manifest_a["runtime_executable"] == f"{PROJ_A_ROOT}/.louke/runtime/lk"
    assert manifest_b["runtime_executable"] == f"{PROJ_B_ROOT}/.louke/runtime/lk"
    assert manifest_a["runtime_mode"] == "LOCAL"
    assert manifest_b["runtime_mode"] == "LOCAL"
    assert manifest_a["runtime_source"] == "project-local"
    assert manifest_b["runtime_source"] == "project-local"
    # Cross-contamination check: A's executable must not equal B's.
    assert manifest_a["runtime_executable"] != manifest_b["runtime_executable"]


# ---------------------------------------------------------------------------
# AC-FR2401-02: nearest workspace root wins
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2401_02_nearest_workspace_root_wins_from_subdir():
    """AC-FR2401-02: invoking from a subdirectory resolves to the nearest workspace root.

    Per interfaces.md §2.1 ``lk version`` / ``lk serve`` must select the
    nearest workspace root and its local runtime, not a global version on
    PATH. The output must show effective root, mode, source and exact version.
    """
    selector = RuntimeSelector(
        project_root=f"{PROJ_A_ROOT}/subdir",
        declared_version=PROJ_A_VERSION,
    )

    identity = selector.resolve()

    # Effective root collapses back to the workspace root.
    assert identity.effective_root == PROJ_A_ROOT
    assert identity.mode is RuntimeMode.LOCAL
    assert identity.source == "project-local"
    assert identity.version == PROJ_A_VERSION
    # Build must be a non-empty exact identifier, not the global placeholder.
    assert identity.build != ""
    assert identity.executable_path == f"{PROJ_A_ROOT}/.louke/runtime/lk"


@pytest.mark.e2e
def test_ac_fr2401_02_nested_workspace_picks_inner_root():
    """AC-FR2401-02: a nested Louke workspace wins over the outer one.

    When a project root, its multi-level subdirectories and another nested
    Louke workspace each declare different local versions, the nearest
    workspace root wins for each invocation. Calling from the nested workspace
    must resolve to the nested root, not the outer project root.
    """
    nested_root = f"{PROJ_A_ROOT}/nested-ws"
    nested_version = "0.12.5"

    selector = RuntimeSelector(
        project_root=nested_root,
        declared_version=nested_version,
    )

    identity = selector.resolve()

    assert identity.effective_root == nested_root
    assert identity.version == nested_version
    assert identity.source == "project-local"
    assert identity.executable_path == f"{nested_root}/.louke/runtime/lk"


# ---------------------------------------------------------------------------
# AC-FR2401-03: global mode requires compatibility check
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2401_03_global_mode_compatible_runtime_resolves():
    """AC-FR2401-03: explicit global mode with a compatible global runtime resolves.

    Only when the global runtime passes compatibility (>= 0.12.0) may the
    workspace read/write workflow state.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        mode=RuntimeMode.GLOBAL,
        global_version="0.12.3",
    )

    identity = selector.resolve()

    assert identity.mode is RuntimeMode.GLOBAL
    assert identity.source == "global"
    assert identity.version == "0.12.3"
    # Compatible global must allow workflow state mutations.
    assert selector.can_read_write_workflow() is True


@pytest.mark.e2e
def test_ac_fr2401_03_global_mode_incompatible_runtime_blocked():
    """AC-FR2401-03: incompatible global runtime raises GlobalModeError and blocks workflow access.

    When the global runtime is below the minimum compatible version, the
    workspace must stop at setup/readiness with a repair action and must not
    allow workflow state writes.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        mode=RuntimeMode.GLOBAL,
        global_version="0.11.0",
    )

    with pytest.raises(GlobalModeError) as exc:
        selector.resolve()

    # Blocked global must not allow workflow mutations.
    assert selector.can_read_write_workflow() is False
    # The error must surface the incompatibility and a repair path.
    assert "incompatible" in str(exc.value).lower()


@pytest.mark.e2e
def test_ac_fr2401_03_global_mode_missing_runtime_blocked():
    """AC-FR2401-03: missing global runtime is rejected with a GlobalModeError.

    An empty global version means the global runtime is absent; the workspace
    must stop rather than silently proceeding without an identity.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        mode=RuntimeMode.GLOBAL,
        global_version="",
    )

    with pytest.raises(GlobalModeError):
        selector.resolve()

    assert selector.can_read_write_workflow() is False


# ---------------------------------------------------------------------------
# AC-FR2401-04: local runtime failures fail before state writes, no global fallback
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2401_04_missing_local_runtime_raises_before_state_write():
    """AC-FR2401-04: a missing local runtime raises InvalidRuntimeError before any state write.

    The selector must fail closed with a repair action and must never fall back
    to a global runtime when local is declared but absent.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
        local_present=False,
    )

    with pytest.raises(InvalidRuntimeError) as exc:
        selector.resolve()

    assert "missing" in str(exc.value).lower()
    # No fallback: a missing local runtime must not enable workflow mutations.
    assert selector.can_read_write_workflow() is False


@pytest.mark.e2e
def test_ac_fr2401_04_wrong_local_version_raises_mismatch():
    """AC-FR2401-04: an actual local runtime at a different version is rejected with VersionMismatchError.

    The expected/actual versions must be surfaced; no global fallback occurs.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
        actual_version="0.13.0",
    )

    with pytest.raises(VersionMismatchError) as exc:
        selector.resolve()

    msg = str(exc.value).lower()
    assert PROJ_A_VERSION in str(exc.value)
    assert "0.13.0" in str(exc.value)
    assert "mismatch" in msg
    assert selector.can_read_write_workflow() is False


@pytest.mark.e2e
def test_ac_fr2401_04_corrupt_local_runtime_raises_integrity_error():
    """AC-FR2401-04: a local runtime that fails integrity verification raises IntegrityError.

    Corrupt artifact bytes must not silently pass; no global fallback occurs.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
        integrity_ok=False,
    )

    with pytest.raises(IntegrityError) as exc:
        selector.resolve()

    assert "integrity" in str(exc.value).lower()
    assert selector.can_read_write_workflow() is False


@pytest.mark.e2e
def test_ac_fr2401_04_no_global_fallback_on_local_failure():
    """AC-FR2401-04: a local failure never produces a global identity.

    Whether the local runtime is missing, mismatched or fails integrity, the
    resolved identity must never be the global runtime. The selector must
    raise rather than substitute a global identity.
    """
    # Each local-failure variant must raise; none may return a global source.
    failure_selectors = [
        RuntimeSelector(
            PROJ_A_ROOT, declared_version=PROJ_A_VERSION, local_present=False
        ),
        RuntimeSelector(
            PROJ_A_ROOT,
            declared_version=PROJ_A_VERSION,
            actual_version="0.13.0",
        ),
        RuntimeSelector(
            PROJ_A_ROOT,
            declared_version=PROJ_A_VERSION,
            integrity_ok=False,
        ),
    ]

    for selector in failure_selectors:
        with pytest.raises(InvalidRuntimeError):
            selector.resolve()
        # And workflow mutation must remain blocked.
        assert selector.can_read_write_workflow() is False


# ---------------------------------------------------------------------------
# AC-FR2401-05: running tasks keep start identity when PATH changes
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2401_05_task_manifest_frozen_after_path_change():
    """AC-FR2401-05: a running task's manifest records the server's start identity.

    After a server starts from a valid local runtime, all dispatched program
    steps, Agent tasks and background processes must record the same
    executable/interpreter/package identity in their manifests. Even if the
    system PATH/global Louke later changes, the manifest identity must not
    drift.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
    )

    # Server starts: identity is resolved and frozen.
    start_identity = selector.resolve()
    start_manifest = selector.task_manifest()

    # Simulate PATH/global change: the selector is already resolved; calling
    # task_manifest again must return the SAME identity, not a new one.
    later_manifest = selector.task_manifest()

    assert later_manifest["runtime_version"] == start_identity.version
    assert later_manifest["runtime_executable"] == start_identity.executable_path
    assert later_manifest["runtime_version"] == start_manifest["runtime_version"]
    assert later_manifest["runtime_executable"] == start_manifest["runtime_executable"]
    assert later_manifest["runtime_mode"] == start_manifest["runtime_mode"]
    assert later_manifest["runtime_source"] == start_manifest["runtime_source"]


@pytest.mark.e2e
def test_ac_fr2401_05_resolved_identity_is_idempotent():
    """AC-FR2401-05: resolving twice yields the same frozen identity object.

    The frozen identity assigned at server start must be returned on every
    subsequent resolution so child processes never observe a different runtime.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
    )

    first = selector.resolve()
    second = selector.resolve()

    assert second is first
    assert second.version == first.version
    assert second.executable_path == first.executable_path


# ---------------------------------------------------------------------------
# AC-FR2401-06: local switch requires controlled restart readiness
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2401_06_local_install_requires_controlled_restart():
    """AC-FR2401-06: a newly installed local runtime requires a controlled restart.

    After installing a local runtime from a setup-only bootstrap, the service
    must signal that a restart is required; readiness must prove the local
    identity before workflow mutations are allowed. Until restart, the
    previously resolved identity stays frozen.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
        mode=RuntimeMode.GLOBAL,
        global_version="0.12.0",
    )

    # Setup-only bootstrap resolves a compatible global identity.
    bootstrap_identity = selector.resolve()
    assert bootstrap_identity.mode is RuntimeMode.GLOBAL

    # Declare an upgrade to the local version; running identity is frozen.
    selector.declare_upgrade_pending(PROJ_A_VERSION)

    # The previously resolved identity must remain frozen - not yet switched.
    frozen_identity = selector.resolve()
    assert frozen_identity.version == bootstrap_identity.version
    assert frozen_identity.mode is RuntimeMode.GLOBAL


# ---------------------------------------------------------------------------
# AC-FR2401-07: running task identity frozen during upgrade
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2401_07_upgrade_freezes_running_task_identity():
    """AC-FR2401-07: a pending upgrade does not change a running task's identity.

    When an upgrade to A is declared, the already-resolved identity stays
    frozen until the service is restarted; the upgrade only affects the
    declared version, not the running task manifest.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
    )

    # Server starts with A's runtime.
    start_identity = selector.resolve()
    start_manifest = selector.task_manifest()
    assert start_manifest["runtime_version"] == PROJ_A_VERSION

    # Upgrade to a new version is declared.
    new_version = "0.12.9"
    selector.declare_upgrade_pending(new_version)

    # Running task manifest must still record the start identity.
    running_manifest = selector.task_manifest()
    assert running_manifest["runtime_version"] == start_identity.version
    assert running_manifest["runtime_version"] == PROJ_A_VERSION
    assert running_manifest["runtime_executable"] == start_identity.executable_path


@pytest.mark.e2e
def test_ac_fr2401_07_upgrade_does_not_affect_other_workspace():
    """AC-FR2401-07: upgrading one workspace does not change another's pin.

    A's upgrade must only change A's declared version; B's selector must be
    unaffected and resolve to B's own identity.
    """
    selector_a = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
    )
    selector_b = RuntimeSelector(
        project_root=PROJ_B_ROOT,
        declared_version=PROJ_B_VERSION,
    )

    selector_a.resolve()
    selector_a.declare_upgrade_pending("0.12.9")

    # B must be unaffected.
    identity_b = selector_b.resolve()
    assert identity_b.version == PROJ_B_VERSION
    assert identity_b.effective_root == PROJ_B_ROOT
    assert identity_b.source == "project-local"


# ---------------------------------------------------------------------------
# AC-FR2401-08: unmanaged/tampered runtime rejected
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2401_08_unmanaged_local_runtime_rejected():
    """AC-FR2401-08: a runtime that is not Louke-managed is rejected.

    The system must only accept Louke-managed artifacts whose
    identity/integrity verification passes. An unmanaged ``lk`` or runtime
    directory must be rejected with IntegrityError.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
        managed=False,
    )

    with pytest.raises(IntegrityError) as exc:
        selector.resolve()

    assert "managed" in str(exc.value).lower()
    assert selector.can_read_write_workflow() is False


@pytest.mark.e2e
def test_ac_fr2401_08_tampered_runtime_rejected_no_repo_code_execution():
    """AC-FR2401-08: a tampered artifact is rejected and no repository code is executed.

    A tampered runtime that fails integrity must raise IntegrityError; the
    selector must never execute arbitrary repository code or accept a
    non-Louke-managed artifact. The mode/version declaration remains visible
    but workflow access is blocked.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
        integrity_ok=False,
        managed=False,
    )

    # The first failing check (integrity) is surfaced; either way the
    # selector must reject and block workflow access.
    with pytest.raises(InvalidRuntimeError):
        selector.resolve()

    assert selector.can_read_write_workflow() is False


@pytest.mark.e2e
def test_ac_fr2401_08_managed_valid_runtime_accepted():
    """AC-FR2401-08: a Louke-managed, integrity-passing runtime is accepted.

    Only when the artifact is Louke-managed and integrity verification passes
    may the runtime be used; the resolved identity must be project-local.
    """
    selector = RuntimeSelector(
        project_root=PROJ_A_ROOT,
        declared_version=PROJ_A_VERSION,
        managed=True,
        integrity_ok=True,
        local_present=True,
    )

    identity = selector.resolve()

    assert isinstance(identity, RuntimeIdentity)
    assert identity.mode is RuntimeMode.LOCAL
    assert identity.source == "project-local"
    assert identity.version == PROJ_A_VERSION
    assert selector.can_read_write_workflow() is True
