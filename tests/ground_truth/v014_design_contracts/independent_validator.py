"""Ground-truth validators for v0.14-002 design-contracts tests.

HARD RULE (test-plan.md §3.2): Nothing in this package may ``import louke.*``.
Only stdlib, ``hashlib``, ``json``, ``pathlib`` and Git CLI are allowed.
Expected digests / IDs / paths must NOT be back-filled from the validator
under test (IF-DES-02 / manifest). All expected values come from locked
fixture bytes read directly by these helpers.

CI static scan enforces the no-import rule; see
``tests/ground_truth/v014_design_contracts/test_no_louke_import.py``.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


def file_sha256(path: Path) -> str:
    """Compute SHA-256 of file bytes (UTF-8 text or raw bytes)."""
    raw = path.read_bytes()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def canonical_json_sha256(obj: Any) -> str:
    """SHA-256 of canonical JSON: UTF-8, sorted keys, no extra whitespace."""
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_acceptance_ac_ids(acceptance_md: Path) -> list[str]:
    """Parse ``acceptance.md`` and return all ``AC-FRXXXX-YY`` / ``AC-NFRXXXX-YY`` IDs.

    Independent token-based parser; does not call any louke validator.
    """
    text = acceptance_md.read_text(encoding="utf-8")
    pattern = re.compile(r"`(AC-(?:FR|NFR)\d{4}-\d{2})`")
    found: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        ac_id = match.group(1)
        if ac_id not in seen:
            seen.add(ac_id)
            found.append(ac_id)
    return found


def parse_test_plan_layers(test_plan_md: Path) -> dict[str, set[str]]:
    """Parse ``test-plan.md`` §4.1 table; return ``{ac_id: {layers}}``.

    Layers are the single-letter codes ``U``/``C``/``I``/``E`` that appear
    before the ``/`` in the "Required layers / CI" column.
    """
    text = test_plan_md.read_text(encoding="utf-8")
    rows: dict[str, set[str]] = {}
    # Match table rows like: | `AC-FR0100-01` | ... | U+C+I / ... | ... |
    row_pattern = re.compile(
        r"\|\s*`(AC-(?:FR|NFR)\d{4}-\d{2})`\s*\|[^|]*\|([^|]+)\|"
    )
    for match in row_pattern.finditer(text):
        ac_id = match.group(1)
        layers_cell = match.group(2)
        layers: set[str] = set()
        for token in layers_cell.split("/"):
            token = token.strip()
            for letter in ("U", "C", "I", "E"):
                if letter in token:
                    layers.add(letter)
        if layers:
            rows[ac_id] = layers
    return rows


def parse_interfaces_ids(interfaces_md: Path) -> list[str]:
    """Parse ``interfaces.md`` and return all ``IF-XXX-NN`` IDs.

    Supports two formats observed in the spec:
    - Backtick-wrapped inline references: `` `IF-DES-01` ``
    - ATX section headers: `` ### IF-DES-01 — ... ``
    """
    text = interfaces_md.read_text(encoding="utf-8")
    pattern = re.compile(r"(?:`|#+\s*)(IF-[A-Z]{2,3}-\d{2})(?:`|\b)")
    found: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        if_id = match.group(1)
        if if_id not in seen:
            seen.add(if_id)
            found.append(if_id)
    return found


def parse_architecture_anchors(architecture_md: Path) -> list[str]:
    """Parse ``architecture.md`` and return all ``ARC-XXX`` IDs."""
    text = architecture_md.read_text(encoding="utf-8")
    pattern = re.compile(r"`(ARC-[A-Z]+)`")
    found: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        anchor = match.group(1)
        if anchor not in seen:
            seen.add(anchor)
            found.append(anchor)
    return found


def collect_test_ac_ids(test_paths: list[Path]) -> dict[str, list[Path]]:
    """Walk test files and collect ``AC-FRXXXX-YY`` / ``AC-NFRXXXX-YY`` references.

    Returns ``{ac_id: [file_path, ...]}``. Only files with a docstring or
    comment containing an AC ID are counted.
    """
    pattern = re.compile(r"(AC-(?:FR|NFR)\d{4}-\d{2})")
    collected: dict[str, list[Path]] = {}
    for path in test_paths:
        if not path.exists():
            continue
        if path.is_dir():
            for child in path.rglob("test_*.py"):
                _collect_from_file(child, pattern, collected)
        elif path.suffix == ".py":
            _collect_from_file(path, pattern, collected)
    return collected


def _collect_from_file(
    path: Path, pattern: re.Pattern, collected: dict[str, list[Path]]
) -> None:
    text = path.read_text(encoding="utf-8")
    for match in pattern.finditer(text):
        ac_id = match.group(1)
        collected.setdefault(ac_id, []).append(path)


REQUIRED_MACHINE_SCHEMA_KINDS = {
    "integration-test",
    "e2e-test",
    "pre-commit",
    "github-actions-ci",
    "release-version",
    "build-artifact",
    "publish-recovery",
}

REQUIRED_AGENT_IO_SCHEMAS = {
    "louke.agent-io.archer-design-task-input",
    "louke.agent-io.archer-design-result",
    "louke.agent-io.prism-design-review-task-input",
    "louke.agent-io.prism-design-review",
}

REQUIRED_INTERFACES = {
    "IF-DES-01", "IF-DES-02", "IF-CON-01", "IF-REG-01", "IF-TST-01",
    "IF-PC-01", "IF-CI-01", "IF-REL-01", "IF-BLD-01", "IF-PUB-01",
    "IF-PRM-01", "IF-REV-01", "IF-WEB-01", "IF-FCT-01", "IF-AUD-01",
}

REQUIRED_ARCHITECTURE_ANCHORS = {
    "ARC-WEB", "ARC-DESIGN", "ARC-FACTS", "ARC-REGISTRY", "ARC-CONTRACTS",
    "ARC-VALIDATE", "ARC-PROMPTS", "ARC-CI", "ARC-PRECOMMIT", "ARC-VERSION",
    "ARC-BUILD", "ARC-PUBLISH", "ARC-REVIEW", "ARC-STORE", "ARC-MIGRATION",
    "ARC-SECURITY",
}

CANONICAL_PROMPT_SOURCES = {
    "louke/agents/Archer.md",
    "louke/agents/Prism.md",
}

CANONICAL_ENVELOPE_KEYS = {
    "kind", "identity", "revision", "schema_ref", "manifest_ref",
    "scope", "generated_by", "compatible_runtime", "artifact_refs",
    "payload",
}
