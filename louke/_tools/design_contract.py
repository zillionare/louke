"""IF-DES-02 unified design validation result (FR-2600).

``python -m louke._tools.design_contract validate --manifest PATH --format json
--output PATH`` runs the design-program gate over the external design-artifact
manifest and emits a stable-check envelope.  Any missing/orphan/conflict returns
a stable check ID localised to FR/AC/interface/architecture/contract and blocks
the baseline.  While the registry is candidate, ``DESIGN.SCHEMA.ACTIVE`` fails
closed.  Secrets are never echoed — only paths and redacted fingerprints.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from louke._tools import contract_registry as reg
from louke._tools import machine_contract as mc

STABLE_CHECK_IDS = (
    "DESIGN.TRACE.CLOSURE",
    "DESIGN.INTERFACE.RESOLUTION",
    "DESIGN.ARCH.CARRIER",
    "DESIGN.CONTRACT.PARITY",
    "DESIGN.SCHEMA.ACTIVE",
    "DESIGN.PROMPT.PARITY",
    "DESIGN.DISCUSSION.OPEN",
    "DESIGN.DIFF.SCOPE",
    "DESIGN.SECRET",
)

_SECRET_PATTERNS = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(password|secret|token)\s*[:=]\s*['\"][^'\"]{8,}['\"]"),
)


def _check(
    check_id: str,
    status: str,
    *,
    remediation: str,
    retryable: bool = True,
    artifact_path: str | None = None,
    field: str | None = None,
    expected: Any = None,
    actual: Any = None,
    fr_ids: list[str] | None = None,
    ac_ids: list[str] | None = None,
    interface_ids: list[str] | None = None,
    architecture_anchors: list[str] | None = None,
    contract_refs: list[str] | None = None,
    prompt_identity: str | None = None,
) -> dict[str, Any]:
    check: dict[str, Any] = {
        "check_id": check_id,
        "status": status,
        "fr_ids": fr_ids or [],
        "ac_ids": ac_ids or [],
        "interface_ids": interface_ids or [],
        "architecture_anchors": architecture_anchors or [],
        "contract_refs": contract_refs or [],
        "retryable": retryable,
        "remediation": remediation,
    }
    if artifact_path is not None:
        check["artifact_path"] = artifact_path
    if field is not None:
        check["field"] = field
    if expected is not None:
        check["expected"] = expected
    if actual is not None:
        check["actual"] = actual
    if prompt_identity is not None:
        check["prompt_identity"] = prompt_identity
    return check


def _check_trace_closure(manifest: dict[str, Any]) -> dict[str, Any]:
    ac_closure = manifest.get("ac_closure", [])
    expected = manifest.get("closure_counts", {}).get("acceptance", len(ac_closure))
    actual = len(ac_closure)
    ac_ids = sorted({e["ac"] for e in ac_closure})
    if actual != expected:
        return _check(
            "DESIGN.TRACE.CLOSURE",
            "fail",
            expected=expected,
            actual=actual,
            ac_ids=ac_ids,
            remediation="restore every required AC closure entry before baseline",
        )
    return _check(
        "DESIGN.TRACE.CLOSURE",
        "pass",
        expected=expected,
        actual=actual,
        ac_ids=ac_ids,
        remediation="trace closure complete",
    )


def _check_interface_resolution(manifest: dict[str, Any]) -> dict[str, Any]:
    known = set(manifest.get("interface_set", []))
    orphans: dict[str, list[str]] = {}
    for entry in manifest.get("ac_closure", []):
        for iface in entry.get("if", []):
            if iface not in known:
                orphans.setdefault(iface, []).append(entry["ac"])
    if orphans:
        return _check(
            "DESIGN.INTERFACE.RESOLUTION",
            "fail",
            interface_ids=sorted(orphans),
            ac_ids=sorted({ac for acs in orphans.values() for ac in acs}),
            remediation="every referenced interface must resolve to a real Interfaces identity",
        )
    return _check(
        "DESIGN.INTERFACE.RESOLUTION",
        "pass",
        interface_ids=sorted(known),
        remediation="all interface references resolve",
    )


def _check_arch_carrier(manifest: dict[str, Any]) -> dict[str, Any]:
    known = set(manifest.get("architecture_anchor_set", []))
    orphans: dict[str, list[str]] = {}
    for entry in manifest.get("ac_closure", []):
        for anchor in entry.get("arc", []):
            if anchor not in known:
                orphans.setdefault(anchor, []).append(entry["ac"])
    if orphans:
        return _check(
            "DESIGN.ARCH.CARRIER",
            "fail",
            architecture_anchors=sorted(orphans),
            ac_ids=sorted({ac for acs in orphans.values() for ac in acs}),
            remediation="every interface semantic must be carried by a real Architecture anchor",
        )
    return _check(
        "DESIGN.ARCH.CARRIER",
        "pass",
        architecture_anchors=sorted(known),
        remediation="all architecture anchors carry their interfaces",
    )


def _check_contract_parity(manifest: dict[str, Any], spec_root: Path) -> dict[str, Any]:
    view = {s["identity"]: s for s in reg.discover().schemas}
    refs: list[str] = []
    for entry in manifest.get("contract_instances", []):
        kind = entry["kind"]
        refs.append(kind)
        identity = f"louke.machine-contract.{kind}"
        packaged = view.get(identity, {}).get("digest")
        instance = json.loads((Path(spec_root) / entry["path"]).read_bytes())
        ref = reg.SchemaRef(identity, "1.0.0", packaged)
        result = reg.validate(ref, json.dumps(instance).encode("utf-8"))
        if not result.valid:
            return _check(
                "DESIGN.CONTRACT.PARITY",
                "fail",
                artifact_path=entry["path"],
                contract_refs=refs,
                remediation=f"{kind} instance does not validate against its active schema",
            )
        try:
            mc.verify_provenance(instance, manifest, spec_root=spec_root)
        except mc.ContractError as exc:
            return _check(
                "DESIGN.CONTRACT.PARITY",
                "fail",
                artifact_path=entry["path"],
                field=exc.code,
                contract_refs=refs,
                remediation="contract provenance must resolve to declared kind/path/bytes",
            )
    return _check(
        "DESIGN.CONTRACT.PARITY",
        "pass",
        contract_refs=refs,
        remediation="all contract instances validate against active schemas with resolved provenance",
    )


def _check_schema_active() -> dict[str, Any]:
    registry = reg.load_registry()
    non_active = [
        s["identity"] for s in reg._all_entries(registry) if s.get("status") != "active"
    ]
    if non_active:
        return _check(
            "DESIGN.SCHEMA.ACTIVE",
            "fail",
            expected="active",
            actual=registry.get("activation_state"),
            contract_refs=sorted(non_active),
            remediation="close the atomic activation gate before baseline; resolve returns SCHEMA_NOT_ACTIVE",
        )
    return _check("DESIGN.SCHEMA.ACTIVE", "pass", remediation="registry is active")


def _check_prompt_parity(manifest: dict[str, Any]) -> dict[str, Any]:
    prompts = manifest.get("prompt_candidates", {})
    bundle = prompts.get("bundle", {})
    binding = prompts.get("reviewer_binding", {})
    if bundle.get("bundle_digest") and bundle["bundle_digest"] == binding.get(
        "reviewed_candidate_bundle_digest"
    ):
        return _check(
            "DESIGN.PROMPT.PARITY",
            "pass",
            prompt_identity=bundle.get("identity"),
            remediation="prompt bundle matches the reviewed candidate binding",
        )
    return _check(
        "DESIGN.PROMPT.PARITY",
        "fail",
        prompt_identity=bundle.get("identity"),
        remediation="prompt bundle digest must match the reviewed candidate binding",
    )


def _check_discussion_open(manifest: dict[str, Any]) -> dict[str, Any]:
    open_threads = manifest.get("open_discussions", [])
    if open_threads:
        return _check(
            "DESIGN.DISCUSSION.OPEN",
            "fail",
            actual=len(open_threads),
            remediation="resolve every open design discussion before baseline",
        )
    return _check(
        "DESIGN.DISCUSSION.OPEN", "pass", remediation="no open design discussions"
    )


def _check_diff_scope(manifest: dict[str, Any]) -> dict[str, Any]:
    out_of_scope = manifest.get("out_of_scope_diffs", [])
    if out_of_scope:
        return _check(
            "DESIGN.DIFF.SCOPE",
            "fail",
            actual=out_of_scope,
            remediation="design edits must stay inside the authorised write set",
        )
    return _check(
        "DESIGN.DIFF.SCOPE",
        "pass",
        remediation="all edits within the authorised write set",
    )


def _check_secret(manifest: dict[str, Any], spec_root: Path) -> dict[str, Any]:
    hits: list[str] = []
    for entry in manifest.get("contract_instances", []) + manifest.get(
        "input_artifacts", []
    ):
        path = Path(spec_root) / entry["path"]
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in _SECRET_PATTERNS:
            if pattern.search(text):
                fingerprint = hashlib.sha256(pattern.pattern.encode()).hexdigest()[:12]
                hits.append(f"{entry['path']}#{fingerprint}")
    if hits:
        return _check(
            "DESIGN.SECRET",
            "fail",
            artifact_path=hits[0].split("#")[0],
            remediation="remove detected secrets; evidence records only path and redacted fingerprint",
        )
    return _check(
        "DESIGN.SECRET", "pass", remediation="no secrets detected in design artifacts"
    )


def run(manifest: dict[str, Any], *, spec_root: Path) -> dict[str, Any]:
    """Run every design-program check and return the IF-DES-02 result envelope."""
    checks = [
        _check_trace_closure(manifest),
        _check_interface_resolution(manifest),
        _check_arch_carrier(manifest),
        _check_contract_parity(manifest, spec_root),
        _check_schema_active(),
        _check_prompt_parity(manifest),
        _check_discussion_open(manifest),
        _check_diff_scope(manifest),
        _check_secret(manifest, spec_root),
    ]
    status = "pass" if all(c["status"] == "pass" for c in checks) else "fail"
    revision_id = manifest.get("manifest_revision", "")
    evidence_digest = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(checks, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )
    return {
        "status": status,
        "revision_id": revision_id,
        "checks": checks,
        "evidence_digest": evidence_digest,
    }


def validate_manifest(
    manifest_path: Path, *, spec_root: Path | None = None
) -> dict[str, Any]:
    """Load ``manifest_path`` and run the design-program gate."""
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_bytes())
    if spec_root is None:
        # manifest lives at <spec_root>/design-artifacts/<manifest>
        spec_root = manifest_path.parent.parent
    return run(manifest, spec_root=spec_root)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint mirroring IF-DES-02."""
    parser = argparse.ArgumentParser(prog="python -m louke._tools.design_contract")
    sub = parser.add_subparsers(dest="command", required=True)
    p_val = sub.add_parser("validate")
    p_val.add_argument("--manifest", required=True)
    p_val.add_argument("--format", choices=("json",), default="json")
    p_val.add_argument("--output", default=None)
    args = parser.parse_args(argv)

    result = validate_manifest(Path(args.manifest))
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        try:
            Path(args.output).write_text(payload + "\n", encoding="utf-8")
        except OSError as exc:  # pragma: no cover - persistence failure is non-zero
            print(f"cannot persist evidence: {exc}")
            return 2
    else:
        print(payload)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
