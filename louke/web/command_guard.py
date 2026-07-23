"""Revision and idempotency guards for mutating Web commands."""

from __future__ import annotations

import json


class CommandGuard:
    """Reject stale revisions and conflicting idempotency-key payloads."""

    def __init__(self, revision: str) -> None:
        self.revision = revision
        self._payloads: dict[str, str] = {}

    def check_revision(self, revision: str) -> None:
        """Raise when a command targets an obsolete revision."""
        if revision != self.revision:
            raise ValueError("stale revision")

    def accept(self, key: str, payload: dict[str, object]) -> bool:
        """Accept a new idempotency key, or return false for an exact retry."""
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        previous = self._payloads.get(key)
        if previous is not None:
            if previous != encoded:
                raise ValueError("idempotency conflict")
            return False
        self._payloads[key] = encoded
        return True
