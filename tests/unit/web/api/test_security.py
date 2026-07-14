"""TestClient tests for the /api/security sub-app (NFR-0401).

AC references covered:
- AC-NFR0401-01: GET /loopback?host=X returns allowed bool; non-loopback hosts
  are rejected with an explanation, but the endpoint itself does not crash.
- AC-NFR0401-02: POST /credentials stores the credential hash (never plaintext);
  the plaintext credential MUST NOT appear in any response body.
- AC-NFR0401-03: GET /credentials/{principal_id}/verify?credential=... returns
  ``{"valid": bool}`` without echoing the stored credential.
- AC-NFR0401-04: POST /redact redacts registered secrets from a payload.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from louke.web.api.security import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient backed by a fresh in-memory security sub-app."""
    return TestClient(create_app())


def test_loopback_allowed_for_localhost(client: TestClient) -> None:
    """AC-NFR0401-01: GET /loopback returns allowed=True for 127.0.0.1."""
    resp = client.get("/loopback", params={"host": "127.0.0.1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["allowed"] is True
    assert body["host"] == "127.0.0.1"


def test_loopback_rejected_for_non_loopback(client: TestClient) -> None:
    """AC-NFR0401-01: GET /loopback returns allowed=False for non-loopback."""
    resp = client.get("/loopback", params={"host": "10.0.0.1"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["allowed"] is False
    assert body["host"] == "10.0.0.1"


def test_set_credential_never_echoes_plaintext(client: TestClient) -> None:
    """AC-NFR0401-02: POST /credentials stores hash, never echoes plaintext."""
    secret = "super-secret-token-12345"
    resp = client.post(
        "/credentials",
        json={"principal_id": "alice", "credential": secret},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["principal_id"] == "alice"
    assert body["credential_set"] is True
    # The plaintext credential MUST NOT appear anywhere in the response.
    assert secret not in resp.text


def test_verify_credential_returns_valid_without_echoing(client: TestClient) -> None:
    """AC-NFR0401-03: GET /credentials/{id}/verify returns valid bool safely."""
    secret = "super-secret-token-12345"
    client.post(
        "/credentials",
        json={"principal_id": "alice", "credential": secret},
    )
    resp = client.get(
        "/credentials/alice/verify",
        params={"credential": secret},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    # The stored credential plaintext MUST NOT appear in the response.
    assert secret not in resp.text


def test_verify_credential_wrong_returns_invalid(client: TestClient) -> None:
    """AC-NFR0401-03: GET /credentials/{id}/verify with wrong credential."""
    client.post(
        "/credentials",
        json={"principal_id": "alice", "credential": "correct-secret"},
    )
    resp = client.get(
        "/credentials/alice/verify",
        params={"credential": "wrong-secret"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is False


def test_redact_replaces_secrets_in_payload(client: TestClient) -> None:
    """AC-NFR0401-03: POST /redact redacts registered secrets from payload."""
    secret = "AKIA-SECRET-KEY-9999"
    payload = {"config": {"api_key": secret, "env": "prod"}, "note": f"see {secret}"}
    resp = client.post(
        "/redact",
        json={"payload": payload, "secrets": [secret]},
    )
    assert resp.status_code == 200
    body = resp.json()
    # The secret must be replaced with the redaction marker in all nested values.
    assert secret not in resp.text
    assert body["payload"]["config"]["api_key"] == "***"
    assert body["payload"]["note"] == "see ***"
