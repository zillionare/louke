"""FR-2401: project-local Louke install, version pin and global fallback.

AC references:
- AC-FR2401-01: concurrent projects use their own pinned local runtime identity
  and data; no cross-project pollution.
- AC-FR2401-02: lk version/serve select the nearest workspace root and local
  runtime over PATH global; output shows effective root, mode, source and exact
  version/build.
- AC-FR2401-03: global mode uses resolvable global runtime with compatibility
  check before read/write workflow state.
- AC-FR2401-04: local runtime failures (missing, corrupt, wrong version,
  integrity failure, schema mismatch) fail before state writes with expected/
  actual info; no fallback to global.
- AC-FR2401-05: once server started with valid local runtime, tasks record the
  same executable/interpreter/package identity and do not switch to new PATH.
- AC-FR2401-06: setup-only Web switched to local runtime after controlled
  restart and readiness; global mode requires compatibility check.
- AC-FR2401-07: upgrades/repairs are project-isolated; running tasks keep start
  identity; unstarted tasks use new identity after controlled restart; failures
  roll back to consistent old version.
- AC-FR2401-08: only Louke-managed, integrity-verified artifacts are accepted;
  mode/version declarations remain auditable; managed env/binaries/cache are not
  version controlled.
"""

from __future__ import annotations

import pytest

from louke.runtime.runtime_selector import (
    GlobalModeError,
    IntegrityError,
    InvalidRuntimeError,
    RuntimeMode,
    RuntimeSelector,
    VersionMismatchError,
)


# -- AC-FR2401-01 -------------------------------------------------------------


def test_ac_fr2401_01_projects_use_own_pinned_runtime():
    """AC-FR2401-01: each project uses its own pinned local runtime."""
    selector_a = RuntimeSelector(project_root="/project_a", declared_version="0.12.1")
    selector_b = RuntimeSelector(project_root="/project_b", declared_version="0.12.2")

    identity_a = selector_a.resolve()
    identity_b = selector_b.resolve()

    assert identity_a.version == "0.12.1"
    assert identity_b.version == "0.12.2"
    assert identity_a.executable_path != identity_b.executable_path


# -- AC-FR2401-02 -------------------------------------------------------------


def test_ac_fr2401_02_nearest_workspace_root_wins():
    """AC-FR2401-02: nearest workspace root and local runtime are selected."""
    selector = RuntimeSelector(
        project_root="/project_a/subdir",
        declared_version="0.12.1",
    )
    identity = selector.resolve()

    assert identity.effective_root == "/project_a"
    assert identity.mode == RuntimeMode.LOCAL
    assert identity.source == "project-local"
    assert identity.version == "0.12.1"
    assert identity.build != ""


# -- AC-FR2401-03 -------------------------------------------------------------


def test_ac_fr2401_03_global_mode_requires_compatibility():
    """AC-FR2401-03: global mode requires compatibility before workflow state."""
    selector = RuntimeSelector(
        project_root="/project_c",
        mode=RuntimeMode.GLOBAL,
        global_version="0.12.0",
    )
    identity = selector.resolve()

    assert identity.mode == RuntimeMode.GLOBAL
    assert identity.source == "global"
    assert selector.can_read_write_workflow() is True


def test_ac_fr2401_03_incompatible_global_blocked():
    """AC-FR2401-03: incompatible global runtime blocks workflow state."""
    selector = RuntimeSelector(
        project_root="/project_c",
        mode=RuntimeMode.GLOBAL,
        global_version="0.11.0",
    )

    with pytest.raises(GlobalModeError):
        selector.resolve()


# -- AC-FR2401-04 -------------------------------------------------------------


def test_ac_fr2401_04_local_missing_blocked():
    """AC-FR2401-04: missing local runtime fails before state write."""
    selector = RuntimeSelector(
        project_root="/project_d",
        declared_version="0.12.1",
        local_present=False,
    )

    with pytest.raises(InvalidRuntimeError):
        selector.resolve()


def test_ac_fr2401_04_version_mismatch_blocked():
    """AC-FR2401-04: local version mismatch fails before state write."""
    selector = RuntimeSelector(
        project_root="/project_e",
        declared_version="0.12.1",
        actual_version="0.12.2",
    )

    with pytest.raises(VersionMismatchError):
        selector.resolve()


def test_ac_fr2401_04_integrity_failure_blocked():
    """AC-FR2401-04: integrity failure fails before state write."""
    selector = RuntimeSelector(
        project_root="/project_f",
        declared_version="0.12.1",
        integrity_ok=False,
    )

    with pytest.raises(IntegrityError):
        selector.resolve()


# -- AC-FR2401-05 -------------------------------------------------------------


def test_ac_fr2401_05_task_manifest_records_runtime_identity():
    """AC-FR2401-05: task manifests record the runtime identity."""
    selector = RuntimeSelector(project_root="/project_a", declared_version="0.12.1")
    identity = selector.resolve()

    manifest = selector.task_manifest()
    assert manifest["runtime_version"] == identity.version
    assert manifest["runtime_executable"] == identity.executable_path


# -- AC-FR2401-06 -------------------------------------------------------------


def test_ac_fr2401_06_local_switch_requires_readiness():
    """AC-FR2401-06: after local install, service must prove local identity."""
    selector = RuntimeSelector(
        project_root="/project_g",
        declared_version="0.12.1",
        local_present=False,
    )

    with pytest.raises(InvalidRuntimeError):
        selector.resolve()


# -- AC-FR2401-07 -------------------------------------------------------------


def test_ac_fr2401_07_running_task_keeps_start_identity():
    """AC-FR2401-07: running tasks keep the identity they started with."""
    selector = RuntimeSelector(project_root="/project_a", declared_version="0.12.1")
    original = selector.resolve()

    selector.declare_upgrade_pending(new_version="0.12.3")
    assert selector.resolve().version == original.version


# -- AC-FR2401-08 -------------------------------------------------------------


def test_ac_fr2401_08_unmanaged_lk_rejected():
    """AC-FR2401-08: unmanaged or tampered runtime is rejected."""
    selector = RuntimeSelector(
        project_root="/project_h",
        declared_version="0.12.1",
        managed=False,
    )

    with pytest.raises(IntegrityError):
        selector.resolve()
