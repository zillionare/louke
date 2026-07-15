"""FR-1310 End User Docs save contract tests."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from starlette.testclient import TestClient

from louke.web.app import create_app


def _client(tmp_path: Path) -> TestClient:
    (tmp_path / ".louke" / "project").mkdir(parents=True)
    (tmp_path / ".louke" / "project" / "project.toml").write_text("[project]\n")
    source = Path(__file__).parents[2] / "fixtures" / "end-user-docs"
    shutil.copytree(source, tmp_path / ".louke" / "end-user-docs")
    return TestClient(create_app(tmp_path))


def test_ac_fr1310_01_canonical_root_listed(tmp_path: Path) -> None:
    """AC-FR1310-01: canonical root lists nested Markdown fixtures."""
    response = _client(tmp_path).get("/api/files?path=.louke/end-user-docs")
    assert response.status_code == 200
    assert {entry["path"] for entry in response.json()["tree"]} == {
        ".louke/end-user-docs/basic.md",
        ".louke/end-user-docs/no-trailing-newline.md",
        ".louke/end-user-docs/subdir/nested.md",
    }


def test_ac_fr1310_06_save_success_sha_roundtrip(tmp_path: Path) -> None:
    """AC-FR1310-06: saved bytes and response SHA are byte-exact."""
    client = _client(tmp_path)
    path = ".louke/end-user-docs/no-trailing-newline.md"
    loaded = client.get(f"/api/files?path={path}").json()
    body = "# saved without newline"
    response = client.post(
        "/api/files",
        json={"path": path, "body_md": body, "expected_mtime": loaded["mtime"]},
    )
    assert response.status_code == 200
    assert response.json()["sha256"] == hashlib.sha256(body.encode()).hexdigest()
    assert client.get(f"/api/files?path={path}").json()["body_md"] == body


def test_ac_fr1310_08_mtime_conflict_409_two_actions(tmp_path: Path) -> None:
    """AC-FR1310-08: stale mtime returns a conflict without overwriting."""
    client = _client(tmp_path)
    path = ".louke/end-user-docs/basic.md"
    loaded = client.get(f"/api/files?path={path}").json()
    target = tmp_path / path
    target.write_bytes(b"external")
    response = client.post(
        "/api/files",
        json={"path": path, "body_md": "mine", "expected_mtime": loaded["mtime"]},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "CONFLICT"


def test_ac_fr1310_10_path_not_allowed(tmp_path: Path) -> None:
    """AC-FR1310-10: paths outside the canonical root are rejected."""
    response = _client(tmp_path).post(
        "/api/files", json={"path": "tests/test_discuss_is_ready.py", "body_md": "x"}
    )
    assert response.status_code == 403
    assert response.json()["code"] == "PATH_NOT_ALLOWED"
