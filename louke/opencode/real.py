"""Real OpenCode HTTP adapter (FR-1401, B4).

This adapter talks to a real ``opencode serve`` process over HTTP using
httpx. It implements the :class:`louke.opencode.adapter.OpenCodeAdapter`
protocol plus a small set of lifecycle helpers (``cancel``, ``probe_version``)
required by architecture §7.

Discovered OpenCode HTTP API (verified against opencode 1.17.15):
    POST   /session                  -> {id, slug, projectID, ...}   create
    GET    /session                   -> [{id, ...}]                 list
    GET    /session/{id}              -> {id, ...} | 404             status
    DELETE /session/{id}              -> true                         stop/end
    POST   /session/{id}/prompt_async -> 204 (async, fire-and-forget) send
    POST   /session/{id}/abort        -> true                         cancel
    GET    /session/{id}/message      -> [{info:{id,role,...}, parts:[{text}]}]
    GET    /global/health             -> {healthy, version}          probe

The async ``prompt_async`` endpoint returns 204 immediately; the assistant
reply arrives later and is observable via ``list_messages``. ``send_message``
therefore returns ``(user_message, True)`` where ``True`` means the prompt was
accepted (not that the assistant has already replied).
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

import httpx

from .adapter import Instance, Message, new_id


_HEALTH_PATH = "/global/health"
_SESSION_PATH = "/session"
_ABORT_SUFFIX = "/abort"
_MESSAGE_SUFFIX = "/message"
_PROMPT_ASYNC_SUFFIX = "/prompt_async"


def _session_path(instance_id: str, suffix: str = "") -> str:
    """Build a session-scoped URL path.

    Args:
        instance_id: The OpenCode session id.
        suffix: Optional sub-resource suffix (e.g. ``/message``).

    Returns:
        ``/session/{instance_id}{suffix}``.
    """
    return f"{_SESSION_PATH}/{instance_id}{suffix}"


class RealOpenCodeAdapter:
    """HTTP adapter that talks to a real ``opencode serve`` process.

    This adapter performs real network I/O via httpx. It is NOT an in-memory
    echo: every method issues an HTTP request and surfaces transport or
    server errors as ``RuntimeError`` (never silently fakes success).

    Args:
        base_url: Base URL of the opencode server, e.g.
            ``http://127.0.0.1:41234``. Trailing slash is stripped.
        timeout: Per-request timeout in seconds.
        client: Optional pre-built httpx.Client (used by tests to inject a
            mock transport). When omitted a new client is created.

    Attributes:
        base_url: The stripped base URL.
    """

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = 5.0,
        client: Optional[httpx.Client] = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = client if client is not None else httpx.Client(timeout=timeout)

    @property
    def base_url(self) -> str:
        return self._base_url

    def create(self, *, correlation_id: str) -> Instance:
        """Create a new OpenCode session.

        Issues ``POST /session`` with an empty body; the server returns the
        new session id, slug and timestamps.

        Args:
            correlation_id: Trace id forwarded as ``x-correlation-id``.

        Returns:
            An :class:`Instance` with ``status="running"`` and the
            server-assigned id.

        Raises:
            RuntimeError: If the server returns a non-2xx status or the
                transport fails. The original status code is included in the
                message so callers can distinguish 4xx from 5xx.
        """
        resp = self._request(
            "POST", _SESSION_PATH, json={}, correlation_id=correlation_id,
        )
        data = resp.json()
        created = _as_epoch(data.get("time", {}).get("created"))
        return Instance(
            id=data["id"],
            status="running",
            created_at=created,
        )

    def list(self) -> List[Instance]:
        """List all known OpenCode sessions.

        Issues ``GET /session``.

        Returns:
            A list of :class:`Instance` objects. Returns an empty list when
            the server has no sessions (this is not an error).

        Raises:
            RuntimeError: On a non-2xx response or transport failure.
        """
        resp = self._request("GET", _SESSION_PATH)
        items = resp.json()
        return [
            Instance(
                id=item["id"],
                status="running",
                created_at=_as_epoch(item.get("time", {}).get("created")),
            )
            for item in items
        ]

    def stop(self, instance_id: str) -> Instance:
        """Stop (end) an OpenCode session.

        Issues ``DELETE /session/{instance_id}``. The session becomes
        unobservable; subsequent ``GET /session/{id}`` will 404.

        Args:
            instance_id: The session id returned by :meth:`create`.

        Returns:
            An :class:`Instance` with ``status="stopped"``.

        Raises:
            RuntimeError: On a non-2xx response (e.g. 404 if the session was
                already gone) or transport failure.
        """
        self._request("DELETE", _session_path(instance_id))
        return Instance(id=instance_id, status="stopped")

    def send_message(
        self, instance_id: str, content: str, *, correlation_id: str
    ) -> tuple[Message, bool]:
        """Send a user message to an OpenCode session.

        Issues ``POST /session/{instance_id}/prompt_async`` with a single
        text part. The async endpoint returns 204 immediately; the assistant
        reply arrives later and is observable via :meth:`list_messages`.

        Args:
            instance_id: The target session id.
            content: The user message text.
            correlation_id: Trace id forwarded as ``x-correlation-id``.

        Returns:
            A tuple ``(user_message, accepted)`` where ``user_message`` is
            the local :class:`Message` record and ``accepted`` is ``True``
            when the server acknowledged the prompt (HTTP 2xx).

        Raises:
            RuntimeError: On a non-2xx response or transport failure.
        """
        body = {"parts": [{"type": "text", "text": content}]}
        self._request(
            "POST",
            _session_path(instance_id, _PROMPT_ASYNC_SUFFIX),
            json=body,
            correlation_id=correlation_id,
        )
        user_msg = Message(
            id=new_id(),
            instance_id=instance_id,
            role="user",
            kind="message",
            content=content,
        )
        return user_msg, True

    def list_messages(
        self, instance_id: str, *, after_message_id: Optional[str]
    ) -> List[Message]:
        """List messages for an OpenCode session.

        Issues ``GET /session/{instance_id}/message``. Each OpenCode message
        is an ``{info, parts}`` envelope; the adapter flattens the first text
        part of each message into :class:`Message.content`.

        Args:
            instance_id: The target session id.
            after_message_id: When set, only messages whose id sorts strictly
                after this cursor are returned. The adapter does this client-
                side because the server's ``before`` query is cursor-based
                differently.

        Returns:
            A list of :class:`Message` objects in chronological order.

        Raises:
            RuntimeError: On a non-2xx response or transport failure.
        """
        resp = self._request(
            "GET", _session_path(instance_id, _MESSAGE_SUFFIX),
        )
        raw_messages = resp.json()
        messages = [_parse_message(instance_id, m) for m in raw_messages]
        if not after_message_id:
            return messages
        for i, m in enumerate(messages):
            if m.id == after_message_id:
                return messages[i + 1:]
        return messages

    def cancel(self, instance_id: str, *, correlation_id: str) -> None:
        """Cancel the current generation for a session.

        Issues ``POST /session/{instance_id}/abort``. This stops the active
        assistant turn without ending the session.

        Args:
            instance_id: The target session id.
            correlation_id: Trace id forwarded as ``x-correlation-id``.

        Raises:
            RuntimeError: On a non-2xx response or transport failure.
        """
        self._request(
            "POST",
            _session_path(instance_id, _ABORT_SUFFIX),
            json={},
            correlation_id=correlation_id,
        )

    def probe_version(self) -> dict[str, Any]:
        """Probe the server health and version.

        Issues ``GET /global/health``. Used by the version-probe gate before
        trusting the adapter contract.

        Returns:
            A dict with at least ``healthy`` (bool) and ``version`` (str).

        Raises:
            RuntimeError: On a non-2xx response or transport failure.
        """
        resp = self._request("GET", _HEALTH_PATH)
        return resp.json()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        correlation_id: Optional[str] = None,
    ) -> httpx.Response:
        """Issue an HTTP request and raise RuntimeError on any failure.

        Args:
            method: HTTP method (GET/POST/DELETE/...).
            path: Path under base_url, starting with ``/``.
            json: Optional JSON body.
            correlation_id: Optional trace id sent as ``x-correlation-id``.

        Returns:
            The httpx.Response on a 2xx status.

        Raises:
            RuntimeError: On transport error or non-2xx status. The message
                includes the method, path, status code and a snippet of the
                body so the caller can diagnose without re-issuing.
        """
        url = f"{self._base_url}{path}"
        headers: dict[str, str] = {}
        if correlation_id:
            headers["x-correlation-id"] = correlation_id
        try:
            resp = self._client.request(
                method, url, json=json, headers=headers, timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise RuntimeError(
                f"opencode {method} {path} transport error: {exc}"
            ) from exc
        if not resp.is_success:
            snippet = _snippet(resp)
            raise RuntimeError(
                f"opencode {method} {path} -> HTTP {resp.status_code}: {snippet}"
            )
        return resp


def _parse_message(instance_id: str, raw: dict[str, Any]) -> Message:
    """Flatten an OpenCode ``{info, parts}`` envelope into a :class:`Message`.

    Args:
        instance_id: The session id (taken from the request, not the body,
            so a malformed body cannot cross wires).
        raw: The raw message dict from the server.

    Returns:
        A :class:`Message` with the first text part as content. If the
        envelope has no text part, content is the empty string (still a
        valid message record).
    """
    info = raw.get("info", {}) or {}
    parts = raw.get("parts", []) or []
    text = ""
    for part in parts:
        if part.get("type") == "text" and part.get("text"):
            text = part["text"]
            break
    role = info.get("role") or "assistant"
    if role not in ("user", "assistant", "system"):
        role = "assistant"
    return Message(
        id=info.get("id", new_id()),
        instance_id=instance_id,
        role=role,
        kind="message",
        content=text,
        created_at=_as_epoch(info.get("time", {}).get("created")),
    )


def _as_epoch(ms: Any) -> float:
    """Convert an OpenCode millisecond timestamp to epoch seconds.

    OpenCode stores times as integer milliseconds. Fall back to ``now`` when
    the field is missing so message ordering is still monotonic.

    Args:
        ms: Milliseconds since epoch, or None.

    Returns:
        Seconds since epoch.
    """
    if ms is None:
        return time.time()
    try:
        return float(ms) / 1000.0
    except (TypeError, ValueError):
        return time.time()


def _snippet(resp: httpx.Response, limit: int = 200) -> str:
    """Return a short text snippet of a response body for error messages.

    Args:
        resp: The httpx.Response.
        limit: Maximum number of characters.

    Returns:
        The body as text (truncated). Never raises.
    """
    try:
        text = resp.text
    except Exception:
        return "<unreadable body>"
    return text if len(text) <= limit else text[:limit] + "..."
