"""AC-FR1500-01/AC-FR1600-01: build/artifact and publish/recovery contracts.

FR-1500 (IF-BLD-01) requires the build-artifact contract to sequence version
prepare -> real build -> artifact enumeration -> digest/extract/compare ->
installed-outlet readback, and to FAIL closed on any missing/unextractable/
mismatched artifact.  FR-1600 (IF-PUB-01) requires the publish-recovery
contract to define ordered operations with stable identities, query-before-
retry, idempotency, and a retryable ``needs_attention``/``uncertain`` state on
partial or unknown provider facts (never a success conclusion).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONTRACTS = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
    / "design-artifacts"
    / "contracts"
)


def _payload(kind: str) -> dict[str, Any]:
    return json.loads((_CONTRACTS / f"{kind}.candidate.json").read_bytes())["payload"]


def test_build_artifact_declares_ordered_gate() -> None:
    """AC-FR1500-01: build-artifact sequences prepare/build/enumerate/compare/install."""
    payload = _payload("build-artifact")
    gate = payload["ordered_gate"]
    assert gate[0].startswith("prepare")
    assert any("build" in step for step in gate)
    assert any("enumerate" in step for step in gate)
    assert any("clean-install" in step for step in gate)


def test_build_artifact_requires_wheel_and_sdist_with_outlets() -> None:
    """AC-FR1500-01: exactly wheel+sdist, each required with installed outlets."""
    payload = _payload("build-artifact")
    ids = {a["id"]: a for a in payload["artifacts"]}
    assert set(ids) == {"wheel", "sdist"}
    for artifact in ids.values():
        assert artifact["required"] is True
        assert artifact["digest_algorithm"] == "sha256"
        assert artifact["installed_outlets"]


def test_build_artifact_fails_closed_on_mismatch() -> None:
    """AC-FR1500-01: source declaration cannot substitute a verified artifact."""
    policy = _payload("build-artifact")["failure_policy"]
    assert policy["fail_closed"] is True
    for reason in (
        "artifact-missing",
        "extract-failure",
        "version-mismatch",
        "outlet-mismatch",
    ):
        assert reason in policy["non_success"]


def test_publish_recovery_orders_operations_uniquely() -> None:
    """AC-FR1600-01: publish operations carry a stable order and identity."""
    payload = _payload("publish-recovery")
    orders = [op["order"] for op in payload["operations"]]
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders)
    for op in payload["operations"]:
        assert op["expected_identity"]
        assert op["query"]
        assert op["recovery"]


def test_publish_recovery_partial_success_is_needs_attention() -> None:
    """AC-FR1600-01: partial/unknown provider facts stop at needs_attention."""
    payload = _payload("publish-recovery")
    assert "needs_attention" in payload["statuses"]
    assert "uncertain" in payload["statuses"]
    assert payload["query_before_retry"] is True
    assert "needs_attention" in payload["partial_success"]


def test_publish_recovery_never_reports_success_on_uncertainty() -> None:
    """AC-FR1600-01: uncertain/needs_attention are fail-closed non-success states."""
    policy = _payload("publish-recovery")["failure_policy"]
    assert policy["fail_closed"] is True
    for reason in ("failed", "uncertain", "needs_attention"):
        assert reason in policy["non_success"]


def test_publish_recovery_idempotent_immutable_targets() -> None:
    """AC-FR1600-01: tag/registry versions are immutable, never overwritten."""
    payload = _payload("publish-recovery")
    assert "immutable" in payload["idempotency"]
    assert payload["credentials"]["PR_access"] is False
