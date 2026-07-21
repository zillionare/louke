#!/usr/bin/env python3
"""Self-host release adapter for Louke's Python distribution.

This is deliberately a repository-local adapter. Louke's public release
contract is language-neutral; a host project chooses an adapter that knows how
to prepare its real version source and inspect its actual artifacts.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tarfile
import tempfile
import zipfile

from packaging.version import InvalidVersion, Version


def _version_from_tag(tag: str) -> str:
    value = str(tag or "")
    if value.startswith("v"):
        value = value[1:]
    if not value or "-dirty" in value or "+local" in value:
        raise ValueError(f"invalid release tag: {tag!r}")
    return value


def _read_project_version(source: Path) -> str:
    """Return the ``[project].version`` string from a pyproject source."""
    text = source.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^\[project\]\s*(.*?)(?=^\[|\Z)", text)
    if not match:
        raise ValueError("[project] section not found in pyproject.toml")
    version_match = re.search(
        r"(?m)^version\s*=\s*(['\"])(?P<version>.*?)\1\s*$", match.group(0)
    )
    if not version_match:
        raise ValueError("[project].version selector not found in pyproject.toml")
    return version_match.group("version")


def inspect_source(source: Path, tag: str | None = None) -> dict[str, str]:
    """Read the canonical version source (``project.version``).

    Emits ``{source, selector, version}``.  A missing selector, a non-PEP-440
    version, or a tag whose canonical form does not equal the source version is
    a hard failure (IF-REL-01).
    """
    version = _read_project_version(source)
    try:
        canonical = str(Version(version))
    except InvalidVersion as exc:
        raise ValueError(f"non-PEP-440 version source: {version!r}") from exc
    if tag is not None:
        tag_version = str(Version(_version_from_tag(tag)))
        if tag_version != canonical:
            raise ValueError(
                f"tag/source mapping mismatch: {tag_version} != {canonical}"
            )
    return {
        "source": str(source.resolve()),
        "selector": "project.version",
        "version": version,
    }


def prepare(tag: str, source: Path) -> dict[str, str]:
    """Write the tag version to the self-host pyproject version field."""
    version = _version_from_tag(tag)
    text = source.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^\[project\]\s*(.*?)(?=^\[|\Z)", text)
    if not match:
        raise ValueError("[project] section not found in pyproject.toml")
    section = match.group(0)
    version_match = re.search(r"(?m)^version\s*=\s*(['\"]).*?\1\s*$", section)
    if not version_match:
        raise ValueError("[project].version not found in pyproject.toml")
    replacement = f'version = "{version}"'
    new_section = (
        section[: version_match.start()] + replacement + section[version_match.end() :]
    )
    new_text = text[: match.start()] + new_section + text[match.end() :]
    changed = new_text != text
    if changed:
        fd, temp_name = tempfile.mkstemp(
            prefix="louke-pyproject-", dir=str(source.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(new_text)
            os.replace(temp_name, source)
        except Exception:
            try:
                os.unlink(temp_name)
            except OSError:
                pass
            raise
    return {
        "tag": tag,
        "version": version,
        "version_source": "pyproject.toml:[project].version",
        "write": "updated" if changed else "unchanged",
    }


def _metadata_version(text: str, artifact: Path) -> str:
    match = re.search(r"(?m)^Version:\s*(\S+)\s*$", text)
    if not match:
        raise ValueError(f"Version header not found in artifact: {artifact}")
    return match.group(1)


def inspect_artifact(artifact: Path) -> dict[str, str]:
    """Extract the embedded Version from a wheel or source distribution."""
    if artifact.name.endswith(".whl"):
        with zipfile.ZipFile(artifact) as archive:
            names = [
                name
                for name in archive.namelist()
                if name.endswith(".dist-info/METADATA")
            ]
            if len(names) != 1:
                raise ValueError(f"expected one wheel METADATA file in {artifact}")
            text = archive.read(names[0]).decode("utf-8", errors="replace")
    elif artifact.name.endswith(".tar.gz") or artifact.name.endswith(".tgz"):
        with tarfile.open(artifact, mode="r:gz") as archive:
            names = [
                name
                for name in archive.getnames()
                if name.endswith("/PKG-INFO") and name.count("/") == 1
            ]
            if len(names) != 1:
                raise ValueError(f"expected one sdist PKG-INFO file in {artifact}")
            member = archive.extractfile(names[0])
            if member is None:
                raise ValueError(f"could not read sdist metadata in {artifact}")
            text = member.read().decode("utf-8", errors="replace")
    else:
        raise ValueError(f"unsupported artifact type: {artifact}")
    return {
        "artifact": str(artifact.resolve()),
        "version": _metadata_version(text, artifact),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="louke_python_release_adapter")
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--tag", required=True)
    prepare_parser.add_argument("--source", type=Path, default=Path("pyproject.toml"))
    inspect_parser = sub.add_parser("inspect")
    inspect_parser.add_argument("--artifact", type=Path, required=True)
    inspect_source_parser = sub.add_parser("inspect-source")
    inspect_source_parser.add_argument(
        "--source", type=Path, default=Path("pyproject.toml")
    )
    inspect_source_parser.add_argument("--tag", default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            result = prepare(args.tag, args.source)
        elif args.command == "inspect-source":
            result = inspect_source(args.source, args.tag)
        else:
            result = inspect_artifact(args.artifact)
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        print(f"release adapter: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
