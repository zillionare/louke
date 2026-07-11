from __future__ import annotations

import base64
import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any

from .store import ProjectStore, ValidationError


SESSION_COOKIE = "louke_session"


@dataclass
class AuthenticatedUser:
    username: str


def current_user(
    store: ProjectStore, cookie_value: str | None
) -> AuthenticatedUser | None:
    if not cookie_value:
        return None
    payload = _decode_session(store, cookie_value)
    if not payload:
        return None
    username = str(payload.get("username") or "").strip()
    if not username or not store.user_exists(username):
        return None
    return AuthenticatedUser(username=username)


def issue_session_cookie(store: ProjectStore, username: str) -> str:
    payload = {"username": username}
    serialized = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(serialized).decode("ascii")
    signature = hmac.new(
        _session_secret(store), encoded.encode("ascii"), hashlib.sha256
    ).hexdigest()
    return f"{encoded}.{signature}"


def register_user(
    store: ProjectStore, username: str, password: str
) -> AuthenticatedUser:
    clean_username = _normalize_username(username)
    clean_password = _normalize_password(password)
    store.create_user(clean_username, clean_password)
    return AuthenticatedUser(username=clean_username)


def authenticate_user(
    store: ProjectStore, username: str, password: str
) -> AuthenticatedUser:
    clean_username = _normalize_username(username)
    clean_password = _normalize_password(password)
    if not store.verify_user(clean_username, clean_password):
        raise ValidationError("invalid username or password")
    return AuthenticatedUser(username=clean_username)


def _decode_session(store: ProjectStore, cookie_value: str) -> dict[str, Any] | None:
    encoded, dot, signature = cookie_value.partition(".")
    if not encoded or not dot or not signature:
        return None
    expected = hmac.new(
        _session_secret(store), encoded.encode("ascii"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return None
    try:
        payload = base64.urlsafe_b64decode(encoded.encode("ascii"))
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None


def _session_secret(store: ProjectStore) -> bytes:
    digest = hashlib.sha256()
    digest.update(str(store.root).encode("utf-8"))
    digest.update(b"\n")
    digest.update(store.project_info_path.read_bytes())
    return digest.digest()


def _normalize_username(username: str) -> str:
    value = str(username or "").strip()
    if len(value) < 2:
        raise ValidationError("username must be at least 2 characters")
    if len(value) > 64:
        raise ValidationError("username must be at most 64 characters")
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.@")
    if any(char not in allowed for char in value):
        raise ValidationError("username contains unsupported characters")
    return value


def _normalize_password(password: str) -> str:
    value = str(password or "")
    if len(value) < 4:
        raise ValidationError("password must be at least 4 characters")
    if len(value) > 256:
        raise ValidationError("password is too long")
    return value
