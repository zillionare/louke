"""Shared pytest configuration for v0.14-003 workflow-reflow-impl
integration tests.

Spec-003 differs from spec-002: Devon has already shipped **real**
implementations of every FR/NFR module under ``louke/v014/frXXXX_*`` and
``louke/v014/nfrXXXX_*`` (commits 11d6b7e..7c02896, issues #284-#319). The
tests in this directory therefore call those real modules directly and
assert on their public observable contracts (per
``.louke/project/specs/v0.14-003-workflow-reflow-impl/interfaces.md``).

Mode (per HANDOFF §1):
- **Activation tests** (``test_activation_cli.py``) call the real CLI via
  ``subprocess.run`` using the ``venv_python`` fixture. They are dormant
  until Devon ships the corresponding ``louke._tools.*`` module.
- **Real-module integration tests** call ``louke.v014.frXXXX_*`` directly
  and are the primary source of coverage. They are NOT mocks.
- **Document/fixture validation tests** read candidate artifacts from
  ``.louke/project/specs/v0.14-003-workflow-reflow-impl/`` and assert
  their schema closure.
- **Host-project integration tests** (``test_host_integration.py``) run
  Louke's CLI against synthetic host fixtures.

Virtual environment policy (per HANDOFF and v0.14-003 test-plan.md §2.3):
- Tests that spawn subprocesses MUST use the ``venv_python`` fixture
  instead of ``sys.executable``. The fixture skips the test when pytest
  is not running inside a venv.

References (ground truth: spec/acc/test-plan/interfaces only):
- v0.14-003 interfaces.md §1-§16 (16 observable IF-* contracts)
- v0.14-003 interfaces.md §17 (7 inherited 002 machine contracts)
- v0.14-003 test-plan.md §2.3 (test runner, .venv requirement)
- v0.14-003 test-plan.md §4 (per-AC required layer / runner / fixture
  / CI gate / evidence)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_ROOT = REPO_ROOT / "tests"
SPEC_ROOT = (
    REPO_ROOT / ".louke" / "project" / "specs" / "v0.14-003-workflow-reflow-impl"
)
FIXTURES_ROOT = TESTS_ROOT / "fixtures" / "v014_003_workflow_reflow"


# ---------------------------------------------------------------------------
# Virtual environment guard
# ---------------------------------------------------------------------------
# Per HANDOFF §1 (Python discipline) and v0.14-003 test-plan.md §2.3
# ("clean build tree + 每件 artifact 独立 clean venv"). All subprocess
# calls MUST go through venv_python, not sys.executable, to avoid polluting
# system Python.


def in_venv() -> bool:
    """Return True if the current Python is running inside a managed env.

    Accepts PEP 405 venv, legacy virtualenv, conda environments, Louke
    global runtime (``~/.louke/venv``), and explicit ``VIRTUAL_ENV``.
    Rejects bare system Python.
    """
    if hasattr(sys, "real_prefix"):
        return True
    if sys.prefix != sys.base_prefix:
        return True
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        executable = Path(sys.executable).resolve()
        try:
            executable.relative_to(Path(conda_prefix).resolve())
            return True
        except ValueError:
            # AC-NFR0500-01: executable not inside conda prefix; continue
            # checking other managed-environment markers.
            pass
    executable = Path(sys.executable).resolve()
    if ".louke" in executable.parts and "venv" in executable.parts:
        return True
    if os.environ.get("VIRTUAL_ENV"):
        return True
    return False


@pytest.fixture(scope="session")
def venv_python() -> str:
    """Return the venv Python executable path for subprocess calls.

    Skips the test if pytest is not running inside a venv.
    """
    if not in_venv():
        pytest.skip(
            # AC-NFR0500-01: integration tests require a virtual environment
            # to avoid polluting system Python.
            "Integration test requires a virtual environment to avoid "
            "polluting system Python (AC-NFR0500-01). Create one with: "
            "python -m venv .venv && source .venv/bin/activate && "
            "pip install -e '.[dev]', then re-run pytest."
        )
    return sys.executable


# ---------------------------------------------------------------------------
# Module-availability helper (mock-first pattern from spec-002)
# ---------------------------------------------------------------------------


def _module_available(module_path: str) -> bool:
    """Check if a module is importable without importing it."""
    import importlib.util

    return importlib.util.find_spec(module_path) is not None


# ---------------------------------------------------------------------------
# Common fixtures: candidate spec docs
# ---------------------------------------------------------------------------


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Required spec file missing: {path}")
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def spec_root() -> Path:
    """Path to the v0.14-003 spec directory."""
    return SPEC_ROOT


@pytest.fixture(scope="session")
def spec_md() -> str:
    """``spec.md`` contents."""
    return _read_text(SPEC_ROOT / "spec.md")


@pytest.fixture(scope="session")
def acceptance_md() -> str:
    """``acceptance.md`` contents (36 AC IDs)."""
    return _read_text(SPEC_ROOT / "acceptance.md")


@pytest.fixture(scope="session")
def test_plan_md() -> str:
    """``test-plan.md`` contents."""
    return _read_text(SPEC_ROOT / "test-plan.md")


@pytest.fixture(scope="session")
def interfaces_md() -> str:
    """``interfaces.md`` contents (16 003 IF + 7 inherited = 23 IF)."""
    return _read_text(SPEC_ROOT / "interfaces.md")


@pytest.fixture(scope="session")
def architecture_md() -> str:
    """``architecture.md`` contents (16 ARC anchors)."""
    return _read_text(SPEC_ROOT / "architecture.md")


@pytest.fixture(scope="session")
def flow_md() -> str:
    """``flow.md`` contents (workflow ordering)."""
    return _read_text(SPEC_ROOT / "flow.md")


# ---------------------------------------------------------------------------
# Fixtures: expected closure sets (ground-truth derived from spec docs)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def expected_ac_ids() -> set[str]:
    """The 36 AC IDs declared in spec-003 acceptance.md (30 FR + 6 NFR).

    Expected values are hard-coded from the spec body (independently
    computed by reading acceptance.md section headers); they are NOT
    back-filled from any louke validator.
    """
    return {
        "AC-FR0100-01",
        "AC-FR0200-01",
        "AC-FR0300-01",
        "AC-FR0400-01",
        "AC-FR0500-01",
        "AC-FR0600-01",
        "AC-FR0700-01",
        "AC-FR0800-01",
        "AC-FR0900-01",
        "AC-FR1000-01",
        "AC-FR1100-01",
        "AC-FR1200-01",
        "AC-FR1300-01",
        "AC-FR1400-01",
        "AC-FR1500-01",
        "AC-FR1600-01",
        "AC-FR1700-01",
        "AC-FR1800-01",
        "AC-FR1900-01",
        "AC-FR2000-01",
        "AC-FR2100-01",
        "AC-FR2200-01",
        "AC-FR2300-01",
        "AC-FR2400-01",
        "AC-FR2500-01",
        "AC-FR2600-01",
        "AC-FR2700-01",
        "AC-FR2800-01",
        "AC-FR2900-01",
        "AC-FR3000-01",
        "AC-NFR0100-01",
        "AC-NFR0200-01",
        "AC-NFR0300-01",
        "AC-NFR0400-01",
        "AC-NFR0500-01",
        "AC-NFR0600-01",
    }


@pytest.fixture(scope="session")
def expected_003_if_ids() -> set[str]:
    """The 16 003 Runtime observable interfaces (interfaces.md §1-§16).

    Hard-coded from the interfaces.md section headers; NOT back-filled.
    """
    return {
        "IF-IMPL-01",
        "IF-WFR-01",
        "IF-TASK-01",
        "IF-RGR-01",
        "IF-REV-02",
        "IF-TEST-02",
        "IF-CAND-01",
        "IF-QUAL-01",
        "IF-CI-02",
        "IF-BLD-02",
        "IF-SEC-01",
        "IF-REL-02",
        "IF-PUB-02",
        "IF-TRACE-01",
        "IF-PROMPT-02",
        "IF-MIG-01",
    }


@pytest.fixture(scope="session")
def expected_inherited_if_ids() -> set[str]:
    """The 7 inherited 002 machine-contract interfaces (interfaces.md §17.2)."""
    return {
        "IF-PC-01",
        "IF-TST-01",
        "IF-CI-01",
        "IF-REL-01",
        "IF-BLD-01",
        "IF-PUB-01",
        "IF-PRM-01",
    }


@pytest.fixture(scope="session")
def expected_fr_ids() -> set[str]:
    """The 30 FR IDs declared in spec-003 spec.md."""
    return {f"FR-{i:04d}" for i in range(100, 3100, 100)}


@pytest.fixture(scope="session")
def expected_nfr_ids() -> set[str]:
    """The 6 NFR IDs declared in spec-003 spec.md."""
    return {f"NFR-{i:04d}" for i in range(100, 700, 100)}


@pytest.fixture(scope="session")
def expected_arc_anchors() -> set[str]:
    """The 16 ARC anchors declared in spec-003 architecture.md."""
    return {f"ARC-{i:02d}" for i in range(1, 17)}


# ---------------------------------------------------------------------------
# Helper: Devon module availability (mock-first when missing)
# ---------------------------------------------------------------------------

# Mapping of FR/NFR -> Devon module path. When a module is missing (Devon
# hasn't shipped that FR yet), tests can request the corresponding
# ``mock_<short>`` fixture, which auto-skips once Devon ships the real
# module. This mirrors the spec-002 shield's pattern.
DEVON_MODULES: dict[str, str] = {
    "FR-0100": "louke.v014.fr0100_m_impl_entry",
    "FR-0200": "louke.v014.fr0200_task_graph",
    "FR-0300": "louke.v014.fr0300_task_graph_validator",
    "FR-0400": "louke.v014.fr0400_task_manifest",
    "FR-0500": "louke.v014.fr0500_red_program_gate",
    "FR-0600": "louke.v014.fr0600_red_git_checkpoint",
    "FR-0700": "louke.v014.fr0700_red_review",
    "FR-0800": "louke.v014.fr0800_green_minimal",
    "FR-0900": "louke.v014.fr0900_green_commit",
    "FR-1000": "louke.v014.fr1000_refactor_subphase",
    "FR-1100": "louke.v014.fr1100_final_review_gate",
    "FR-1200": "louke.v014.fr1200_m_test_assets",
    "FR-1300": "louke.v014.fr1300_m_test_executor",
    "FR-1400": "louke.v014.fr1400_release_candidate",
    "FR-1500": "louke.v014.fr1500_local_quality_chain",
    "FR-1600": "louke.v014.fr1600_artifact_version",
    "FR-1700": "louke.v014.fr1700_github_ci",
    "FR-1800": "louke.v014.fr1800_candidate_prism_review",
    "FR-1900": "louke.v014.fr1900_security_gates",
    "FR-2000": "louke.v014.fr2000_finding_routing",
    "FR-2100": "louke.v014.fr2100_m_release_preview",
    "FR-2200": "louke.v014.fr2200_publish_ledger",
    "FR-2300": "louke.v014.fr2300_post_publish_recovery",
    "FR-2400": "louke.v014.fr2400_m_milestone",
    "FR-2500": "louke.v014.fr2500_bug_fix_variant",
    "FR-2600": "louke.v014.fr2600_return_upstream",
    "FR-2700": "louke.v014.fr2700_retry_waiver",
    "FR-2800": "louke.v014.fr2800_impl_prompts",
    "FR-2900": "louke.v014.fr2900_review_prompts",
    "FR-3000": "louke.v014.fr3000_keeper_maestro",
    "NFR-0100": "louke.v014.nfr0100_atomicity",  # also nfr0100_determinism
    "NFR-0200": "louke.v014.nfr0200_least_privilege",
    "NFR-0300": "louke.v014.nfr0300_restart_recovery",
    "NFR-0400": "louke.v014.nfr0400_audit_observability",
    "NFR-0500": "louke.v014.nfr0500_host_compat",
    "NFR-0600": "louke.v014.nfr0600_migration_compat",
}


def devon_module_available(fr_id: str) -> bool:
    """Check if Devon has shipped the module for the given FR/NFR."""
    return _module_available(DEVON_MODULES[fr_id])


# ---------------------------------------------------------------------------
# Pytest hooks
# ---------------------------------------------------------------------------


def pytest_configure(config):
    """Register v0.14-003 specific markers."""
    config.addinivalue_line(
        "markers",
        "v014_003: v0.14-003 workflow-reflow-impl integration test",
    )
    config.addinivalue_line(
        "markers",
        "awaiting_devon(fr): test exercises an interface whose real "
        "implementation is pending; auto-skips when Devon ships the "
        "corresponding louke.v014.frXXXX_* module",
    )
    config.addinivalue_line(
        "markers",
        "real_module: test calls Devon's real louke.v014.frXXXX_* "
        "implementation (not a mock)",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark every test under tests/integration/v014_003_workflow_reflow/."""
    for item in items:
        if "tests/integration/v014_003_workflow_reflow" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.v014_003)
