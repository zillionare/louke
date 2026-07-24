"""Shared pytest configuration for v0.14-004 workspace-onboarding integration tests.

Mode B (mock-first): tests run against the real Python modules and
the real TestClient. No public HTTP exit is mocked; external adapters
(Git, OpenCode, ``gh``) are replaced with in-process stand-ins per
test-plan §2.4. This conftest follows the prior convention used by
the v0.14-003 integration suite (see
``tests/integration/v014_003_workflow_reflow/conftest.py``):

* ``_module_available`` and ``DEVON_MODULES`` are re-exported from
  ``_mode_b`` and the registered ``awaiting_devon_v014_004`` marker
  behaves analogously to ``awaiting_devon`` in spec-003.
* ``stub_*`` fixtures build a ``MagicMock`` per cross-module
  interface per spec-002 ``workbench_api`` convention.

The synthetic-host isolation helpers (``synthetic_host_project``,
``synthetic_bare_remote``) are genuinely new for v0.14-004 to
satisfy test-plan §3.2 (Ground Truth isolation).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ._mode_b import (
    DEVON_MODULES,
    _module_available,
    assert_contract_shape,
    devon_module_available,
    devon_module_or_mock,
    devon_module_skip,
    make_stub,
    synthetic_bare_remote,
    synthetic_host_project,
)
import os


REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "v014_workspace_onboarding"


# ---------------------------------------------------------------------------
# Pytest hook registration (mirrors v0.14-003 conftest)
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "v014_004: v0.14-004 workspace-onboarding integration test",
    )
    config.addinivalue_line(
        "markers",
        "v014_004_mode_b: stub-first test that auto-switches to Devon artifacts",
    )
    config.addinivalue_line(
        "markers",
        "awaiting_devon_v014_004(identifier): test exercises an interface "
        "whose real implementation is pending; auto-skips when Devon ships "
        "the canonical louke.* module for the given FR/NFR/IF id",
    )


WITHDRAWN_TEST_IF_BASENAMES: frozenset[str] = frozenset(
    {
        "test_if01_workbench_shell.py",
        "test_if02_first_user_login.py",
        "test_if03_entry_projection.py",
        "test_if04_setup_projection.py",
        "test_if05_repository_commands.py",
        "test_if06_dependency_recheck.py",
        "test_if07_review_apply_reconcile.py",
        "test_if08_workflow_status.py",
        "test_if09_guide_projection.py",
        "test_if10_owning_surface_action.py",
        "test_if11_start_story_deep_link.py",
        "test_if12_structured_evidence.py",
        "test_if13_accessibility_responsive.py",
        "test_if14_compatibility_urls.py",
        # Excluded: test_if15_ci_gates_evidence.py — that file
        # verifies the ``check_ac_traceability`` tool and the
        # CI gate contract; it does NOT drive the withdrawn
        # continuous Setup Wizard, and skipping it would mask
        # whether the new 44-AC baseline still gates green.
    }
)


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    for item in items:
        path = str(item.fspath)
        if "tests/integration/v014_workspace_onboarding" in path:
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.v014_004)
        # E-002 (Prism re-review N-002): legacy IF-01..IF-14 suites drive
        # the withdrawn continuous Setup Wizard
        # (``louke.web.setup_journey``, ``EntryFacts(setup_step=...)``,
        # ``setup_operations``, etc.). The new contract lives under
        # ``test_ac_*.py``; the legacy tests are kept for historical
        # diff only. The 14 IF-* files are matched by exact base-name
        # rather than the previous substring match so that
        # ``test_if15_ci_gates_evidence.py`` (the CI/traceability
        # gate verifier) is NOT accidentally skipped.
        #
        # NB: ``check_ac_traceability.py`` does NOT exclude this
        # directory from its scan; it still reads AC tokens from
        # these files. The new ``test_ac_*.py`` suite independently
        # covers all 44 ACs, so the legacy AC tokens (now mostly
        # absent from the placeholder bodies) are redundant rather
        # than load-bearing for the 44/44 closure count.
        basename = str(item.fspath).rsplit("/", 1)[-1]
        if basename in WITHDRAWN_TEST_IF_BASENAMES:
            # AC-FR0101-01 withdrawn; tracked in #323
            item.add_marker(
                pytest.mark.skip(
                    reason=(
                        "spec: withdrawn continuous Setup Wizard "
                        "(Prism review F-001/E-002/N-002); real "
                        "v0.14-004 contract lives under test_ac_*.py. "
                        "test_if15_ci_gates_evidence.py is intentionally "
                        "NOT in this skip-set because it verifies the "
                        "ac-trace gate itself. "
                        "AC-FR0101-01 withdrawn; tracked in #323."
                    )
                )
            )


# ---------------------------------------------------------------------------
# Fixture: workspace_dir / bare_git_remote (preserved from prior)
# ---------------------------------------------------------------------------


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    """An isolated, empty workspace directory with a clean HOME."""
    home = tmp_path / "home"
    home.mkdir()
    ws = tmp_path / "workspace"
    ws.mkdir()
    return ws


@pytest.fixture
def bare_git_remote(tmp_path: Path) -> Path:
    """A loopback bare Git repository for clone tests (no credentials)."""
    return synthetic_bare_remote(tmp_path)


# ---------------------------------------------------------------------------
# Fixture: synthetic-host isolation wrapper (test-plan §3.2)
# ---------------------------------------------------------------------------


@pytest.fixture
def synthetic_host():
    """Yield a temp directory containing a synthetic host ``.louke/``.

    Use this fixture when the test must touch the synthetic host's
    layout. An ``autouse`` variant below activates a fresh synthetic
    host for every test in this directory by default (Prism review
    F-003). Tests that take this fixture get a *nested* synthetic
    host so the inner one wins for tests that explicitly need to
    inspect the host's ``.louke/``.
    """
    with synthetic_host_project() as host:
        yield host


@pytest.fixture(autouse=True)
def _autouse_synthetic_host(tmp_path: Path):
    """Run every test in a fresh synthetic host-project directory.

    Per Mode B §3.3 (Prism review F-003), every test in this
    directory must run inside a synthetic host project so any code
    that accidentally reads the workspace's ``.louke/`` cannot leak
    Louke's own registry schema into the host project. The host
    project lives under ``tmp_path`` and is cleaned up by pytest.
    """
    with synthetic_host_project(
        marker=f"v014004-autouse-{os.urandom(2).hex()}"
    ) as host:
        yield host


# ---------------------------------------------------------------------------
# Fixtures: stub-first per-interface MagicMock (spec-002 pattern)
# ---------------------------------------------------------------------------


@pytest.fixture
def stub_setup_v2():
    """Mode B stub for IF-WEB-01 setup gate / IF-SETUP-01 projection."""
    return make_stub(
        "IF-WEB-01",
        SCHEMA_VERSION=2,
        STATUS_PENDING_USER="pending_user",
        STATUS_PENDING_MODEL="pending_model",
        STATUS_COMPLETE="complete",
    )


@pytest.fixture
def stub_setup_projection():
    stub = make_stub(
        "IF-SETUP-01",
        SCHEMA_VERSION=2,
        STATUS_PENDING_USER="pending_user",
        STATUS_PENDING_MODEL="pending_model",
        STATUS_COMPLETE="complete",
    )
    stub.read.return_value = {
        "version": 2,
        "workspace_id": "synthetic",
        "revision": 0,
        "status": stub.STATUS_PENDING_USER,
        "first_principal_id": None,
        "model_check": None,
        "completed_at": None,
    }
    return stub


@pytest.fixture
def stub_first_user():
    return make_stub("IF-SETUP-02", CONFLICT="CONFLICT")


@pytest.fixture
def stub_opencode_probe():
    probe = make_stub(
        "IF-SETUP-03",
        PROBE_PROMPT="please echo hi",
        STATE_PASSED="passed",
        STATE_FAILED="failed",
        STATE_UNCERTAIN="uncertain",
    )
    probe.is_available.return_value = True
    probe.run_minimal.return_value = {
        "state": probe.STATE_PASSED,
        "attempted_models": [{"model_id": "minimax/m2", "result": "ok"}],
    }
    return probe


@pytest.fixture
def stub_projects_context():
    return make_stub(
        "IF-PROJECT-01",
        STATE_EMPTY="empty",
        STATE_ACTIVE="active",
        STATE_CONFLICT="conflict",
    )


@pytest.fixture
def stub_guide_session():
    return make_stub(
        "IF-GUIDE-01",
        AUTHORITY_RUNTIME="runtime",
        AUTHORITY_GUIDE="guide",
        AUTHORITY_HUMAN="human",
        KIND_RUNTIME="runtime_status",
        KIND_GUIDE_ADVICE="guide_advice",
    )


@pytest.fixture
def stub_environment_gate():
    return make_stub(
        "IF-ENV-01",
        REQUIRED_SCOPES=("gist", "project", "repo", "workflow"),
    )


@pytest.fixture
def stub_release_entry():
    return make_stub(
        "IF-PREVIEW-01",
        PREVIEW_STALE="STALE_PREVIEW",
        STATE_READY="ready",
        STATE_FOUNDATION="foundation",
        STATE_SCRIBE="scribe",
    )


@pytest.fixture
def stub_runtime_projection():
    return make_stub(
        "IF-STATUS-01",
        CANONICAL_STAGES=(
            "M-START",
            "M-STORY",
            "M-SPEC",
            "M-ACC",
            "M-REQ-APPROVAL",
            "M-DESIGN",
            "M-IMPL",
            "M-TEST",
            "M-VERIFY",
            "M-SECURITY",
            "M-RELEASE",
            "M-PUBLISH",
            "M-MILESTONE",
        ),
    )


@pytest.fixture
def stub_return_application():
    return make_stub("IF-RETURN-01")


@pytest.fixture
def stub_document_surface():
    return make_stub("IF-DOC-01")


@pytest.fixture
def stub_compatibility_router():
    return make_stub(
        "IF-COMPAT-01",
        ENTRY_CANONICAL_PROJECTS="/workbench?activity=projects",
    )


@pytest.fixture
def stub_audit_observability():
    return make_stub("IF-AUDIT-01")


@pytest.fixture
def stub_csrf_middleware():
    return make_stub("IF-CSRF")


# ---------------------------------------------------------------------------
# Fixtures: real-artifact activation (mirrors spec-002 ``workbench_api``)
# ---------------------------------------------------------------------------


def _devon_fixture(identifier: str):
    """Skip the test cleanly when Devon's module for ``identifier`` is absent.

    Mirrors the spec-003 ``workbench_api`` pattern: the real module is
    returned when Devon has shipped it; otherwise the test is
    ``pytest.skip``-ed so the stub-first contract checks in the
    surrounding test file remain the source of truth.
    """

    def _inner():
        if not devon_module_available(identifier):
            # AC-FR0001-01; tracked in #322-#337
            pytest.skip(
                f"v0.14-004 awaits Devon ship of {identifier!r}; "
                f"stub-first contract checks above already cover the "
                f"same surface (mirrors spec-003 awaiting_devon marker) "
                f"(AC-FR0001-01 through AC-FR1501-01, #322-#337)"
            )
        module, _ = devon_module_or_mock(identifier)
        return module

    return _inner


@pytest.fixture
def setup_v2_artifact():
    """IF-WEB-01 / IF-SETUP-01: real Setup + Web artifact or stub."""
    return _devon_fixture("IF-WEB-01")()


@pytest.fixture
def opencode_probe_artifact():
    return _devon_fixture("IF-SETUP-03")()


@pytest.fixture
def projects_context_artifact():
    return _devon_fixture("IF-PROJECT-01")()


@pytest.fixture
def guide_session_artifact():
    return _devon_fixture("IF-GUIDE-01")()


@pytest.fixture
def environment_gate_artifact():
    return _devon_fixture("IF-ENV-01")()


@pytest.fixture
def release_entry_artifact():
    return _devon_fixture("IF-PREVIEW-01")()


@pytest.fixture
def runtime_projection_artifact():
    return _devon_fixture("IF-STATUS-01")()


@pytest.fixture
def return_application_artifact():
    return _devon_fixture("IF-RETURN-01")()


@pytest.fixture
def document_surface_artifact():
    return _devon_fixture("IF-DOC-01")()


@pytest.fixture
def compatibility_router_artifact():
    return _devon_fixture("IF-COMPAT-01")()


@pytest.fixture
def audit_observability_artifact():
    return _devon_fixture("IF-AUDIT-01")()


@pytest.fixture
def csrf_middleware_artifact():
    return _devon_fixture("IF-CSRF")()


# ---------------------------------------------------------------------------
# Re-export the prior helpers at module level so tests can ``from . import``
# ---------------------------------------------------------------------------


__all__ = [
    "DEVON_MODULES",
    "_module_available",
    "assert_contract_shape",
    "devon_module_available",
    "devon_module_or_mock",
    "devon_module_skip",
    "make_stub",
    "synthetic_bare_remote",
    "synthetic_host_project",
]  # noqa: F401
