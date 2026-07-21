"""IF-PRM-01 prompt bundle manifest verification and staging readback.

The candidate prompt bundle is normative design evidence, never an active
deployment.  This module verifies the closed source set is exactly
``louke/agents/Archer.md`` + ``louke/agents/Prism.md``, recomputes the
canonical ``bundle_digest`` deterministically (per the recorded
``bundle_digest_scope``), and reads back the candidate staging render against
the recorded source/transformer/staging digests without ever writing
``.opencode/agents``.  Everything fails closed:
``PROMPT_SCOPE_DENIED|PROMPT_DRIFT|PROMPT_UNTRUSTED|PROMPT_SCHEMA_INVALID``.
FR-1700/1800/2000/2050/2100.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

CLOSED_SOURCE_SET = ("louke/agents/Archer.md", "louke/agents/Prism.md")

PROMPT_ERROR_CODES = (
    "PROMPT_SCOPE_DENIED",
    "PROMPT_DRIFT",
    "PROMPT_UNTRUSTED",
    "PROMPT_SCHEMA_INVALID",
)

_BUNDLE_NAME = "prompt-bundle.candidate.json"


class PromptBundleError(Exception):
    """Fail-closed prompt bundle error carrying a stable IF-PRM-01 code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def file_digest(data: bytes) -> str:
    """Return the ``sha256:`` digest of ``data``."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_bundle(spec_root: Path) -> dict[str, Any]:
    """Load the candidate prompt bundle manifest under ``spec_root``."""
    path = Path(spec_root) / "design-artifacts" / "prompts" / _BUNDLE_NAME
    if not path.is_file():
        raise PromptBundleError("PROMPT_SCHEMA_INVALID", f"bundle not found: {path}")
    return json.loads(path.read_bytes())


def verify_closed_set(manifest: dict[str, Any]) -> None:
    """Enforce the exact closed source set (AC-FR1700-01/AC-FR2100-01)."""
    declared = list(manifest.get("closed_source_set", []))
    if declared != list(CLOSED_SOURCE_SET):
        raise PromptBundleError(
            "PROMPT_SCOPE_DENIED",
            f"closed source set must be exactly {list(CLOSED_SOURCE_SET)}, got {declared}",
        )
    source_paths = [s["path"] for s in manifest.get("sources", [])]
    if source_paths != list(CLOSED_SOURCE_SET):
        raise PromptBundleError(
            "PROMPT_SCOPE_DENIED",
            f"bundle sources must be exactly {list(CLOSED_SOURCE_SET)}, got {source_paths}",
        )


def compute_bundle_digest(manifest: dict[str, Any]) -> str:
    """Recompute the canonical ``bundle_digest`` per ``bundle_digest_scope``.

    SHA-256 of UTF-8 lines (each with a final newline): bundle identity; one
    pipe-delimited line per ordered role of role, source digest and the exact
    input/output schema identity/version/digest; the transformer digest; then
    each ordered rendered digest.
    """
    lines: list[str] = [manifest["bundle_identity"]]
    for source in manifest["sources"]:
        inp = source["input_schema_ref"]
        out = source["output_schema_ref"]
        lines.append(
            "|".join(
                [
                    source["role"],
                    source["digest"],
                    inp["identity"],
                    inp["version"],
                    inp["digest"],
                    out["identity"],
                    out["version"],
                    out["digest"],
                ]
            )
        )
    lines.append(manifest["transformer"]["digest"])
    for deployment in manifest["deployments"]:
        lines.append(deployment["rendered_digest"])
    payload = "".join(line + "\n" for line in lines)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_bundle_digest(manifest: dict[str, Any]) -> None:
    """Fail closed when the recorded bundle digest does not recompute."""
    recomputed = compute_bundle_digest(manifest)
    if recomputed != manifest.get("bundle_digest"):
        raise PromptBundleError(
            "PROMPT_DRIFT",
            f"bundle digest drift: recomputed {recomputed} != recorded {manifest.get('bundle_digest')}",
        )


def _load_staging_record(spec_root: Path, record_rel: str) -> dict[str, Any]:
    return json.loads((Path(spec_root) / record_rel).read_bytes())


def staging_readback(
    manifest: dict[str, Any], *, spec_root: Path, repo_root: Path
) -> dict[str, Any]:
    """Read back the candidate staging render (IF-PRM-01, no active write).

    Re-reads the current source bytes, the transformer (``board.py``) and each
    staging record, and reports ``candidate_staging_in_sync|missing|drifted|
    stale`` with per-role expected/actual digests.  Never touches
    ``.opencode/agents``.
    """
    verify_closed_set(manifest)
    sources = {s["role"]: s for s in manifest["sources"]}
    transformer_expected = manifest["transformer"]["digest"]
    board_path = Path(repo_root) / manifest["transformer"]["source"]
    transformer_actual = (
        file_digest(board_path.read_bytes()) if board_path.is_file() else None
    )

    records: list[dict[str, Any]] = []
    missing = False
    drifted = False
    for deployment in manifest["deployments"]:
        role = deployment["role"]
        source = sources[role]
        source_path = Path(repo_root) / source["path"]
        source_actual = (
            file_digest(source_path.read_bytes()) if source_path.is_file() else None
        )
        staging = _load_staging_record(spec_root, deployment["record"])
        render_actual = staging["staging_readback"]["actual_rendered_digest"]
        records.append(
            {
                "role": role,
                "source_expected": source["digest"],
                "source_actual": source_actual,
                "render_expected": deployment["rendered_digest"],
                "render_actual": render_actual,
                "active_digest": staging["active_deployment"]["digest"],
            }
        )
        if source_actual is None:
            missing = True
        elif (
            source_actual != source["digest"]
            or render_actual != deployment["rendered_digest"]
        ):
            drifted = True

    if missing or transformer_actual is None:
        status = "missing"
    elif transformer_actual != transformer_expected:
        status = "stale"
    elif drifted:
        status = "drifted"
    else:
        status = "candidate_staging_in_sync"

    return {
        "bundle_identity": manifest["bundle_identity"],
        "bundle_digest": manifest["bundle_digest"],
        "readback_kind": "candidate-staging",
        "status": status,
        "active_changed": False,
        "records": records,
        "transformer_expected": transformer_expected,
        "transformer_actual": transformer_actual,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: verify + staging readback of the candidate bundle."""
    parser = argparse.ArgumentParser(prog="python -m louke._tools.prompt_bundle")
    sub = parser.add_subparsers(dest="command", required=True)
    p_read = sub.add_parser("readback")
    p_read.add_argument("--spec-root", required=True)
    p_read.add_argument("--repo-root", default=".")
    p_read.add_argument("--format", choices=("json",), default="json")
    args = parser.parse_args(argv)

    spec_root = Path(args.spec_root)
    manifest = load_bundle(spec_root)
    try:
        verify_closed_set(manifest)
        verify_bundle_digest(manifest)
    except PromptBundleError as exc:
        print(json.dumps({"error": exc.code, "message": exc.message}))
        return 1
    result = staging_readback(
        manifest, spec_root=spec_root, repo_root=Path(args.repo_root)
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "candidate_staging_in_sync" else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
