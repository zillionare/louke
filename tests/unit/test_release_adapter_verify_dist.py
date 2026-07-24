"""AC-NFR0501-01: release artifacts must expose one canonical version."""

from __future__ import annotations

import tarfile
import zipfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest


_ADAPTER_SPEC = spec_from_file_location(
    "release_adapter_test_module", Path("tools/louke_python_release_adapter.py")
)
assert _ADAPTER_SPEC and _ADAPTER_SPEC.loader
adapter = module_from_spec(_ADAPTER_SPEC)
_ADAPTER_SPEC.loader.exec_module(adapter)


def test_verify_dist_requires_matching_wheel_and_sdist(tmp_path) -> None:
    """Artifact verification emits evidence only for matching distributions."""
    source = tmp_path / "pyproject.toml"
    source.write_text('[project]\nversion = "0.14.0"\n', encoding="utf-8")
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "louke-0.14.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("louke-0.14.0.dist-info/METADATA", "Version: 0.14.0\n")
    sdist = dist / "louke-0.14.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo("louke-0.14.0/PKG-INFO")
        payload = b"Version: 0.14.0\n"
        info.size = len(payload)
        archive.addfile(info, __import__("io").BytesIO(payload))

    result = adapter.verify_dist(source, dist, dist / "verified.json")

    assert result["version"] == "0.14.0"
    assert (dist / "verified.json").exists()


def test_verify_dist_rejects_missing_or_extra_artifacts(tmp_path) -> None:
    """Verification fails closed unless the distribution has one of each type."""
    source = tmp_path / "pyproject.toml"
    source.write_text('[project]\nversion = "0.14.0"\n', encoding="utf-8")
    dist = tmp_path / "dist"
    dist.mkdir()

    with pytest.raises(ValueError, match="exactly one wheel and one sdist"):
        adapter.verify_dist(source, dist, dist / "verified.json")


def test_verify_dist_rejects_metadata_version_drift(tmp_path) -> None:
    """Verification fails closed when an artifact embeds another version."""
    source = tmp_path / "pyproject.toml"
    source.write_text('[project]\nversion = "0.14.0"\n', encoding="utf-8")
    dist = tmp_path / "dist"
    dist.mkdir()
    wheel = dist / "louke-0.14.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("louke-0.14.0.dist-info/METADATA", "Version: 0.13.0\n")
    sdist = dist / "louke-0.14.0.tar.gz"
    with tarfile.open(sdist, "w:gz") as archive:
        info = tarfile.TarInfo("louke-0.14.0/PKG-INFO")
        payload = b"Version: 0.14.0\n"
        info.size = len(payload)
        archive.addfile(info, __import__("io").BytesIO(payload))

    with pytest.raises(ValueError, match="artifact version"):
        adapter.verify_dist(source, dist, dist / "verified.json")
