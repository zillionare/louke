"""Real OpenCode HTTP adapter (FR-1401, B4).

This adapter talks to a real ``opencode serve`` process over HTTP using
httpx. It implements the :class:`louke.opencode.adapter.OpenCodeAdapter`
protocol plus a small set of lifecycle helpers (``cancel``, ``probe_version``)
required by architecture §7.

Discovered OpenCode HTTP API (verified against opencode 1.17.15 and 1.18.1):
    POST   /api/session               -> {id, slug, projectID, ...}   create
    GET    /api/session                -> {data:[{id,...}], cursor}    list
    DELETE /api/session/{id}           -> true                         stop/end
    POST   /api/session/{id}/prompt   -> {data:{id,...}}              send
    POST   /api/session/{id}/abort    -> true                         cancel
    GET    /api/session/{id}/message   -> {data:[{id,type,content,...}], cursor}
    GET    /global/health              -> {healthy, version}           probe
    GET    /api/agent                  -> {data:[{id, model, ...}]}     Agent catalog
    POST   /api/session/{id}/agent     -> 204                          select Agent
    POST   /api/session/{id}/model     -> 204                          select model

B19 (issue #167) corrected the endpoints to the real ``/api`` prefix and
the response shapes to the ``{data: [...]}`` envelope actually returned
by opencode 1.17.15. The old ``/session/{id}/prompt_async`` path returned
an HTML catch-all (no such route), and ``/session/{id}/message?limit=N``
returned ``[]`` because the real list endpoint ignores query params.

OpenCode 1.18.1 keeps these HTTP endpoints and emits assistant streaming
events from ``/event`` using ``session.next.text.started``,
``session.next.text.delta``, ``session.next.text.ended``,
``session.next.step.ended`` and ``session.next.step.failed`` event types.
"""

from __future__ import annotations

import os
import json
import time
from typing import Any, Iterator, List, Optional

import httpx

from .adapter import (
    Instance,
    Message,
    ProviderResult,
    SessionReconcile,
    StreamEvent,
    new_id,
)


_HEALTH_PATH = "/global/health"
_SESSION_PATH = "/api/session"
_AGENT_PATH = "/api/agent"
_ABORT_SUFFIX = "/abort"
_AGENT_SUFFIX = "/agent"
_MODEL_SUFFIX = "/model"
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
            mock transport). When omitted a new client is created with
            environment proxy settings disabled for the managed loopback
            service.

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
        if client is None:
            client = httpx.Client(timeout=timeout, trust_env=False)
        self._client = client

    @property
    def base_url(self) -> str:
        return self._base_url

    def create(
        self,
        *,
        correlation_id: str,
        model: Optional[str] = None,
        directory: Optional[str] = None,
        agent: Optional[str] = None,
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
        agent: Optional OpenCode Agent id. When set, the adapter resolves
                its concrete model from ``GET /api/agent`` and configures the
                new session with the Agent and model switch endpoints before
                returning it. A failed setup stops the new session.

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
        body = {"directory": resolved_dir}
        # In managed Louke servers, allow OpenCode's own config to select the
        # model (for example the user's local m3 provider). Unit callers retain
        # the historical free-model default unless this switch is explicit.
        if resolved_model or os.environ.get("LOUKE_OPENCODE_USE_SERVER_DEFAULT") != "1":
            body["model"] = _parse_model_spec(resolved_model)
        resp = self._request(
            "POST",
            _SESSION_PATH,
            json=body,
            correlation_id=correlation_id,
        )
        data = resp.json()
        inner = data.get("data", data) if isinstance(data, dict) else data
        created = _as_epoch(inner.get("time", {}).get("created"))
        instance = Instance(
            id=inner["id"],
            status="running",
            created_at=created,
        )
        if agent is not None:
            self._configure_agent(instance.id, agent)
        return instance

    def _configure_agent(self, instance_id: str, agent: str) -> None:
        """Configure a new session with a validated OpenCode Agent and model.

        Args:
            instance_id: The newly-created OpenCode session id.
            agent: The exact lowercase Agent id from the generated roster.

        Raises:
            RuntimeError: If the Agent is unavailable, its model is invalid,
                configuration fails, or cleanup after failure fails.
        """
        try:
            model = self._resolve_agent_model(agent)
            self._request(
                "POST",
                _session_path(instance_id, _AGENT_SUFFIX),
                json={"agent": agent},
            )
            self._request(
                "POST",
                _session_path(instance_id, _MODEL_SUFFIX),
                json={"model": model},
            )
        except RuntimeError as exc:
            try:
                self.stop(instance_id)
            except RuntimeError as cleanup_exc:
                raise RuntimeError(
                    f"OpenCode agent setup failed for {agent!r}: {exc}; "
                    f"session cleanup failed: {cleanup_exc}"
                ) from exc
            raise RuntimeError(
                f"OpenCode agent setup failed for {agent!r}: {exc}"
            ) from exc

    def _resolve_agent_model(self, agent: str) -> dict[str, str]:
        """Resolve an Agent id to its concrete provider/model pair.

        Args:
            agent: The exact Agent id requested by the caller.

        Returns:
            A model object suitable for ``POST /api/session/{id}/model``.

        Raises:
            RuntimeError: If the Agent is absent or does not expose both model
                provider and id fields.
        """
        if not agent.strip():
            raise RuntimeError("selected OpenCode agent id must not be empty")
        response = self._request("GET", _AGENT_PATH)
        agents = _unwrap_data_envelope(response.json())
        selected = next((item for item in agents if item.get("id") == agent), None)
        if selected is None:
            raise RuntimeError(f"agent {agent!r} was not found in /api/agent")
        raw_model = selected.get("model")
        if not isinstance(raw_model, dict):
            raise RuntimeError(f"agent {agent!r} has no concrete model")
        provider_id = raw_model.get("providerID")
        model_id = raw_model.get("id")
        if not isinstance(provider_id, str) or not provider_id.strip():
            raise RuntimeError(f"agent {agent!r} model is missing providerID")
        if not isinstance(model_id, str) or not model_id.strip():
            raise RuntimeError(f"agent {agent!r} model is missing id")
        return {"providerID": provider_id, "id": model_id}

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
        items = _unwrap_data_envelope(resp.json())
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
        except ValueError:
            # Non-JSON 2xx body: keep the locally generated id and accept.
            data = None
        if isinstance(data, dict) and isinstance(data.get("data"), dict):
            msg_id = data["data"].get("id") or msg_id
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
            "GET",
            _session_path(instance_id, _MESSAGE_SUFFIX),
        )
        raw_messages = _unwrap_data_envelope(resp.json())
        messages = [_parse_message(instance_id, m) for m in raw_messages]
        if not after_message_id:
            return messages
        for i, m in enumerate(messages):
            if m.id == after_message_id:
                return messages[i + 1 :]
        return messages

    def stream_events(
        self, instance_id: str, last_event_id: Optional[str] = None
    ) -> Iterator[StreamEvent]:
        """Yield normalized events from OpenCode's project-level ``/event`` SSE.

        Args:
            instance_id: Only events belonging to this OpenCode session are
                yielded.
            last_event_id: Optional SSE cursor sent as ``Last-Event-ID``.

        Yields:
            ``delta``, terminal ``completed``, or provider ``error`` events.

        Raises:
            RuntimeError: If the SSE endpoint or an authoritative terminal
                message request fails.
        """
        assistant_messages: set[str] = set()
        text_parts: set[str] = set()
        with self._client.stream(
            "GET",
            f"{self._base_url}/event",
            headers={"Last-Event-ID": last_event_id} if last_event_id else None,
            timeout=None,
        ) as response:
            if not response.is_success:
                raise RuntimeError(
                    f"opencode GET /event -> HTTP {response.status_code}: {_snippet(response)}"
                )
            if "text/event-stream" not in response.headers.get("content-type", ""):
                raise RuntimeError(
                    "opencode GET /event did not return text/event-stream"
                )
            for raw in response.iter_lines():
                if not raw or not raw.startswith("data:"):
                    continue
                try:
                    event = json.loads(raw[5:].strip())
                except json.JSONDecodeError:
                    continue
                event_id = str(event.get("id") or new_id())
                event_type = event.get("type")
                data = event.get("data") or event.get("properties") or {}
                next_event = self._normalize_next_event(
                    event_type,
                    data,
                    event_id,
                    instance_id,
                    assistant_messages,
                    text_parts,
                )
                if next_event is not None:
                    yield next_event
                    continue
                if event_type == "message.updated":
                    if data.get("sessionID") != instance_id:
                        continue
                    info = data.get("info") or {}
                    if info.get("role") == "assistant" and info.get("id"):
                        assistant_messages.add(str(info["id"]))
                    continue
                if event_type == "message.part.updated":
                    if data.get("sessionID") != instance_id:
                        continue
                    part = data.get("part") or {}
                    if part.get("type") == "text" and part.get("id"):
                        message_id = part.get("messageID") or part.get("messageId")
                        if message_id in assistant_messages:
                            text_parts.add(str(part["id"]))
                    continue
                if event_type == "message.part.delta":
                    if (
                        data.get("sessionID") != instance_id
                        or data.get("field") != "text"
                    ):
                        continue
                    if data.get("messageID") not in assistant_messages:
                        continue
                    if data.get("partID") not in text_parts:
                        continue
                    yield StreamEvent(
                        event_id=event_id,
                        type="delta",
                        message_id=str(data["messageID"]),
                        delta=str(data.get("delta") or ""),
                    )
                    continue
                if (
                    event_type == "session.idle"
                    and data.get("sessionID") == instance_id
                ):
                    messages = self.list_messages(instance_id, after_message_id=None)
                    assistant = next(
                        (m for m in reversed(messages) if m.role == "assistant"), None
                    )
                    if assistant is not None:
                        yield StreamEvent(
                            event_id=event_id,
                            type="completed",
                            message_id=assistant.id,
                            content=assistant.content,
                        )
                    continue
                if (
                    event_type == "session.error"
                    and data.get("sessionID") == instance_id
                ):
                    error = data.get("error") or "OpenCode session error"
                    yield StreamEvent(
                        event_id=event_id,
                        type="error",
                        message_id=next(iter(assistant_messages), ""),
                        error=str(error),
                    )

    def _normalize_next_event(
        self,
        event_type: str,
        data: dict[str, Any],
        event_id: str,
        instance_id: str,
        assistant_messages: set[str],
        text_parts: set[str],
    ) -> Optional[StreamEvent]:
        """Normalize one OpenCode 1.18.1 ``session.next`` event.

        Args:
            event_type: The SSE event type.
            data: The event's ``properties`` or legacy ``data`` object.
            event_id: The SSE event id.
            instance_id: The session whose events may be emitted.
            assistant_messages: Known assistant message ids for the session.
            text_parts: Known assistant text part ids for the session.

        Returns:
            A normalized event when the input is an emitting event; otherwise
            None. State-only events update the supplied id sets in place.

        Raises:
            RuntimeError: If terminal success cannot fetch the message list.
        """
        if event_type in {"session.next.step.started", "session.next.text.started"}:
            if data.get("sessionID") != instance_id:
                return None
            assistant_message_id = data.get("assistantMessageID")
            if assistant_message_id:
                assistant_messages.add(str(assistant_message_id))
            if event_type == "session.next.text.started":
                text_id = data.get("textID")
                if assistant_message_id and text_id:
                    text_parts.add(str(text_id))
            return None
        if data.get("sessionID") != instance_id:
            return None
        assistant_message_id = str(data.get("assistantMessageID") or "")
        if event_type == "session.next.text.delta":
            if (
                assistant_message_id not in assistant_messages
                or str(data.get("textID") or "") not in text_parts
            ):
                return None
            return StreamEvent(
                event_id=event_id,
                type="delta",
                message_id=assistant_message_id,
                delta=str(data.get("delta") or ""),
            )
        if event_type == "session.next.step.ended":
            if (
                data.get("finish") != "stop"
                or assistant_message_id not in assistant_messages
            ):
                return None
            assistant = self._find_assistant_message(instance_id, assistant_message_id)
            if assistant is None:
                return None
            return StreamEvent(
                event_id=event_id,
                type="completed",
                message_id=assistant.id,
                content=assistant.content,
            )
        if event_type == "session.next.step.failed":
            return StreamEvent(
                event_id=event_id,
                type="error",
                message_id=assistant_message_id,
                error=_format_opencode_error(data.get("error")),
            )
        return None

    def _find_assistant_message(
        self, instance_id: str, message_id: str
    ) -> Optional[Message]:
        """Fetch the authoritative assistant message for a terminal step.

        Args:
            instance_id: The target OpenCode session id.
            message_id: The assistant message id from the terminal event.

        Returns:
            The matching assistant message, or None when the server has not
            exposed one for the terminal step.

        Raises:
            RuntimeError: If the OpenCode message endpoint fails.
        """
        messages = self.list_messages(instance_id, after_message_id=None)
        return next(
            (
                message
                for message in messages
                if message.role == "assistant" and message.id == message_id
            ),
            None,
        )

    def reconcile_session(
        self, instance_id: str, *, after_result_id: Optional[str] = None
    ) -> SessionReconcile:
        """Query assistant messages and normalize a completed JSON result.

        Args:
            instance_id: OpenCode session identity bound to the task attempt.
            after_result_id: Optional result cursor retained by the caller.

        Returns:
            A running, completed, not-found, or ambiguous session outcome.
            Assistant JSON objects are returned as controlled provider results.

        Raises:
            No exception is raised for provider/session uncertainty; it is
            represented by ``status="ambiguous"`` for fail-closed recovery.
        """
        try:
            messages = self.list_messages(instance_id, after_message_id=None)
        except RuntimeError as exc:
            text = str(exc)
            if "HTTP 404" in text:
                return SessionReconcile(status="not_found", error=text)
            return SessionReconcile(status="ambiguous", error=text)
        assistant_messages = [
            message for message in messages if message.role == "assistant"
        ]
        if not assistant_messages:
            return SessionReconcile(status="running")
        results: list[ProviderResult] = []
        for message in assistant_messages:
            if after_result_id and message.id == after_result_id:
                continue
            payload: dict[str, object] | None
            try:
                decoded = json.loads(message.content)
            except (TypeError, json.JSONDecodeError):
                decoded = None
            payload = decoded if isinstance(decoded, dict) else None
            results.append(ProviderResult(result_id=message.id, payload=payload))
        return SessionReconcile(status="completed", results=results)

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
                method,
                url,
                json=json,
                headers=headers,
                timeout=self._timeout,
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


def _unwrap_data_envelope(payload: Any) -> list[dict[str, Any]]:
    """Return the ``data`` array from an opencode envelope, tolerant of shape.

    The real opencode 1.17.15 list/message endpoints wrap their payload in
    ``{"data": [...], "cursor": {...}}``. Older or partial responses may
    return a bare list. This helper accepts both and always returns a list,
    filtering out non-dict items so a malformed body cannot crash the caller.

    Args:
        payload: The decoded JSON body (dict with ``data`` or a bare list).

    Returns:
        A list of message/instance dicts (possibly empty).
    """
    if isinstance(payload, dict):
        items = payload.get("data", [])
    else:
        items = payload
    if not isinstance(items, list):
        return []
    return [it for it in items if isinstance(it, dict)]


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
    whose ``type == "text"`` (delegated to :func:`_concat_text_parts`).

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
    text = _concat_text_parts(parts)
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


def _concat_text_parts(parts: Any) -> str:
    """Concatenate all ``{"type": "text", "text": ...}`` entries in ``parts``.

    Defensive against non-list / non-dict entries so a malformed server body
    cannot raise during parsing (a single corrupt part should not discard
    the rest of the message).

    Args:
        parts: The ``content`` array of an opencode message item.

    Returns:
        The concatenated text of all text-type parts (``""`` when none).
    """
    if not isinstance(parts, list):
        return ""
    out: list[str] = []
    for p in parts:
        if isinstance(p, dict) and p.get("type") == "text":
            t = p.get("text")
            if isinstance(t, str):
                out.append(t)
    return "".join(out)


def _format_opencode_error(error: Any) -> str:
    """Format an OpenCode provider error into a useful stable message.

    Args:
        error: The error value from an OpenCode SSE event.

    Returns:
        A human-readable error string, including the provider error type when
        the server supplies one.
    """
    if isinstance(error, dict):
        error_type = error.get("type")
        message = error.get("message")
        if error_type and message:
            return f"{error_type}: {message}"
        if message:
            return str(message)
        if error_type:
            return str(error_type)
    if error:
        return str(error)
    return "OpenCode step failed"


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
