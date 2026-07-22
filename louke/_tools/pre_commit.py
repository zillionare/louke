"""Git pre-commit quality gates backed by Runtime quality scanners.

This module also implements IF-PC-01 pre-commit contract install/readback
verification (FR-1000): preserves existing hooks, declares install/readback/
version/quick checks/may_modify/failure semantics, forbids Archer/Devon from
executing install, and forbids ``authoritative_full_gate=true`` (pre-commit
must not be used as the Red proof or the final full-quality gate).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from .check_acs import parse_acceptance, scan_refs
from .check_assertions import scan_file

PREFIXES = (
    "feat: green",
    "fix: green",
    "refactor:",
    "fix:",
    "docs:",
    "chore:",
    "e2e:",
)
TEST_SUFFIXES = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".sh", ".bats"}

PRECOMMIT_ERROR_CODES = (
    "PRECOMMIT_INSTALL_AUTHORITY_DENIED",
    "PRECOMMIT_FULL_GATE_FORBIDDEN",
    "PRECOMMIT_DRIFT",
    "PRECOMMIT_MISSING",
    "PRECOMMIT_CONFLICT",
)

_ALLOWED_INSTALLERS = ("Runtime", "Runtime/program")


class PreCommitContractError(Exception):
    """A fail-closed pre-commit contract rejection carrying a stable code."""

    __test__ = False

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def validate_subject(subject: str) -> list[str]:
    """Return quality-gate findings for a commit subject."""
    if any(subject.startswith(prefix) for prefix in PREFIXES):
        return []
    return [f"commit subject has no allowed prefix: {subject}"]


def should_scan_ac_trace(subject: str) -> bool:
    """Return whether the subject requires AC trace validation."""
    return not subject.startswith("fix:")


def staged_test_files(filenames: list[str] | None = None) -> list[Path]:
    """Return staged test files, or pre-commit's supplied file list."""
    if filenames:
        candidates = [Path(name) for name in filenames]
    else:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
            check=False,
            capture_output=True,
            text=True,
        )
        candidates = [Path(line) for line in result.stdout.splitlines()]
    return [
        path
        for path in candidates
        if path.suffix in TEST_SUFFIXES
        and path.is_file()
        and "tests" in path.parts
        and "fixtures" not in path.parts
    ]


def run_quality_checks(subject: str, files: list[Path]) -> list[str]:
    """Run anti-pattern and, unless fixing, AC checks on staged tests."""
    findings: list[str] = []
    for path in files:
        findings.extend(_format_scan_finding(path, item) for item in scan_file(path))
    # The pre-commit stage has no commit subject. AC ownership is evaluated by
    # the commit-msg hook, where the subject is available; the pre-commit stage
    # still performs the anti-pattern scan above.
    if not subject or not should_scan_ac_trace(subject):
        return findings
    if not files:
        return findings
    acceptance_path = Path(".louke/project/specs") / _spec_id() / "acceptance.md"
    if not acceptance_path.exists():
        return findings + [f"acceptance.md not found: {acceptance_path}"]
    known = set(parse_acceptance(acceptance_path))
    result = scan_refs(
        files,
        current_version=f"v{_project_version()}",
        known_acs=known,
        first_lines_only=True,
    )
    for item in result["refs"]:
        if item["status"] in {"wrong-version", "malformed"}:
            findings.append(
                f"{item['status']}: {item['raw']} ({item['file']}:{item['line']})"
            )
        elif item["status"] == "current" and item["ac"] in result["unknown"]:
            findings.append(f"unknown AC: {item['ac']}")
    if not result["refs"]:
        findings.append("AC trace missing from staged test code")
    return findings


def _format_scan_finding(path: Path, item: dict[str, object]) -> str:
    """Format one Runtime anti-pattern finding for hook output."""
    return f"{item['code']} {path}:{item['line']}"


def _project_version() -> str:
    return _project_value("version") or "0.13.1"


def _spec_id() -> str:
    return _project_value("spec_id")


def _project_value(key: str) -> str:
    try:
        import tomllib

        data = tomllib.loads(
            Path(".louke/project/project.toml").read_text(encoding="utf-8")
        )
    except (OSError, tomllib.TOMLDecodeError):
        return ""
    return str(data.get("project", {}).get(key, ""))


# --- IF-PC-01 pre-commit contract install/readback (FR-1000) -----------------


def load_contract(contract_path: Path) -> dict[str, Any]:
    """Load a pre-commit contract instance from ``contract_path``."""
    return json.loads(Path(contract_path).read_bytes())


def verify_preserve_existing_hooks(contract: dict[str, Any]) -> None:
    """Verify the contract preserves existing hooks (AC-FR1000-01).

    Raises :class:`PreCommitContractError` if no ``preserve-existing`` hook is
    declared or if its ``may_modify`` flag is not ``True`` (preserved hooks may
    be modified only by Runtime during a managed upgrade).
    """
    payload = contract.get("payload", {})
    hooks = payload.get("hooks", [])
    preserved = next((h for h in hooks if h.get("id") == "preserve-existing"), None)
    if preserved is None:
        raise PreCommitContractError(
            "PRECOMMIT_DRIFT",
            "contract does not declare a preserve-existing hook",
        )
    if preserved.get("may_modify") is not True:
        raise PreCommitContractError(
            "PRECOMMIT_CONFLICT",
            "preserve-existing hook must allow may_modify=true for managed upgrade",
        )


def verify_no_full_gate_claim(contract: dict[str, Any]) -> None:
    """Verify the contract does not claim authoritative full-quality gate.

    Pre-commit is a fast local gate only; the Red proof and the final full
    quality gate are not pre-commit's responsibility (AC-FR1000-01).
    """
    payload = contract.get("payload", {})
    if payload.get("authoritative_full_gate") is True:
        raise PreCommitContractError(
            "PRECOMMIT_FULL_GATE_FORBIDDEN",
            "pre-commit contract must not claim authoritative_full_gate=true",
        )


def verify_install_authority(contract: dict[str, Any], *, installer: str) -> None:
    """Verify the install authority is Runtime, not Archer/Devon.

    Args:
        contract: The pre-commit contract instance.
        installer: The actor attempting the install (e.g. ``Runtime``,
            ``Archer``, ``Devon``).

    Raises:
        PreCommitContractError: With ``PRECOMMIT_INSTALL_AUTHORITY_DENIED``
            if the installer is not Runtime.
    """
    if installer not in _ALLOWED_INSTALLERS:
        raise PreCommitContractError(
            "PRECOMMIT_INSTALL_AUTHORITY_DENIED",
            f"installer {installer!r} is not authorised; only Runtime may install",
        )


def parse_existing_hook_snapshot(contract: dict[str, Any]) -> dict[str, Any]:
    """Return the existing-hook snapshot declared in the contract."""
    payload = contract.get("payload", {})
    snapshot = payload.get("existing_hook_snapshot", {})
    if not snapshot:
        raise PreCommitContractError(
            "PRECOMMIT_MISSING",
            "contract has no existing_hook_snapshot",
        )
    return dict(snapshot)


def aggregate_readback(
    contract: dict[str, Any],
    *,
    config_path: Path,
    installed_stages: list[str],
) -> dict[str, Any]:
    """Aggregate the pre-commit readback status (AC-FR1000-01).

    Args:
        contract: The pre-commit contract instance.
        config_path: Path to the managed config file (``.pre-commit-config.yaml``).
        installed_stages: List of installed hook stages (e.g. ``["pre-commit"]``).

    Returns:
        A dict with ``status`` in ``in_sync|drifted|missing|conflict`` and
        ``contract_revision`` / ``installed_stages`` fields.
    """
    payload = contract.get("payload", {})
    expected_stages = list(payload.get("stages", []))
    config_path = Path(config_path)
    if not config_path.is_file():
        return {
            "status": "missing",
            "contract_revision": contract.get("revision"),
            "expected_stages": expected_stages,
            "installed_stages": list(installed_stages),
        }
    missing_stages = [s for s in expected_stages if s not in installed_stages]
    if missing_stages:
        return {
            "status": "drifted",
            "contract_revision": contract.get("revision"),
            "expected_stages": expected_stages,
            "installed_stages": list(installed_stages),
            "missing_stages": missing_stages,
        }
    return {
        "status": "in_sync",
        "contract_revision": contract.get("revision"),
        "expected_stages": expected_stages,
        "installed_stages": list(installed_stages),
    }


def main(argv: list[str] | None = None) -> int:
    """Run the hook selected by pre-commit and return a process status."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--hook", choices=("pre-commit", "commit-msg"), required=True)
    parser.add_argument("filenames", nargs="*")
    args = parser.parse_args(argv)
    subject = ""
    if args.hook == "commit-msg":
        if not args.filenames:
            return 2
        subject = Path(args.filenames[0]).read_text(encoding="utf-8").splitlines()[0]
        findings = validate_subject(subject)
        findings.extend(run_quality_checks(subject, staged_test_files()))
    else:
        findings = run_quality_checks("", staged_test_files(args.filenames))
    for finding in findings:
        print(f"[REJECT] {finding}", file=sys.stderr)
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
