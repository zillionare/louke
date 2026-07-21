"""IF-CI-01 CI contract generation, readback and required-check aggregation.

``python -m louke._tools.ci_contract render --contract PATH --output
.github/workflows/louke-ci.yml`` renders the Louke-managed workflow as
canonical YAML — identical contract input yields identical bytes and digest.
``readback`` compares the managed file against the contract without ever
overwriting it, returning ``in_sync|missing|invalid|drifted|conflict``.  The
contract defines exactly one stable ``Louke CI / required`` aggregate that
succeeds only when every required job is exactly ``success``.  FR-1100/1200/1300.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from louke._tools import machine_contract as mc

# Required Test-Plan layers that must each land as a CI job/gate (AC-FR1100-01).
REQUIRED_LAYER_COMMAND_IDS = (
    "quality",
    "unit",
    "integration",
    "e2e",
    "build",
    "artifact-verify",
    "design-contract",
    "ac-trace",
)

# Any GitHub Actions job conclusion outside this literal is a non-success
# (AC-FR1200-01: fail/cancel/timeout/missing/illegal-skip/unknown all fail).
_SUCCESS = "success"


def _job_key(job_id: str) -> str:
    """Map a contract job id to a valid GitHub Actions job key.

    The aggregate job's id is the human-facing required-check *name*
    (``Louke CI / required``); its workflow key is the stable ``required``.
    """
    if job_id == "Louke CI / required":
        return "required"
    return job_id


def load_contract(path: Path) -> dict[str, Any]:
    """Load a github-actions-ci contract instance from ``path``."""
    return json.loads(Path(path).read_bytes())


def required_job_ids(contract: dict[str, Any]) -> list[str]:
    """Return the required job ids the aggregate check depends on."""
    payload = contract["payload"]
    aggregate = next(j for j in payload["jobs"] if j["id"] == payload["required_check"])
    return list(aggregate["needs"])


def aggregate_required(conclusions: dict[str, str], contract: dict[str, Any]) -> str:
    """Aggregate the stable required check (AC-FR1200-01).

    Returns ``success`` only when every required job reports exactly
    ``success``; a missing conclusion or any non-success literal fails closed.
    """
    for job in required_job_ids(contract):
        if conclusions.get(job) != _SUCCESS:
            return "failure"
    return _SUCCESS


def check_closure(contract: dict[str, Any]) -> dict[str, Any]:
    """Verify every required Test-Plan layer lands as a CI job (AC-FR1100-01)."""
    covered = {j.get("command_ref") for j in contract["payload"]["jobs"]}
    missing = [cid for cid in REQUIRED_LAYER_COMMAND_IDS if cid not in covered]
    return {"ok": not missing, "missing": missing}


def _command_by_ref(contract: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {c["id"]: c for c in contract["payload"]["commands"]}


def render(contract: dict[str, Any]) -> str:
    """Render the managed workflow as deterministic canonical YAML."""
    payload = contract["payload"]
    commands = _command_by_ref(contract)
    matrix = payload.get("runner_matrix", {})
    default_runner = matrix.get("default", "ubuntu-22.04")

    workflow: dict[str, Any] = {
        "name": "Louke CI",
        "on": {
            "pull_request": {},
            "push": {"branches": list(payload.get("target_branches", []))},
            "workflow_dispatch": {},
        },
        "permissions": {"contents": "read"},
        "jobs": {},
    }

    jobs: dict[str, Any] = {}
    for job in payload["jobs"]:
        key = _job_key(job["id"])
        node: dict[str, Any] = {}
        if key == "required":
            node["name"] = job["id"]
        node["runs-on"] = default_runner
        needs = [_job_key(n) for n in job.get("needs", [])]
        if needs:
            node["needs"] = needs
        node["timeout-minutes"] = job.get("timeout_minutes")
        node["permissions"] = {"contents": "read"}
        if key == "required":
            node["if"] = "always()"
            node["steps"] = [
                {
                    "name": "aggregate required jobs",
                    "run": "test '${{ contains(needs.*.result, 'failure') || "
                    "contains(needs.*.result, 'cancelled') || "
                    "contains(needs.*.result, 'skipped') }}' = 'false'",
                }
            ]
        else:
            cmd = commands.get(job["command_ref"], {})
            node["steps"] = [
                {
                    "name": job["command_ref"],
                    "run": cmd.get("command", job["command_ref"]),
                }
            ]
        jobs[key] = node
    workflow["jobs"] = jobs

    body = yaml.safe_dump(
        workflow, sort_keys=False, default_flow_style=False, width=100000
    )
    header = (
        f"# {payload['owner_marker']}\n"
        f"# contract_revision: {payload['contract_revision']}\n"
        "# generated by louke._tools.ci_contract render; do not edit by hand\n"
    )
    return header + body


def workflow_digest(text: str) -> str:
    """Return the ``sha256:`` digest of the rendered workflow bytes."""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _resolve_contract_digest(
    contract: dict[str, Any], contract_path: Path, spec_root: Path | None
) -> str | None:
    if spec_root is None:
        # <spec_root>/design-artifacts/contracts/<kind>.candidate.json
        spec_root = Path(contract_path).resolve().parents[2]
    try:
        manifest = mc.load_manifest(spec_root)
        resolved = mc.resolve_contract(contract, manifest, spec_root=spec_root)
        return resolved.contract_digest
    except mc.ContractError:
        return None


def readback(
    contract_path: Path, workflow_path: Path, *, spec_root: Path | None = None
) -> dict[str, Any]:
    """Compare the managed workflow to the contract without overwriting it."""
    contract_path = Path(contract_path)
    workflow_path = Path(workflow_path)
    contract = load_contract(contract_path)
    contract_digest = _resolve_contract_digest(contract, contract_path, spec_root)
    expected = render(contract)
    expected_digest = workflow_digest(expected)
    closure = check_closure(contract)
    checks = {"closure": closure, "commands_present": True}
    commands = [c["id"] for c in contract["payload"]["commands"]]

    if not workflow_path.is_file():
        return {
            "status": "missing",
            "contract_digest": contract_digest,
            "workflow_digest": None,
            "checks": checks,
            "commands": commands,
        }

    actual = workflow_path.read_text(encoding="utf-8")
    try:
        parsed = yaml.safe_load(actual)
    except yaml.YAMLError:
        parsed = None
    if not isinstance(parsed, dict):
        return {
            "status": "invalid",
            "contract_digest": contract_digest,
            "workflow_digest": workflow_digest(actual),
            "checks": checks,
            "commands": commands,
        }

    marker = contract["payload"]["owner_marker"]
    if marker not in actual:
        return {
            "status": "conflict",
            "contract_digest": contract_digest,
            "workflow_digest": workflow_digest(actual),
            "checks": checks,
            "commands": commands,
        }

    actual_digest = workflow_digest(actual)
    if actual_digest == expected_digest:
        return {
            "status": "in_sync",
            "contract_digest": contract_digest,
            "workflow_digest": actual_digest,
            "checks": checks,
            "commands": commands,
        }

    diff = "".join(
        difflib.unified_diff(
            expected.splitlines(keepends=True),
            actual.splitlines(keepends=True),
            fromfile="managed(expected)",
            tofile="on-disk(actual)",
        )
    )
    return {
        "status": "drifted",
        "contract_digest": contract_digest,
        "workflow_digest": actual_digest,
        "diff": diff,
        "checks": checks,
        "commands": commands,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint mirroring IF-CI-01 render/readback."""
    parser = argparse.ArgumentParser(prog="python -m louke._tools.ci_contract")
    sub = parser.add_subparsers(dest="command", required=True)

    p_render = sub.add_parser("render")
    p_render.add_argument("--contract", required=True)
    p_render.add_argument("--output", required=True)

    p_read = sub.add_parser("readback")
    p_read.add_argument("--contract", required=True)
    p_read.add_argument("--workflow", required=True)
    p_read.add_argument("--format", choices=("json",), default="json")

    args = parser.parse_args(argv)

    if args.command == "render":
        contract = load_contract(Path(args.contract))
        closure = check_closure(contract)
        if not closure["ok"]:
            print(f"contract closure incomplete: missing {closure['missing']}")
            return 1
        try:
            Path(args.output).write_text(render(contract), encoding="utf-8")
        except OSError as exc:  # pragma: no cover - persistence failure is non-zero
            print(f"cannot persist workflow: {exc}")
            return 2
        return 0

    result = readback(Path(args.contract), Path(args.workflow))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "in_sync" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
