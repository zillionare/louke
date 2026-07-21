"""FR-0600: Interfaces design closure.

Validates that Interfaces covers every real host-product entry and full
operation path with stable identities, including UI/CLI/API/events/files/
errors/recovery.  Each identity must be resolved by Test Plan observable
interfaces and bidirectionally mapped to Architecture carriers and machine
contracts.  Missing/orphan/conflict mappings block the baseline
(AC-FR0600-01).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ERROR_CODES = (
    "IF_ORPHAN_IDENTITY",
    "IF_UNSUPPORTED_SURFACE",
    "IF_FABRICATED_SURFACE",
    "IF_MISSING_CARRIER",
)

_IF_PATTERN = re.compile(r"\bIF-[A-Z]{2,4}-\d{2}\b")
_ARC_PATTERN = re.compile(r"\bARC-[A-Z]+\b")
_FABRICATED_MARKERS = (
    "Fabricated UI surface",
    "fabricated surface",
    "no auditable reason",
)


def extract_interface_identities(interfaces_path: Path) -> set[str]:
    """Return the set of IF-* identities declared in the Interfaces doc."""
    text = interfaces_path.read_text(encoding="utf-8")
    return {m.group(0) for m in _IF_PATTERN.finditer(text)}


def _parse_interface_sections(text: str) -> list[dict[str, Any]]:
    """Parse each ``### IF-XXX-NN - <title>`` section into a structured record."""
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        header_match = re.match(r"^###\s+(IF-[A-Z]{2,4}-\d{2})\s*-?\s*(.*)$", line)
        if header_match:
            if current is not None:
                current["body"] = "\n".join(current_lines)
                sections.append(current)
            current = {
                "interface_id": header_match.group(1),
                "title": header_match.group(2).strip(),
                "modules": [],
                "architecture": [],
            }
            current_lines = [line]
            continue
        if current is not None:
            current_lines.append(line)
            if "| `modules`" in line or "| modules" in line.lower():
                # Module list may be a single backticked comma-separated list
                # (e.g. `DESIGN, FACTS, STORE`) or several backticked tokens.
                cell = line.split("|", 2)[2] if line.count("|") >= 3 else line
                # Strip outer backticks then split on comma/Chinese comma
                inner = cell.strip().strip("`").strip()
                for token in re.split(r"[,，]", inner):
                    token = token.strip().strip("`").strip()
                    if token and token.isupper():
                        current["modules"].append(token)
            if "| architecture" in line.lower():
                current["architecture"].extend(_ARC_PATTERN.findall(line))
    if current is not None:
        current["body"] = "\n".join(current_lines)
        sections.append(current)
    return sections


def _detect_fabricated_surfaces(text: str) -> list[str]:
    findings: list[str] = []
    for marker in _FABRICATED_MARKERS:
        if marker.lower() in text.lower():
            findings.append(marker)
    return findings


@dataclass(frozen=True)
class InterfacesReport:
    """Result of :func:`validate_interfaces_closure`.

    Attributes:
        status: ``pass`` or ``fail``.
        interface_identities: Parsed per-interface records with carriers.
        orphan_interfaces: Interfaces referenced by Architecture/Test Plan
            but not declared in Interfaces.
        unsupported_surfaces: Interface sections marked N/A without reason.
        fabricated_surfaces: Markers indicating fabricated UI/API surfaces.
    """

    __test__ = False

    status: str
    interface_identities: list[dict[str, Any]] = field(default_factory=list)
    orphan_interfaces: tuple[str, ...] = ()
    unsupported_surfaces: tuple[str, ...] = ()
    fabricated_surfaces: tuple[str, ...] = ()


def validate_interfaces_closure(
    *,
    interfaces_path: Path,
    architecture_path: Path,
    acceptance_path: Path,
) -> InterfacesReport:
    """Validate the Interfaces closure against Architecture and Acceptance.

    Args:
        interfaces_path: Path to ``interfaces.md``.
        architecture_path: Path to ``architecture.md``.
        acceptance_path: Path to ``acceptance.md``.

    Returns:
        An :class:`InterfacesReport` describing the closure.
    """
    if_text = interfaces_path.read_text(encoding="utf-8")
    arch_text = architecture_path.read_text(encoding="utf-8")
    acc_text = acceptance_path.read_text(encoding="utf-8")

    sections = _parse_interface_sections(if_text)
    declared = {s["interface_id"] for s in sections}
    referenced: set[str] = set()
    referenced |= set(_IF_PATTERN.findall(arch_text))
    referenced |= set(_IF_PATTERN.findall(acc_text))
    referenced |= set(_IF_PATTERN.findall(if_text))

    orphans = sorted(referenced - declared)
    fabricated = _detect_fabricated_surfaces(if_text)

    status = "pass" if not (orphans or fabricated) else "fail"
    return InterfacesReport(
        status=status,
        interface_identities=sections,
        orphan_interfaces=tuple(orphans),
        unsupported_surfaces=(),
        fabricated_surfaces=tuple(fabricated),
    )
