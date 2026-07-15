"""Stable stage-result to badge mappings for the Runs read model."""

from __future__ import annotations

from typing import Any


STATUS_LABELS = {
    "completed": "completed",
    "current": "running",
    "waiting_for_human": "waiting",
    "blocked": "blocked",
    "failed": "failed",
    "pending": "pending",
    "skipped_by_definition": "skipped",
}
REVIEW_LABELS = {"PASS": "approved", "REJECT": "rejected", "WAIVED": "pending"}
GATE_LABELS = {"pass": "passed", "fail": "blocked"}
AUTHOR_LABELS = {"done": "done", "blocked": "blocked", "running": "running"}


def _badge(kind: str, value: Any, label: str, unknown: bool = False) -> dict[str, Any]:
    """Build the public StageBadge shape without dropping the original value."""
    return {
        "kind": kind,
        "value": str(value),
        "display_label": label,
        "unknown": unknown,
        "stale": False,
    }


def status_badge(status: Any) -> dict[str, Any]:
    """Map a graph status to a known or explicitly unknown badge."""
    value = str(status)
    label = STATUS_LABELS.get(value)
    return _badge("status", value, label or f"unknown status: {value}", label is None)


def badges_for_result(result: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Map one stage-result object to its presentation badge."""
    result = result if isinstance(result, dict) else {}
    kind = str(result.get("kind") or "")
    if kind == "review":
        value = result.get("verdict", "")
        label = REVIEW_LABELS.get(str(value))
    elif kind == "gate":
        value = result.get("verdict", "")
        label = GATE_LABELS.get(str(value))
    elif kind == "author":
        value = result.get("outcome", result.get("verdict", ""))
        label = AUTHOR_LABELS.get(str(value))
    else:
        value = kind or result.get("value", "")
        label = None
    return [
        _badge(
            kind or "result",
            value,
            label or f"unknown result kind: {value}",
            label is None,
        )
    ]
