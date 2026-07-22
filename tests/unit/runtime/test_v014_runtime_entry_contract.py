"""Unit contracts for the v0.14 Runtime entry contract bundle."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import pytest

from louke.runtime.release_contract import (
    DevelopmentBootstrapError,
    load_release_contract_bundle,
)
from louke.web.api._runtime_store import build_catalog, build_run_store


LOUKE_ROOT = Path(__file__).resolve().parents[3]


def test_v014_catalog_default_new_feature_is_the_locked_bundle_graph() -> None:
    """The Web catalog exposes the complete v0.14 graph, not the v0.12 stub."""
    catalog = build_catalog(
        workspace_root=LOUKE_ROOT,
        mode="development_bootstrap",
    )

    definition = catalog.get("new_feature", "0.14.0")

    assert definition.start_step == "M-START"
    assert [step.step_id for step in definition.steps] == [
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
    ]
    assert definition.contract_bundle_id == "louke-v0.14.0-entry-contract-bundle"
    assert definition.contract_sources == (
        "v0.14-001-workflow-reflow-spec",
        "v0.14-002-workflow-reflow-design",
        "v0.14-003-workflow-reflow-impl",
    )


def test_louke_workspace_catalog_defaults_to_bundle_without_legacy_version() -> None:
    """The Louke workspace default resolves the old request through v0.14."""
    catalog = build_catalog(workspace_root=LOUKE_ROOT)

    assert catalog.get("new_feature", "0.14.0").start_step == "M-START"
    with pytest.raises(KeyError):
        catalog.get("new_feature", "1")


def test_v014_bundle_manifest_records_current_contracts_and_bootstrap_checks() -> None:
    """The Runtime read model binds all three contracts and records skipped checks."""
    bundle = load_release_contract_bundle(
        LOUKE_ROOT,
        mode="development_bootstrap",
    )

    assert bundle.release == "0.14.0"
    assert bundle.entry_spec == "v0.14-001-workflow-reflow-spec"
    assert [entry.spec_id for entry in bundle.contracts] == [
        "v0.14-001-workflow-reflow-spec",
        "v0.14-002-workflow-reflow-design",
        "v0.14-003-workflow-reflow-impl",
    ]
    assert bundle.status == "locked"
    assert bundle.mode == "development_bootstrap"
    assert bundle.checks == {"legacy_formal_validators": "not_executed"}
    assert bundle.human_decision["entry_spec"] == "v0.14-001-workflow-reflow-spec"


def test_host_project_cannot_select_development_bootstrap(tmp_path: Path) -> None:
    """A host workspace cannot opt into Louke's bootstrap validation bypass."""
    with pytest.raises(DevelopmentBootstrapError, match="Louke workspace"):
        load_release_contract_bundle(tmp_path, mode="development_bootstrap")


def test_run_read_model_preserves_bundle_identity() -> None:
    """A run reports the three-contract bundle instead of one legacy spec id."""
    store = build_run_store(
        workspace_root=LOUKE_ROOT,
        mode="development_bootstrap",
    )
    try:
        definition = store._catalog.get("new_feature", "0.14.0")
        run = store.create_run(definition)
        payload = asdict(run)
    finally:
        store.close()

    assert payload["contract_bundle_id"] == "louke-v0.14.0-entry-contract-bundle"
    assert payload["contract_bundle_contracts"] == (
        "v0.14-001-workflow-reflow-spec",
        "v0.14-002-workflow-reflow-design",
        "v0.14-003-workflow-reflow-impl",
    )
