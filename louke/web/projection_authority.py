"""Monotonic Runtime projection authority for web read models."""

from __future__ import annotations

from copy import deepcopy


class ProjectionAuthority:
    """Keep one latest projection and reject stale replacement attempts."""

    def __init__(self) -> None:
        self._revision: str | None = None
        self._payload: dict[str, object] | None = None

    def publish(self, revision: str, payload: dict[str, object]) -> None:
        """Publish a revision unless it is older than the current projection."""
        if self._revision is not None and revision < self._revision:
            raise ValueError("stale projection revision")
        self._revision = revision
        self._payload = deepcopy(payload)

    def read(self, revision: str) -> dict[str, object]:
        """Read the current projection only when the requested revision matches."""
        if revision != self._revision or self._payload is None:
            raise ValueError("stale projection revision")
        return deepcopy(self._payload)
