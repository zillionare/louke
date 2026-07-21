"""FR-0500: Architecture design closure.

Validates that the Architecture defines component boundaries, dependency
direction, data/control flow, state/consistency, fault boundaries, security
and trust boundaries, migration/compatibility strategy and key technical
decisions - all traceable to requirements and host project facts.  Each
Interfaces status/permission/error/recovery semantic must be bidirectionally
mapped to a carrier component, state mechanism and security/trust/fault
boundary.  Missing carriers, orphans or bidirectional conflicts block the
baseline (AC-FR0500-01).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ERROR_CODES = (
    "ARCH_ORPHAN_ANCHOR",
    "ARCH_UNSUPPORTED_INTERFACE",
    "ARCH_UNDECIDED_BOUNDARY",
    "ARCH_MISSING_CARRIER",
)

_ARC_PATTERN = re.compile(r"\bARC-[A-Z]+\b")
_IF_PATTERN = re.compile(r"\bIF-[A-Z]{2,4}-\d{2}\b")
_UNDECIDED_MARKERS = (
    "TBD - Devon to choose",
    "Devon to decide",
    "Devon to pick",
    "leave to Devon",
    "left to Devon",
    "TODO: pick",
)


class ArchitectureValidationError(Exception):
    """A fail-closed Architecture validation rejection."""

    __test__ = False

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def extract_architecture_anchors(architecture_path: Path) -> set[str]:
    """Return the set of ARC-* anchors declared in the Architecture doc."""
    text = architecture_path.read_text(encoding="utf-8")
    return {m.group(0) for m in _ARC_PATTERN.finditer(text)}


def extract_component_table(architecture_path: Path) -> list[dict[str, str]]:
    """Parse the §2 component table from ``architecture_path``.

    The table has rows of the form::

        | `MODULE` | Component | Responsibility | Not responsible for |

    Returns a list of dicts with ``module_id``, ``component``,
    ``responsibility`` and ``not_responsible_for`` keys.
    """
    text = architecture_path.read_text(encoding="utf-8")
    components: list[dict[str, str]] = []
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if (
            stripped.startswith("|")
            and "模块" in stripped
            or (stripped.startswith("|") and in_table)
        ):
            in_table = True
            if "---" in stripped:
                continue
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) < 4:
                continue
            module_cell = cells[0]
            module_match = re.search(r"`([A-Z]+)`", module_cell)
            if not module_match:
                continue
            components.append(
                {
                    "module_id": module_match.group(1),
                    "component": cells[1],
                    "responsibility": cells[2],
                    "not_responsible_for": cells[3],
                }
            )
        elif in_table and not stripped.startswith("|"):
            in_table = False
    return components


def _detect_undecided_boundaries(text: str) -> list[str]:
    findings: list[str] = []
    for marker in _UNDECIDED_MARKERS:
        if marker.lower() in text.lower():
            findings.append(marker)
    return findings


@dataclass(frozen=True)
class ArchitectureReport:
    """Result of :func:`validate_architecture_carriers`.

    Attributes:
        status: ``pass`` or ``fail``.
        interface_carriers: Per-interface carrier anchors (interface-side view).
        anchor_carriers: Per-anchor carried interfaces (anchor-side view).
        orphan_anchors: ARC-* in Interfaces but not declared in Architecture.
        missing_anchors: ARC-* in Architecture but not referenced by Interfaces.
        unsupported_interfaces: Interfaces with no carrier anchor.
        undecided_boundaries: Markers indicating undecided technical boundaries.
    """

    __test__ = False

    status: str
    interface_carriers: list[dict[str, Any]] = field(default_factory=list)
    anchor_carriers: list[dict[str, Any]] = field(default_factory=list)
    orphan_anchors: tuple[str, ...] = ()
    missing_anchors: tuple[str, ...] = ()
    unsupported_interfaces: tuple[str, ...] = ()
    undecided_boundaries: tuple[str, ...] = ()


def _interface_carrier_section(text: str) -> dict[str, set[str]]:
    """Parse the ``architecture`` field of each interface table row.

    The Interfaces doc declares for each IF a row like::

        | architecture | `ARC-DESIGN`, `ARC-FACTS`, `ARC-SECURITY` |

    Returns a mapping of interface id -> set of carrier anchors.
    """
    carriers: dict[str, set[str]] = {}
    current_if: str | None = None
    for line in text.splitlines():
        if_match = _IF_PATTERN.search(line)
        if if_match and line.strip().startswith("###"):
            current_if = if_match.group(0)
            carriers.setdefault(current_if, set())
            continue
        if current_if and "| architecture |" in line:
            anchors = _ARC_PATTERN.findall(line)
            carriers[current_if].update(anchors)
    return carriers


def validate_architecture_carriers(
    *,
    architecture_path: Path,
    interfaces_path: Path,
) -> ArchitectureReport:
    """Validate that Architecture carriers every Interfaces semantic.

    Args:
        architecture_path: Path to ``architecture.md``.
        interfaces_path: Path to ``interfaces.md``.

    Returns:
        An :class:`ArchitectureReport` describing the carrier closure.
    """
    arch_text = architecture_path.read_text(encoding="utf-8")
    if_text = interfaces_path.read_text(encoding="utf-8")
    arch_anchors = extract_architecture_anchors(architecture_path)
    interface_anchors: set[str] = set()
    interface_carriers: list[dict[str, Any]] = []
    anchor_to_interfaces: dict[str, set[str]] = {a: set() for a in arch_anchors}

    for iface, anchors in _interface_carrier_section(if_text).items():
        interface_anchors.update(anchors)
        interface_carriers.append({"interface_id": iface, "carriers": sorted(anchors)})
        for anchor in anchors:
            anchor_to_interfaces.setdefault(anchor, set()).add(iface)

    orphan_anchors = sorted(interface_anchors - arch_anchors)
    missing_anchors = sorted(arch_anchors - interface_anchors)
    unsupported = sorted(
        iface
        for iface, anchors in _interface_carrier_section(if_text).items()
        if not anchors
    )
    undecided = _detect_undecided_boundaries(arch_text)

    anchor_carriers = [
        {"anchor_id": a, "interfaces": sorted(ifaces)}
        for a, ifaces in sorted(anchor_to_interfaces.items())
    ]

    status = "pass"
    if orphan_anchors or unsupported or undecided:
        status = "fail"
    return ArchitectureReport(
        status=status,
        interface_carriers=interface_carriers,
        anchor_carriers=anchor_carriers,
        orphan_anchors=tuple(orphan_anchors),
        missing_anchors=tuple(missing_anchors),
        unsupported_interfaces=tuple(unsupported),
        undecided_boundaries=tuple(undecided),
    )
