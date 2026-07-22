"""Contracts for the v0.14 hosted CI performance safeguards."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml


_WORKFLOW = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "louke-ci.yml"
)
_MANDATORY_JOBS = {
    "quality",
    "build-artifacts",
    "artifact-verify",
    "unit",
    "integration",
    "e2e-standin",
    "ac-trace",
    "install-matrix",
}
_BUILD_ARTIFACT = "louke-build-artifacts-${{ github.sha }}"


@pytest.fixture(scope="module")
def workflow() -> dict[str, Any]:
    """Load the canonical workflow as a mapping for contract assertions."""
    parsed = yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(parsed, dict)
    return parsed


def test_quality_build_and_trace_are_independent_frontier_jobs(
    workflow: dict[str, Any],
) -> None:
    """Build and trace must not wait for the slow quality job or artifact build."""
    jobs = workflow["jobs"]
    assert jobs["build-artifacts"].get("needs") in (None, [])
    assert jobs["ac-trace"].get("needs") in (None, [])


def test_concurrency_cancels_only_redundant_non_release_runs(
    workflow: dict[str, Any],
) -> None:
    """Repeated refs are coalesced without cancelling tag or release runs."""
    concurrency = workflow["concurrency"]
    assert "github.ref" in concurrency["group"]
    expression = concurrency["cancel-in-progress"]
    assert "github.ref_type != 'tag'" in expression
    assert "inputs.release == true" in expression


def test_e2e_caches_pip_and_playwright_with_locked_inputs(
    workflow: dict[str, Any],
) -> None:
    """E2E cache keys must identify its interpreter, browser and dependency lock."""
    e2e_steps = workflow["jobs"]["e2e-standin"]["steps"]
    setup = next(
        step
        for step in e2e_steps
        if step.get("uses", "").startswith("actions/setup-python")
    )
    assert setup["with"]["cache"] == "pip"
    assert "playwright-requirements.txt" in setup["with"]["cache-dependency-path"]

    cache = next(step for step in e2e_steps if step.get("id") == "playwright-cache")
    assert cache["uses"].startswith("actions/cache@")
    cache_key = cache["with"]["key"]
    assert "runner.os" in cache_key
    assert "python-version" in cache_key
    assert "playwright" in cache_key.lower()
    assert "hashFiles" in cache_key

    cache_hit_install = next(
        step
        for step in e2e_steps
        if step.get("name") == "Validate Chromium system dependencies"
    )
    assert (
        cache_hit_install["if"] == "steps.playwright-cache.outputs.cache-hit == 'true'"
    )
    assert "ldd" in cache_hit_install["run"]
    assert "--version" in cache_hit_install["run"]
    assert "if missing:" in cache_hit_install["run"]
    cache_miss_install = next(
        step
        for step in e2e_steps
        if step.get("name") == "Install Chromium and system dependencies"
    )
    assert (
        cache_miss_install["if"] == "steps.playwright-cache.outputs.cache-hit != 'true'"
    )
    assert "install --with-deps chromium" in cache_miss_install["run"]


def test_required_aggregation_and_full_matrix_remain_fail_closed(
    workflow: dict[str, Any],
) -> None:
    """Performance changes must retain every required job, suite, and matrix cell."""
    jobs = workflow["jobs"]
    assert set(jobs["required"]["needs"]) == _MANDATORY_JOBS
    assert jobs["required"]["if"] == "always()"
    assert '!= "success"' in jobs["required"]["steps"][0]["run"]

    assert jobs["unit"]["strategy"]["matrix"]["python-version"] == [
        "3.11",
        "3.12",
        "3.13",
        "3.14",
    ]
    install_matrix = jobs["install-matrix"]["strategy"]["matrix"]["include"]
    assert {(cell["os"], cell["python-version"]) for cell in install_matrix} == {
        (os, version)
        for os in ("ubuntu-22.04", "macos-14", "windows-2022")
        for version in ("3.11", "3.12", "3.13")
    }

    assert "e2e --profile all --runtime both" in jobs["e2e-standin"]["steps"][-1]["run"]
    assert any(
        "--cov-fail-under=95" in step.get("run", "") for step in jobs["unit"]["steps"]
    )


def test_all_wheel_consumers_download_sha_bound_build_artifact(
    workflow: dict[str, Any],
) -> None:
    """Every wheel consumer must use the artifact built for this commit."""
    build_steps = workflow["jobs"]["build-artifacts"]["steps"]
    upload = next(
        step
        for step in build_steps
        if step.get("uses", "").startswith("actions/upload-artifact")
    )
    assert upload["with"]["name"] == _BUILD_ARTIFACT

    consumers = (
        "artifact-verify",
        "unit",
        "integration",
        "e2e-standin",
        "install-matrix",
    )
    for job_id in consumers:
        downloads = [
            step
            for step in workflow["jobs"][job_id]["steps"]
            if step.get("uses", "").startswith("actions/download-artifact")
        ]
        assert downloads and downloads[0]["with"]["name"] == _BUILD_ARTIFACT


def test_release_paths_still_require_verified_same_run_artifacts(
    workflow: dict[str, Any],
) -> None:
    """Tag/manual real-smoke and publish gates remain behind required and verify."""
    jobs = workflow["jobs"]
    for job_id in ("real-smoke", "publish"):
        needs = set(jobs[job_id]["needs"])
        assert {"required", "build-artifacts", "artifact-verify"} <= needs
        assert "github.event_name == 'workflow_dispatch'" in jobs[job_id]["if"]
        assert "inputs.release == true" in jobs[job_id]["if"]
        assert any(
            step.get("with", {}).get("name") == _BUILD_ARTIFACT
            for step in jobs[job_id]["steps"]
            if step.get("uses", "").startswith("actions/download-artifact")
        )
