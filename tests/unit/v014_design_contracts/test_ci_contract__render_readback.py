"""AC-FR1100-01/AC-FR1200-01/AC-FR1300-01: IF-CI-01 CI contract program.

``python -m louke._tools.ci_contract render`` renders the managed workflow
canonically (same input -> same digest) and ``readback`` reports
in_sync|missing|invalid|drifted|conflict without silently overwriting human
edits.  The contract defines exactly one stable ``Louke CI / required`` check
that only succeeds when every required job is exactly success, and closure
fails if any required quality/AC-trace/build/artifact layer is missing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from louke._tools import ci_contract as ci

_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
_CONTRACT = (
    _SPEC_ROOT / "design-artifacts" / "contracts" / "github-actions-ci.candidate.json"
)


def _contract() -> dict[str, Any]:
    return json.loads(_CONTRACT.read_bytes())


def test_render_is_deterministic() -> None:
    """AC-FR1300-01: identical contract input renders identical canonical YAML."""
    first = ci.render(_contract())
    second = ci.render(_contract())
    assert first == second
    assert ci.workflow_digest(first) == ci.workflow_digest(second)


def test_render_carries_owner_marker_triggers_permissions() -> None:
    """AC-FR1100-01: managed path/marker, triggers and least-privilege perms render."""
    text = ci.render(_contract())
    assert "louke-managed:v0.14-002" in text
    assert "pull_request" in text
    assert "contents: read" in text


def test_render_defines_single_required_check() -> None:
    """AC-FR1200-01: exactly one stable aggregate ``Louke CI / required``."""
    text = ci.render(_contract())
    assert text.count("Louke CI / required") == 1
    assert "if: always()" in text


def test_required_aggregate_success_only_when_all_success() -> None:
    """AC-FR1200-01: aggregate is success only when every required job is success."""
    conclusions = {j: "success" for j in ci.required_job_ids(_contract())}
    assert ci.aggregate_required(conclusions, _contract()) == "success"


@pytest.mark.parametrize(
    "bad",
    ["failure", "cancelled", "timed_out", "skipped", "", "unknown"],
)
def test_required_aggregate_fails_on_any_non_success(bad: str) -> None:
    """AC-FR1200-01: fail/cancel/timeout/missing/illegal-skip/unknown -> failure."""
    ids = ci.required_job_ids(_contract())
    conclusions = {j: "success" for j in ids}
    conclusions[ids[0]] = bad  # one non-success job
    assert ci.aggregate_required(conclusions, _contract()) == "failure"


def test_required_aggregate_fails_on_missing_job() -> None:
    """AC-FR1200-01: a missing required job conclusion aggregates to failure."""
    ids = ci.required_job_ids(_contract())
    conclusions = {j: "success" for j in ids[1:]}  # drop first job entirely
    assert ci.aggregate_required(conclusions, _contract()) == "failure"


def test_closure_passes_for_authored_contract() -> None:
    """AC-FR1100-01: authored contract carries every required CI layer."""
    result = ci.check_closure(_contract())
    assert result["ok"] is True
    assert result["missing"] == []


def test_closure_detects_missing_required_layer() -> None:
    """AC-FR1100-01: dropping a required layer job fails closure."""
    contract = _contract()
    contract["payload"]["jobs"] = [
        j for j in contract["payload"]["jobs"] if j["command_ref"] != "ac-trace"
    ]
    result = ci.check_closure(contract)
    assert result["ok"] is False
    assert "ac-trace" in result["missing"]


def test_readback_missing_when_workflow_absent(tmp_path: Path) -> None:
    """AC-FR1300-01: absent managed workflow reads back as missing."""
    result = ci.readback(_CONTRACT, tmp_path / "louke-ci.yml", spec_root=_SPEC_ROOT)
    assert result["status"] == "missing"


def test_readback_in_sync_for_rendered_workflow(tmp_path: Path) -> None:
    """AC-FR1300-01: a freshly rendered workflow reads back in_sync."""
    out = tmp_path / "louke-ci.yml"
    out.write_text(ci.render(_contract()), encoding="utf-8")
    result = ci.readback(_CONTRACT, out, spec_root=_SPEC_ROOT)
    assert result["status"] == "in_sync"
    assert result["workflow_digest"] == ci.workflow_digest(ci.render(_contract()))


def test_readback_drifted_and_never_overwrites(tmp_path: Path) -> None:
    """AC-FR1300-01: human edits surface as drift with a diff, never overwritten."""
    out = tmp_path / "louke-ci.yml"
    out.write_text(ci.render(_contract()), encoding="utf-8")
    edited = out.read_text() + "\n# human edit\n"
    out.write_text(edited, encoding="utf-8")
    result = ci.readback(_CONTRACT, out, spec_root=_SPEC_ROOT)
    assert result["status"] == "drifted"
    assert result["diff"]
    assert out.read_text() == edited  # no silent overwrite


def test_readback_invalid_yaml(tmp_path: Path) -> None:
    """AC-FR1300-01: unparseable managed workflow reads back invalid."""
    out = tmp_path / "louke-ci.yml"
    out.write_text("name: [unterminated\n:::", encoding="utf-8")
    result = ci.readback(_CONTRACT, out, spec_root=_SPEC_ROOT)
    assert result["status"] == "invalid"


def test_cli_render_then_readback(tmp_path: Path) -> None:
    """AC-FR1300-01: CLI render persists canonical YAML that reads back in_sync."""
    out = tmp_path / "louke-ci.yml"
    code = ci.main(["render", "--contract", str(_CONTRACT), "--output", str(out)])
    assert code == 0
    assert out.is_file()
    code = ci.main(
        [
            "readback",
            "--contract",
            str(_CONTRACT),
            "--workflow",
            str(out),
            "--format",
            "json",
        ]
    )
    assert code == 0
