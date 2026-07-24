"""Shared pytest configuration for ``tests/unit/web/``.

The v0.14-004 Setup gate middleware reads the v2 Setup manifest and
blocks non-allowlist routes when Setup is incomplete. Tests that
exercise the running app's handlers need a complete Setup state; the
``setup_complete`` fixture below writes a v2 complete manifest into
the test's ``tmp_path`` so the gate does not block the endpoints
under test. Tests that opt in via ``@pytest.mark.uses_setup_gate`` or
request the ``setup_complete`` fixture directly get the manifest.
Tests that exercise ``louke.web.setup_state`` in isolation should
NOT use this fixture, since it would interfere with their assertions
about corrupt / missing / unknown-schema manifests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from louke.web.setup_state import SetupManifest, SetupStatus, write_manifest


@pytest.fixture
def setup_complete(tmp_path: Path) -> Path:
    """Write a v2 complete Setup manifest into ``tmp_path/.louke/``.

    Tests that drive the running web app (via ``create_app``) should
    request this fixture so the Setup gate does not block the
    endpoints they exercise.
    """
    project_dir = tmp_path / ".louke" / "project"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "project.toml").write_text(
        '[project]\nversion = "0.8"\nspec_id = "demo"\n', encoding="utf-8"
    )
    manifest = (
        SetupManifest(
            workspace_id="ws_test",
            revision=0,
            status=SetupStatus.PENDING_USER,
        )
        .advance_to_pending_model(
            first_principal_id="prin_test",
            expected_revision=0,
        )
        .complete(
            model_check_state="passed",
            model_check_id="chk_test",
            model_check_revision=1,
            model_id="minimax/m2",
            diagnosis=None,
            observed_at="2026-07-24T00:00:00Z",
            expected_revision=1,
        )
    )
    write_manifest(tmp_path, manifest)
    return tmp_path
