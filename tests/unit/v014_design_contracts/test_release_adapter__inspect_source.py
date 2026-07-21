"""AC-FR1400-01: IF-REL-01 release-version adapter ``inspect-source``.

The self-host Python adapter grows an ``inspect-source`` entry that reads the
canonical version source (``pyproject.toml`` ``[project].version``) and emits
``{source, selector:"project.version", version}``.  A missing selector, a
non-PEP-440 version, or a tag whose canonical form does not equal the source
version is a non-zero mapping failure.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[3]
_ADAPTER = _ROOT / "tools" / "louke_python_release_adapter.py"

_spec = importlib.util.spec_from_file_location("_louke_release_adapter", _ADAPTER)
assert _spec and _spec.loader
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)


def _pyproject(tmp_path: Path, version: str) -> Path:
    src = tmp_path / "pyproject.toml"
    src.write_text(
        f'[project]\nname = "demo"\nversion = "{version}"\n', encoding="utf-8"
    )
    return src


def test_inspect_source_reports_source_selector_version(tmp_path: Path) -> None:
    """AC-FR1400-01: inspect-source emits absolute source, selector, version."""
    src = _pyproject(tmp_path, "0.14.0")
    result = adapter.inspect_source(src)
    assert result["source"] == str(src.resolve())
    assert result["selector"] == "project.version"
    assert result["version"] == "0.14.0"


def test_inspect_source_missing_selector_raises(tmp_path: Path) -> None:
    """AC-FR1400-01: a source without [project].version is a hard failure."""
    src = tmp_path / "pyproject.toml"
    src.write_text('[project]\nname = "demo"\n', encoding="utf-8")
    with pytest.raises(ValueError):
        adapter.inspect_source(src)


def test_inspect_source_rejects_non_pep440(tmp_path: Path) -> None:
    """AC-FR1400-01: a non-PEP-440 version cannot be accepted as canonical."""
    src = _pyproject(tmp_path, "not-a-version")
    with pytest.raises(ValueError):
        adapter.inspect_source(src)


def test_inspect_source_tag_mapping_match(tmp_path: Path) -> None:
    """AC-FR1400-01: a tag whose canonical form equals the source passes."""
    src = _pyproject(tmp_path, "0.14.0")
    result = adapter.inspect_source(src, tag="v0.14.0")
    assert result["version"] == "0.14.0"


def test_inspect_source_tag_mapping_mismatch_raises(tmp_path: Path) -> None:
    """AC-FR1400-01: a tag that does not map to the source version fails."""
    src = _pyproject(tmp_path, "0.14.0")
    with pytest.raises(ValueError):
        adapter.inspect_source(src, tag="v0.15.0")


def test_cli_inspect_source_prints_json_and_exits_zero(tmp_path: Path) -> None:
    """AC-FR1400-01: the CLI persists JSON and exits zero on a valid source."""
    src = _pyproject(tmp_path, "0.14.0")
    proc = subprocess.run(
        [sys.executable, str(_ADAPTER), "inspect-source", "--source", str(src)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    payload = json.loads(proc.stdout)
    assert payload["selector"] == "project.version"
    assert payload["version"] == "0.14.0"


def test_cli_inspect_source_nonzero_on_bad_version(tmp_path: Path) -> None:
    """AC-FR1400-01: an invalid version source exits non-zero (fail-closed)."""
    src = _pyproject(tmp_path, "not-a-version")
    proc = subprocess.run(
        [sys.executable, str(_ADAPTER), "inspect-source", "--source", str(src)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
