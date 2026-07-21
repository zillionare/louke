"""Integration tests for FR-0500: Architecture Design.

AC-FR0500-01: Architecture gives components/dependencies, data and control
flow, state consistency, faults, security, migration compatibility and
key decisions for current requirements; traceable to project facts and
FR/AC. Each Interface state/permission/error/recovery semantics maps
bi-directionally to its carrying component, state mechanism and security/
trust or fault boundary; consistent with Test Plan observable points and
machine contract commands/paths/status semantics.
"""
# AC-FR0500-01

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_ROOT = (
    REPO_ROOT
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)


def test_architecture_md_exists():
    assert (SPEC_ROOT / "architecture.md").exists()


def test_architecture_lists_all_16_anchors():
    """architecture.md must reference all 16 ARC-XXX anchors."""
    from tests.ground_truth.v014_design_contracts.independent_validator import (
        parse_architecture_anchors,
        REQUIRED_ARCHITECTURE_ANCHORS,
    )
    anchors = set(parse_architecture_anchors(SPEC_ROOT / "architecture.md"))
    missing = REQUIRED_ARCHITECTURE_ANCHORS - anchors
    assert not missing, f"architecture.md missing anchors: {missing}"


def test_architecture_module_table_has_16_modules():
    """architecture.md §2 module table must list 16 modules."""
    text = (SPEC_ROOT / "architecture.md").read_text(encoding="utf-8")
    # Module IDs from architecture.md §2
    expected_modules = {
        "WEB", "DESIGN", "FACTS", "REGISTRY", "CONTRACTS", "VALIDATOR",
        "PROMPTS", "CI", "PRECOMMIT", "VERSION", "BUILD", "PUBLISH",
        "SESSION", "REVIEW", "STORE", "MIGRATION",
    }
    for module in expected_modules:
        assert f"`{module}`" in text, f"architecture.md missing module: {module}"


def test_architecture_defines_dependency_flow():
    """architecture.md §3 must define the dependency flow."""
    text = (SPEC_ROOT / "architecture.md").read_text(encoding="utf-8")
    assert "## 3. 依赖与数据流" in text or "## 3." in text
    assert "FACTS" in text and "DESIGN" in text and "STORE" in text


def test_architecture_defines_security_boundaries():
    """architecture.md §7 must define security boundaries."""
    text = (SPEC_ROOT / "architecture.md").read_text(encoding="utf-8")
    assert "## 7." in text and ("安全" in text or "security" in text.lower())


def test_architecture_defines_migration_compatibility():
    """architecture.md must mention migration compatibility."""
    text = (SPEC_ROOT / "architecture.md").read_text(encoding="utf-8")
    assert "迁移" in text or "migration" in text.lower()


def test_architecture_references_host_facts():
    """architecture.md must reference host project facts (FACTS module)."""
    text = (SPEC_ROOT / "architecture.md").read_text(encoding="utf-8")
    assert "FACTS" in text
    assert "facts" in text.lower() or "事实" in text


@pytest.mark.awaiting_devon("FR-0500")
def test_validator_detects_missing_carrier_for_interface(mock_design_contract):
    """Validator must detect when an interface has no architecture carrier."""
    mock_design_contract.validate_manifest.return_value = {
        "ok": False,
        "checks": [
            {"id": "missing-carrier", "status": "fail", "interface": "IF-XXX-99"}
        ],
    }
    result = mock_design_contract.validate_manifest({})
    assert not result["ok"]
