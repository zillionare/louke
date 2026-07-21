"""Shared pytest configuration for v0.14-002 design-contracts integration tests.

Mode B (mock-first): ``louke._tools.*`` modules for v0.14-002 are not yet
implemented by Devon. This conftest injects ``unittest.mock.MagicMock``
stubs for any ``louke._tools.<module>`` that fails to import, so tests can
be written against the interface contract defined in
``.louke/project/specs/v0.14-002-workflow-reflow-design/interfaces.md``.

When Devon ships a real module, the corresponding mock is bypassed
automatically (the real import wins). Tests that still rely on mock
behaviour must explicitly request the ``mock_<module>`` fixture.

Virtual environment policy:
- Tests that spawn subprocesses (``test_activation_cli.py``,
  ``test_host_integration.py``) MUST use the ``venv_python`` fixture
  instead of ``sys.executable`` directly. This prevents accidentally
  running Louke's CLI with system Python, which could pollute the
  system environment. See v0.14-002 test-plan.md §2.3:
  "依赖由project `.venv`安装锁定的`pytest==8.4.1`..." and
  v0.14-003 test-plan.md §2.3: "clean build tree + 每件 artifact 独立
  clean venv".
- The ``venv_python`` fixture skips tests when pytest is not running
  inside a venv (``sys.prefix == sys.base_prefix``), with a clear message
  directing the user to create a venv first.

References (ground truth: spec/acc/test-plan/interfaces only):
- v0.14-002 interfaces.md (15 IF-XXX contracts, CLI command definitions)
- v0.14-002 test-plan.md §2.3 (test runner, .venv requirement)
- v0.14-003 interfaces.md §17 (002 contracts inherited, not redefined)
- v0.14-003 test-plan.md §2.3 (clean venv, lk --version)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
TESTS_ROOT = REPO_ROOT / "tests"
SPEC_ROOT = (
    REPO_ROOT
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
DESIGN_ARTIFACTS = SPEC_ROOT / "design-artifacts"
FIXTURES_ROOT = TESTS_ROOT / "fixtures" / "v014_design_contracts"


# ---------------------------------------------------------------------------
# Virtual environment guard
# ---------------------------------------------------------------------------
# Tests that spawn subprocesses (activation tests, host-project integration
# tests) MUST use ``venv_python`` instead of ``sys.executable``. Running
# Louke's CLI with system Python risks polluting the system environment
# (e.g., importing a globally-installed louke instead of the dev version).
# v0.14-003 architecture.md §IF-BLD-02 explicitly requires clean venv for
# artifact verification; we apply the same discipline to integration tests.

def in_venv() -> bool:
    """Return True if the current Python is running inside a managed environment.

    Accepts:
    - ``venv`` (PEP 405: ``sys.prefix != sys.base_prefix``)
    - Legacy ``virtualenv`` (sets ``sys.real_prefix``)
    - Conda environments (``CONDA_PREFIX`` is set and executable is inside it)
    - Louke global runtime (``~/.louke/venv``)
    - Explicit ``VIRTUAL_ENV`` env var (for CI)

    Rejects: bare system Python (``/usr/bin/python``, Homebrew, etc.)
    """
    # Legacy virtualenv
    if hasattr(sys, "real_prefix"):
        return True
    # PEP 405 venv
    if sys.prefix != sys.base_prefix:
        return True
    # Conda environment (base or named env — both are managed, not system)
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        executable = Path(sys.executable).resolve()
        try:
            executable.relative_to(Path(conda_prefix).resolve())
            return True
        except ValueError:
            pass
    # Louke global runtime (~/.louke/venv) — managed, not system
    executable = Path(sys.executable).resolve()
    if ".louke" in executable.parts and "venv" in executable.parts:
        return True
    # Explicit override via env var (for CI that exports VIRTUAL_ENV)
    if os.environ.get("VIRTUAL_ENV"):
        return True
    return False


@pytest.fixture(scope="session")
def venv_python() -> str:
    """Return the venv Python executable path for subprocess calls.

    Skips the test if pytest is not running inside a venv. This prevents
    integration tests from accidentally invoking Louke's CLI with system
    Python, which could:
    1. Use a globally-installed louke instead of the dev version
    2. Modify system Python's environment (pip install, etc.)
    3. Produce misleading test results against the wrong louke version

    Usage in tests::

        def test_something(venv_python):
            result = subprocess.run(
                [venv_python, "-m", "louke._tools.design_contract", ...],
                ...
            )

    To create a venv for development::

        python -m venv .venv
        source .venv/bin/activate
        pip install -e '.[dev]'
        python -m pytest tests/integration/v014_design_contracts
    """
    if not in_venv():
        pytest.skip(
            "Integration test requires a virtual environment to avoid "
            "polluting system Python. Create one with: "
            "python -m venv .venv && source .venv/bin/activate && "
            "pip install -e '.[dev]', then re-run pytest."
        )
    return sys.executable

# ---------------------------------------------------------------------------
# Mock infrastructure (Mode B)
# ---------------------------------------------------------------------------

# Mapping of (module_path) -> default mock configuration. Each entry describes
# the v0.14-002 module Devon will implement and the IF-XXX interface it
# realises. Tests can request ``mock_<short_name>`` to get the MagicMock.
MOCK_MODULES: dict[str, dict[str, str]] = {
    "louke._tools.design_contract": {"if": "IF-DES-02", "fr": "FR-0400"},
    "louke._tools.contract_registry": {"if": "IF-REG-01", "fr": "FR-0700"},
    "louke._tools.ci_contract": {"if": "IF-CI-01", "fr": "FR-1100"},
    "louke._tools.precommit_contract": {"if": "IF-PC-01", "fr": "FR-1000"},
    "louke._tools.release_version": {"if": "IF-REL-01", "fr": "FR-1400"},
    "louke._tools.build_artifact": {"if": "IF-BLD-01", "fr": "FR-1500"},
    "louke._tools.publish_recovery": {"if": "IF-PUB-01", "fr": "FR-1600"},
    "louke._tools.prompt_bundle": {"if": "IF-PRM-01", "fr": "FR-1700"},
    "louke._tools.design_review": {"if": "IF-REV-01", "fr": "FR-2500"},
    "louke._tools.host_facts": {"if": "IF-FCT-01", "fr": "FR-0200"},
    "louke._tools.workbench": {"if": "IF-WEB-01", "fr": "FR-0300"},
    "louke._tools.audit_export": {"if": "IF-AUD-01", "fr": "NFR-0400"},
    "louke._tools.design_coordinator": {"if": "IF-DES-01", "fr": "FR-0100"},
}


def _import_or_mock(module_path: str) -> tuple[Any, bool]:
    """Import ``module_path`` or return a ``MagicMock`` stub.

    Returns ``(module, is_mock)``. When the real module exists, ``is_mock``
    is ``False`` and tests run against the real implementation.
    """
    try:
        import importlib

        return importlib.import_module(module_path), False
    except ImportError:
        return MagicMock(name=module_path), True


@pytest.fixture(scope="session")
def mock_louke_tools() -> dict[str, Any]:
    """Session-scoped cache of mock/real ``louke._tools.*`` modules.

    Each entry is either the real module (if Devon has implemented it) or
    a ``MagicMock`` stub configured with sensible defaults derived from
    the candidate artifacts. Tests that need module-specific behaviour
    should request the per-module fixture (e.g. ``mock_design_contract``)
    which overrides defaults on top of this cache.
    """
    cache: dict[str, Any] = {}
    for path in MOCK_MODULES:
        module, _is_mock = _import_or_mock(path)
        cache[path] = module
    return cache


def _make_module_fixture(module_path: str):
    """Factory: build a per-module mock fixture with override helpers.

    When Devon ships the real module, this fixture **auto-skips** instead
    of returning the real module. This prevents tests from setting
    ``.return_value`` on real module attributes (which would crash with
    ``AttributeError``) and forces the test author to write a real
    integration test that calls the actual implementation.
    """

    @pytest.fixture
    def _fixture(monkeypatch, mock_louke_tools):
        module = mock_louke_tools[module_path]
        if not isinstance(module, MagicMock):
            pytest.skip(
                f"{module_path} is now implemented by Devon; "
                f"replace this mock test with a real integration test "
                f"that calls the actual module."
            )
        # Ensure sys.modules has the mocked module so that
        # ``from louke._tools.X import Y`` resolves to the mock.
        monkeypatch.setitem(sys.modules, module_path, module)
        return module

    _fixture.__name__ = module_path.rsplit(".", 1)[-1]
    return _fixture


# Expose one fixture per mockable module: ``mock_design_contract``,
# ``mock_contract_registry``, etc.
for _path in MOCK_MODULES:
    _short = _path.rsplit(".", 1)[-1]
    globals()[f"mock_{_short}"] = _make_module_fixture(_path)


# ---------------------------------------------------------------------------
# Candidate-artifact fixtures (real bytes from design-artifacts/)
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict:
    """Load a JSON file from design-artifacts; raise ``FileNotFoundError``
    if missing so the test fails loudly instead of silently skipping."""
    if not path.exists():
        raise FileNotFoundError(f"Required fixture missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def design_manifest() -> dict:
    """``design-artifact-manifest.candidate.json`` — the master manifest."""
    return _load_json(
        DESIGN_ARTIFACTS / "design-artifact-manifest.candidate.json"
    )


@pytest.fixture(scope="session")
def registry_candidate() -> dict:
    """``registry/registry.candidate.json`` — 7 machine schemas + 4 agent I/O."""
    return _load_json(DESIGN_ARTIFACTS / "registry" / "registry.candidate.json")


@pytest.fixture(scope="session")
def integration_test_contract() -> dict:
    """``contracts/integration-test.candidate.json`` instance."""
    return _load_json(
        DESIGN_ARTIFACTS / "contracts" / "integration-test.candidate.json"
    )


@pytest.fixture(scope="session")
def e2e_test_contract() -> dict:
    """``contracts/e2e-test.candidate.json`` instance."""
    return _load_json(
        DESIGN_ARTIFACTS / "contracts" / "e2e-test.candidate.json"
    )


@pytest.fixture(scope="session")
def host_facts_snapshot() -> dict:
    """``inputs/host-project-facts.snapshot.json`` — Louke dogfood facts."""
    return _load_json(
        DESIGN_ARTIFACTS / "inputs" / "host-project-facts.snapshot.json"
    )


@pytest.fixture(scope="session")
def node_host_release_fixture() -> dict:
    """``validation/release-version-node-host.valid.candidate.json``.

    NFR-0300 heterogeneous positive: same ``release-version@1.0.0`` schema
    accepts a Node/SemVer/package.json host.
    """
    return _load_json(
        DESIGN_ARTIFACTS
        / "validation"
        / "release-version-node-host.valid.candidate.json"
    )


@pytest.fixture(scope="session")
def negative_schema_fixtures() -> dict:
    """``validation/negative-schema-fixtures.candidate.json`` — 8 mutations."""
    return _load_json(
        DESIGN_ARTIFACTS
        / "validation"
        / "negative-schema-fixtures.candidate.json"
    )


# ---------------------------------------------------------------------------
# Helper: xfail-awaiting-Devon marker
# ---------------------------------------------------------------------------

def pytest_configure(config):
    """Register v0.14-002 specific markers."""
    config.addinivalue_line(
        "markers",
        "awaiting_devon(fr): test exercises an interface whose real "
        "implementation is pending; expected to xfail until Devon ships "
        "the corresponding louke._tools.* module",
    )
    config.addinivalue_line(
        "markers",
        "v014_002: v0.14-002 workflow-reflow-design integration/e2e test",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark every test under tests/integration/v014_design_contracts/."""
    for item in items:
        if "tests/integration/v014_design_contracts" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.v014_002)


# ---------------------------------------------------------------------------
# Common test data builders
# ---------------------------------------------------------------------------

@pytest.fixture
def canonical_envelope_keys() -> set[str]:
    """Required keys of every machine-contract canonical envelope (IF-CON-01)."""
    return {
        "kind",
        "identity",
        "revision",
        "schema_ref",
        "manifest_ref",
        "scope",
        "generated_by",
        "compatible_runtime",
        "artifact_refs",
        "payload",
    }


@pytest.fixture
def required_machine_schema_kinds() -> set[str]:
    """Seven required machine-contract kinds (FR-0700)."""
    return {
        "integration-test",
        "e2e-test",
        "pre-commit",
        "github-actions-ci",
        "release-version",
        "build-artifact",
        "publish-recovery",
    }


@pytest.fixture
def required_agent_io_schemas() -> list[str]:
    """Four required Agent I/O schemas (FR-1900)."""
    return [
        "louke.agent-io.archer-design-task-input",
        "louke.agent-io.archer-design-result",
        "louke.agent-io.prism-design-review-task-input",
        "louke.agent-io.prism-design-review",
    ]


@pytest.fixture
def canonical_prompt_sources() -> set[str]:
    """Closed set of canonical prompt paths (FR-1700)."""
    return {"louke/agents/Archer.md", "louke/agents/Prism.md"}
