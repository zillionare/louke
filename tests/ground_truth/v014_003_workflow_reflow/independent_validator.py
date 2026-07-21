"""Ground-truth validators for v0.14-003 workflow-reflow-impl tests.

HARD RULE (test-plan.md §3.2): Nothing in this package may ``import louke.*``.
Only stdlib, ``hashlib``, ``json``, ``pathlib`` and Git CLI are allowed.
Expected digests / IDs / paths must NOT be back-filled from the validator
under test (any louke Runtime validator). All expected values come from
locked spec bytes read directly by these helpers.

CI static scan enforces the no-import rule; see
``tests/ground_truth/v014_003_workflow_reflow/test_no_louke_import.py``.
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


def parse_interfaces_ids(interfaces_md: Path) -> list[str]:
    """Parse ``interfaces.md`` and return all ``IF-XXX-NN`` IDs.

    Supports:
    - Backtick-wrapped inline references: `` `IF-IMPL-01` ``
    - ATX section headers: `` ## `IF-IMPL-01` - ... ``
    """
    text = interfaces_md.read_text(encoding="utf-8")
    # Match IF-<LETTERS>-<DIGITS>; letters can be 2-7 chars (e.g. PROMPT=6, IMPL=4, RGR=3).
    pattern = re.compile(r"(?:`|#+\s*)(IF-[A-Z]{2,7}-\d{2})(?:`|\b)")
    found: list[str] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        if_id = match.group(1)
        if if_id not in seen:
            seen.add(if_id)
            found.append(if_id)
    return found


def parse_test_plan_layers(test_plan_md: Path) -> dict[str, set[str]]:
    """Parse ``test-plan.md`` §4.1 table; return ``{ac_id: {layers}}``.

    Layers are the single-letter codes ``U``/``C``/``I``/``E``/``CE``/``A``/``S``
    that appear before the ``/`` in the "Required layers" column.
    """
    text = test_plan_md.read_text(encoding="utf-8")
    rows: dict[str, set[str]] = {}
    row_pattern = re.compile(r"\|\s*`(AC-(?:FR|NFR)\d{4}-\d{2})`\s*\|[^|]*\|([^|]+)\|")
    for match in row_pattern.finditer(text):
        ac_id = match.group(1)
        layers_cell = match.group(2)
        layers: set[str] = set()
        for token in layers_cell.split("/"):
            token = token.strip()
            for letter in ("U", "C", "I", "E", "A", "S"):
                if letter in token:
                    layers.add(letter)
            if "CE" in token:
                layers.add("CE")
        if layers:
            rows[ac_id] = layers
    return rows


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


# ---------------------------------------------------------------------------
# Locked closure sets (independently derived from spec docs, not back-filled)
# ---------------------------------------------------------------------------

REQUIRED_003_INTERFACES = {
    "IF-IMPL-01",
    "IF-WFR-01",
    "IF-TASK-01",
    "IF-RGR-01",
    "IF-REV-02",
    "IF-TEST-02",
    "IF-CAND-01",
    "IF-QUAL-01",
    "IF-CI-02",
    "IF-BLD-02",
    "IF-SEC-01",
    "IF-REL-02",
    "IF-PUB-02",
    "IF-TRACE-01",
    "IF-PROMPT-02",
    "IF-MIG-01",
}

REQUIRED_INHERITED_INTERFACES = {
    "IF-PC-01",
    "IF-TST-01",
    "IF-CI-01",
    "IF-REL-01",
    "IF-BLD-01",
    "IF-PUB-01",
    "IF-PRM-01",
}

REQUIRED_FR_IDS = {f"FR-{i:04d}" for i in range(100, 3100, 100)}
REQUIRED_NFR_IDS = {f"NFR-{i:04d}" for i in range(100, 700, 100)}

REQUIRED_AC_IDS = {
    "AC-FR0100-01",
    "AC-FR0200-01",
    "AC-FR0300-01",
    "AC-FR0400-01",
    "AC-FR0500-01",
    "AC-FR0600-01",
    "AC-FR0700-01",
    "AC-FR0800-01",
    "AC-FR0900-01",
    "AC-FR1000-01",
    "AC-FR1100-01",
    "AC-FR1200-01",
    "AC-FR1300-01",
    "AC-FR1400-01",
    "AC-FR1500-01",
    "AC-FR1600-01",
    "AC-FR1700-01",
    "AC-FR1800-01",
    "AC-FR1900-01",
    "AC-FR2000-01",
    "AC-FR2100-01",
    "AC-FR2200-01",
    "AC-FR2300-01",
    "AC-FR2400-01",
    "AC-FR2500-01",
    "AC-FR2600-01",
    "AC-FR2700-01",
    "AC-FR2800-01",
    "AC-FR2900-01",
    "AC-FR3000-01",
    "AC-NFR0100-01",
    "AC-NFR0200-01",
    "AC-NFR0300-01",
    "AC-NFR0400-01",
    "AC-NFR0500-01",
    "AC-NFR0600-01",
}
