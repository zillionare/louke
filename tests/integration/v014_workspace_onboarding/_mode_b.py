"""Mode B (mock-first) shared helpers for v0.14-004 workspace-onboarding.

This module reuses the prior pattern established for v0.14-003 in
``tests/integration/v014_003_workflow_reflow/conftest.py`` and
``tests/e2e/v014_design_contracts/conftest.py``:

* ``_module_available(module_path)`` — ``importlib.util.find_spec``
  based availability check; mirrors the spec-003 conftest helper.
* ``DEVON_MODULES`` — a per-FR registry that maps each v0.14-004
  FR/NFR to the canonical ``louke.*`` module path that Devon must
  publish; mirrors the spec-003 ``DEVON_MODULES`` registry.
* ``devon_module_available(fr_id)`` — FR lookup helper; mirrors the
  spec-003 ``devon_module_available`` helper.

What is **new** for v0.14-004 (not present in v0.14-002/-003):

* ``synthetic_host_project`` — a context manager that builds an
  isolated host-project ``.louke/`` directory and verifies Louke
  tooling does not leak its own registry schema into the host
  project (test-plan §3.2 Ground Truth isolation).
* ``_seed_host_louke`` — the synthetic-project writer.
* ``synthetic_bare_remote`` — a controllable Git remote for IF-ENV-02
  binding tests without invoking system Git credentials.
* ``awaiting_devon_v014_004`` marker — registered alongside the
  ``awaiting_devon`` marker that already ships with spec-003.

Stubs are produced with ``unittest.mock.MagicMock`` exactly as the
spec-002 ``workbench_api`` fixture does; the same recommendation
applies: ``MagicMock`` instances pass trivially because every
attribute exists, but real implementations are checked strictly with
``assert_contract_shape``.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import MagicMock

import pytest


# ---------------------------------------------------------------------------
# Module-availability helper (mirrors v0.14-003 conftest)
# ---------------------------------------------------------------------------


def _module_available(module_path: str) -> bool:
    """Return True iff ``module_path`` is importable without importing.

    Mirrors the spec-003 helper in
    ``tests/integration/v014_003_workflow_reflow/conftest.py:117``. The
    check uses ``importlib.util.find_spec`` so we never trigger the
    module's side effects before we know we want it.
    """
    return importlib.util.find_spec(module_path) is not None


# ---------------------------------------------------------------------------
# Devon-module registry (mirrors v0.14-003 ``DEVON_MODULES``)
# ---------------------------------------------------------------------------


DEVON_MODULES: dict[str, str] = {
    "IF-WEB-01": "louke.web.setup_gate",
    "IF-SETUP-01": "louke.web.setup_projection",
    "IF-SETUP-02": "louke.web.first_user",
    "IF-SETUP-03": "louke.web.opencode_probe",
    "IF-PROJECT-01": "louke.web.projects_context",
    "IF-GUIDE-01": "louke.web.guide_session",
    "IF-ENV-01": "louke.web.environment_gate",
    "IF-ENV-02": "louke.web.environment_gate",  # same module surface
    "IF-DRAFT-01": "louke.web.draft_storage",
    "IF-PREVIEW-01": "louke.runtime.release_entry",
    "IF-CREATE-01": "louke.runtime.foundation_scribe",
    "IF-IDENTITY-01": "louke.runtime.project_identity",
    "IF-STATUS-01": "louke.runtime.projection",
    "IF-ATTEMPT-01": "louke.runtime.attempt_detail",
    "IF-RETURN-01": "louke.runtime.return_application",
    "IF-DOC-01": "louke.web.document_surface",
    "IF-COMPAT-01": "louke.web.compatibility_router",
    "IF-AUDIT-01": "louke.runtime.audit_observability",
    "IF-CSRF": "louke.web.csrf_middleware",
}


def devon_module_available(identifier: str) -> bool:
    """Return True iff Devon's module for ``identifier`` is importable.

    ``identifier`` may be either a v0.14-004 interface id (``IF-*``)
    or an FR/NFR id (``FR-XXXX`` / ``NFR-XXXX``). The lookup goes
    through ``_INTERFACE_TO_FR`` first when an interface id is given.
    """
    fr_or_if = identifier
    module = DEVON_MODULES.get(fr_or_if) or DEVON_MODULES.get(
        _INTERFACE_TO_FR.get(fr_or_if, ""), ""
    )
    if module:
        return _module_available(module)
    raise KeyError(
        f"unknown identifier {identifier!r}; expected one of "
        f"{sorted(DEVON_MODULES.keys())}"
    )


_INTERFACE_TO_FR: dict[str, str] = {
    "IF-WEB-01": "FR-0001",
    "IF-SETUP-01": "FR-0101",
    "IF-SETUP-02": "FR-0101",
    "IF-SETUP-03": "FR-0201",
    "IF-PROJECT-01": "FR-0401",
    "IF-GUIDE-01": "FR-0501",
    "IF-ENV-01": "FR-0601",
    "IF-ENV-02": "FR-0801",
    "IF-DRAFT-01": "FR-0901",
    "IF-PREVIEW-01": "FR-1001",
    "IF-CREATE-01": "FR-1101",
    "IF-IDENTITY-01": "FR-1501",
    "IF-STATUS-01": "FR-1201",
    "IF-ATTEMPT-01": "FR-1301",
    "IF-RETURN-01": "FR-1401",
    "IF-DOC-01": "FR-1101",
    "IF-COMPAT-01": "FR-1501",
    "IF-AUDIT-01": "NFR-0101",
    "IF-CSRF": "NFR-0101",
}


def devon_module_skip(identifier: str, *, fr: str) -> None:
    """Skip the test with the ``awaiting_devon_v014_004`` marker semantics.

    Mirrors the spec-003 ``pytest.mark.awaiting_devon(fr)`` usage: the
    test will skip cleanly when Devon has not yet shipped the canonical
    module for the given FR/NFR, and stays in scope when it does.
    """
    if devon_module_available(identifier):
        return
    pytest.skip(
        f"v0.14-004 awaits Devon ship of {identifier!r} (skipped like "
        f"spec-003 ``awaiting_devon({fr})``) "
        f"see AC-{fr}-01 and issues #322-#342"
    )


def devon_module_or_mock(identifier: str) -> tuple[Any, bool]:
    """Return ``(module, is_mock)`` for the given identifier.

    Mirrors the spec-002 ``_import_or_mock`` helper in
    ``tests/e2e/v014_design_contracts/conftest.py:50``; the boolean
    flag lets the test author decide whether to assert against the
    real surface (when Devon has shipped) or the stub contract.

    When Devon has shipped, the real module is loaded so the test
    can call into it; the test should then re-state the FR it is
    covering and update ``awaiting_devon_v014_004`` to
    ``live_v014_004`` once it has been promoted.
    """
    try:
        fr = _INTERFACE_TO_FR.get(identifier) or identifier
        module_path = DEVON_MODULES.get(identifier) or DEVON_MODULES.get(fr)
        if not module_path:
            raise KeyError(identifier)
        module = importlib.import_module(module_path)
        return module, False
    except (ImportError, KeyError):
        return MagicMock(name=f"v014_004-stub:{identifier}"), True


# ---------------------------------------------------------------------------
# Stub factory + contract shape checker
# ---------------------------------------------------------------------------


def make_stub(identifier: str, **attributes: Any) -> MagicMock:
    """Build a ``MagicMock`` that exposes the artifact's surface.

    ``attributes`` lets the test pin the return values that matter for
    the contract assertion; ``MagicMock`` auto-supplies every other
    attribute. This is the same convention as the spec-002
    ``workbench_api`` fixture, just expressed at the call site.
    """
    mock = MagicMock(name=f"v014_004-stub:{identifier}")
    for key, value in attributes.items():
        setattr(mock, key, value)
    return mock


def assert_contract_shape(
    instance: Any,
    required: tuple[str, ...],
    *,
    context: str,
) -> None:
    """Assert ``instance`` exposes every ``required`` attribute.

    ``context`` is included in the AssertionError so a stub mismatch is
    easy to locate; ``MagicMock`` instances pass trivially because every
    attribute exists, but real implementations are checked strictly.
    """
    missing = [name for name in required if not hasattr(instance, name)]
    assert not missing, (
        f"{context}: contract missing attributes {missing!r}; "
        f"present attributes: "
        f"{[n for n in dir(instance) if not n.startswith('_')][:20]}"
    )


# ---------------------------------------------------------------------------
# Synthetic host-project isolation (test-plan §3.2 — new in v0.14-004)
# ---------------------------------------------------------------------------


def _seed_host_louke(target: Path, *, marker: str) -> None:
    """Write a synthetic host-project ``.louke/project/project.toml``.

    ``marker`` is a per-run prefix used so concurrent CI jobs do not
    accidentally share the same workspace_id. The payload is JSON-only
    — Louke tooling must read it without leaking its own internal
    schema into the host project.
    """
    louke_dir = target / ".louke"
    project_dir = louke_dir / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "test_framework": "pytest",
            "workspace_id_marker": marker,
            "is_synthetic_host_project": True,
        },
        "integration": {"run": "noop", "paths": ["tests"], "cwd": "."},
        "e2e": {"run": "noop", "paths": ["tests/e2e"], "cwd": "."},
    }
    (project_dir / "project.toml").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )


@contextmanager
def synthetic_host_project(marker: str | None = None) -> Iterator[Path]:
    """Yield a temp directory containing a synthetic host ``.louke/``.

    Per Mode B §3.3 (and ``test-plan`` §3.2 Ground Truth isolation),
    every v0.14-004 test that exercises Louke tooling must run inside
    a host-project layout; this context manager builds one with a
    per-run ``workspace_id_marker`` so two tests cannot collide.

    Note: this context manager does *not* chdir into the synthetic
    project; it only writes ``.louke/project/project.toml`` so the
    host-project layout exists in the temp directory. Tests that
    need to work from the synthetic project as the active cwd
    should ``os.chdir(yielded_path)`` themselves inside the body.
    """
    if marker is None:
        marker = "v014004-" + os.urandom(4).hex()
    tmp = Path(tempfile.mkdtemp(prefix=f"louke-synth-{marker}-"))
    _seed_host_louke(tmp, marker=marker)
    try:
        yield tmp
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def synthetic_bare_remote(tmp_path: Path) -> Path:
    """Create an empty bare Git remote at ``tmp_path/bare.git``.

    No real network is involved; the URL is the local path. Stands in
    for the ``git-empty-remote`` fixture in test-plan §2.4 without
    requiring system git author/credential configuration.
    """
    remote = tmp_path / "bare.git"
    if remote.exists():
        shutil.rmtree(remote, ignore_errors=True)
    remote.mkdir()
    subprocess.run(
        ["git", "init", "--bare", str(remote)],
        check=True,
        capture_output=True,
    )
    return remote


# ---------------------------------------------------------------------------
# Compile-time path resolution for design-stage scope (testers, etc.)
# ---------------------------------------------------------------------------


def iter_files(root: Path):
    """Yield every file under ``root`` (used by synthetic-host leak scans)."""
    for path in root.rglob("*"):
        if path.is_file():
            yield path
