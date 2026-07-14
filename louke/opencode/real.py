"""Real OpenCode HTTP adapter (FR-1401, B4).

This adapter talks to a real ``opencode serve`` process over HTTP using
httpx. It implements the :class:`louke.opencode.adapter.OpenCodeAdapter`
protocol plus a small set of lifecycle helpers (``cancel``, ``probe_version``)
required by architecture §7.

Discovered OpenCode HTTP API (verified against opencode 1.17.15, B19 fix):
    POST   /api/session               -> {id, slug, projectID, ...}   create
    GET    /api/session                -> {data:[{id,...}], cursor}    list
    DELETE /api/session/{id}           -> true                         stop/end
    POST   /api/session/{id}/prompt   -> {data:{id,...}}              send
    POST   /api/session/{id}/abort    -> true                         cancel
    GET    /api/session/{id}/message   -> {data:[{id,type,content,...}], cursor}
    GET    /global/health              -> {healthy, version}           probe

B19 (issue #167) corrected the endpoints to the real ``/api`` prefix and
the response shapes to the ``{data: [...]}`` envelope actually returned
by opencode 1.17.15. The old ``/session/{id}/prompt_async`` path returned
an HTML catch-all (no such route), and ``/session/{id}/message?limit=N``
returned ``[]`` because the real list endpoint ignores query params.
"""

from __future__ import annotations

import os
import time
from typing import Any, List, Optional

import httpx

from .adapter import Instance, Message, new_id


_HEALTH_PATH = "/global/health"
_SESSION_PATH = "/api/session"
_ABORT_SUFFIX = "/abort"
_MESSAGE_SUFFIX = "/message"
_PROMPT_SUFFIX = "/prompt"

# Default model used when none is supplied. ``big-pickle`` is the free
# opencode-hosted model (no provider credentials required for the L3 smoke).
_DEFAULT_DIRECTORY = "/tmp"
_DEFAULT_PROVIDER_ID = "opencode"
_DEFAULT_MODEL_ID = "big-pickle"


def _session_path(instance_id: str, suffix: str = "") -> str:
    """Build a session-scoped URL path under ``/api/session``.

    Args:
        instance_id: The OpenCode session id.
        suffix: Optional sub-resource suffix (e.g. ``/message``).

    Returns:
        ``/api/session/{instance_id}{suffix}``.
    """
    return f"{_SESSION_PATH}/{instance_id}{suffix}"


def _parse_model_spec(model: Optional[str]) -> dict[str, str]:
    """Resolve a model full-name into the ``{providerID, id}`` opencode body.

    Accepts the opencode full-name form ``"provider/model"`` (e.g.
    ``"opencode/big-pickle"``) or an already-split ``{"providerID","id"}``
    dict-like input. Falls back to the default free model when ``model``
    is None or unparseable.

    Args:
        model: A ``"provider/model"`` full-name, or None for the default.

    Returns:
        A dict ``{"providerID": ..., "id": ...}`` suitable for the
        ``POST /api/session`` body.
    """
    if not model:
        return {"providerID": _DEFAULT_PROVIDER_ID, "id": _DEFAULT_MODEL_ID}
    if "/" in model:
        provider, _, mid = model.partition("/")
        if provider and mid:
            return {"providerID": provider, "id": mid}
    return {"providerID": _DEFAULT_PROVIDER_ID, "id": model}


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

    def create(
        self,
        *,
        correlation_id: str,
        model: Optional[str] = None,
        directory: Optional[str] = None,
    ) -> Instance:
        """Create a new OpenCode session.

        Issues ``POST /api/session`` with body
        ``{"directory": ..., "model": {"providerID": ..., "id": ...}}``.
        The server returns the new session id, slug and timestamps.

        Args:
            correlation_id: Trace id forwarded as ``x-correlation-id``.
            model: Optional model full-name (``"provider/model"``). When
                omitted, the ``OPENCODE_MODEL`` env var is consulted; when
                that is also unset, the default free model
                ``"opencode/big-pickle"`` is used.
            directory: Optional working directory for the session. Defaults
                to ``/tmp`` (or ``OPENCODE_DIRECTORY`` env var when set).

        Returns:
            An :class:`Instance` with ``status="running"`` and the
            server-assigned id.

        Raises:
            RuntimeError: If the server returns a non-2xx status or the
                transport fails. The original status code is included in the
                message so callers can distinguish 4xx from 5xx.
        """
        resolved_model = model or os.environ.get("OPENCODE_MODEL")
        resolved_dir = directory or os.environ.get(
            "OPENCODE_DIRECTORY", _DEFAULT_DIRECTORY
        )
        body = {
            "directory": resolved_dir,
            "model": _parse_model_spec(resolved_model),
        }
        resp = self._request(
            "POST", _SESSION_PATH, json=body, correlation_id=correlation_id,
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

        Issues ``GET /api/session``. The real endpoint returns an envelope
        ``{"data": [...], "cursor": {...}}``; this method flattens the
        ``data`` array into :class:`Instance` objects.

        Returns:
            A list of :class:`Instance` objects. Returns an empty list when
            the server has no sessions (this is not an error).

        Raises:
            RuntimeError: On a non-2xx response or transport failure.
        """
        resp = self._request("GET", _SESSION_PATH)
        payload = resp.json()
        items = payload.get("data", []) if isinstance(payload, dict) else payload
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

        Issues ``DELETE /api/session/{instance_id}``. The server returns
        ``true``; the session becomes unobservable afterwards.

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

        Issues ``POST /api/session/{instance_id}/prompt`` with body
        ``{"prompt": {"text": content}}``. The server returns 200 with
        ``{"data": {"id": "msg_...", ...}}`` - the admitted user message.
        The assistant reply arrives asynchronously and is observable via
        :meth:`list_messages`.

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
        body = {"prompt": {"text": content}}
        resp = self._request(
            "POST",
            _session_path(instance_id, _PROMPT_SUFFIX),
            json=body,
            correlation_id=correlation_id,
        )
        msg_id = new_id()
        try:
            data = resp.json()
            if isinstance(data, dict) and isinstance(data.get("data"), dict):
                msg_id = data["data"].get("id") or msg_id
        except ValueError:
            # Non-JSON 2xx body: keep the locally generated id.
            pass
        user_msg = Message(
            id=msg_id,
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

        Issues ``GET /api/session/{instance_id}/message``. The real endpoint
        returns ``{"data": [...], "cursor": {...}}``; each item has the
        shape ``{id, type, content: [{type:"text", text}], ...}``.

        Args:
            instance_id: The target session id.
            after_message_id: When set, only messages whose id sorts strictly
                after this cursor are returned. The adapter does this client-
                side (the server's ``cursor`` query is opaque) so callers get
                a stable "newer-than" semantic regardless of server cursor
                format.

        Returns:
            A list of :class:`Message` objects in chronological order.

        Raises:
            RuntimeError: On a non-2xx response or transport failure.
        """
        resp = self._request(
            "GET", _session_path(instance_id, _MESSAGE_SUFFIX),
        )
        payload = resp.json()
        raw_messages = (
            payload.get("data", []) if isinstance(payload, dict) else payload
        )
        messages = [_parse_message(instance_id, m) for m in raw_messages]
        if not after_message_id:
            return messages
        for i, m in enumerate(messages):
            if m.id == after_message_id:
                return messages[i + 1:]
        return messages

    def cancel(self, instance_id: str, *, correlation_id: str) -> None:
        """Cancel the current generation for a session.

        Issues ``POST /api/session/{instance_id}/abort``. This stops the
        active assistant turn without ending the session. If the server
        returns 404 (abort path not available on this build), the method
        falls back to :meth:`stop` (DELETE the session) so callers do not
        see a spurious failure during teardown of an already-ended session.

        Args:
            instance_id: The target session id.
            correlation_id: Trace id forwarded as ``x-correlation-id``.

        Raises:
            RuntimeError: On a non-2xx / non-404 response or transport failure.
        """
        try:
            self._request(
                "POST",
                _session_path(instance_id, _ABORT_SUFFIX),
                json={},
                correlation_id=correlation_id,
            )
        except RuntimeError as exc:
            if "HTTP 404" in str(exc):
                # Abort endpoint absent on this build; fall back to ending
                # the session so a missing abort route does not break
                # teardown.
                self.stop(instance_id)
                return
            raise

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
    """Flatten an OpenCode message item into a :class:`Message`.

    The real opencode 1.17.15 message shape (post-B19) is::

        {
          "id": "msg_xxx",
          "type": "assistant" | "user",
          "content": [{"type": "text", "text": "..."}, ...],
          "time": {...},
          ...
        }

    The role is read from ``type`` (values ``"assistant"`` / ``"user"``).
    The content text is the concatenation of every ``content[i].text``
    whose ``type == "text"``.

    Args:
        instance_id: The session id (taken from the request, not the body,
            so a malformed body cannot cross wires).
        raw: The raw message dict from the server.

    Returns:
        A :class:`Message` with the concatenated text parts as content.
        If the item has no text part, content is the empty string (still a
        valid message record).
    """
    parts = raw.get("content") or []
    text = "".join(
        p.get("text", "")
        for p in parts
        if isinstance(p, dict) and p.get("type") == "text"
    )
    role = raw.get("type") or "assistant"
    if role not in ("user", "assistant", "system"):
        role = "assistant"
    return Message(
        id=raw.get("id") or new_id(),
        instance_id=instance_id,
        role=role,
        kind="message",
        content=text,
        created_at=_as_epoch(raw.get("time", {}).get("created")),
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
