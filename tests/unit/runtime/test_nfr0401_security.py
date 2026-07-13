"""NFR-0401: loopback identity and secret security.

AC references:
- AC-NFR0401-01: Web server defaults to loopback; non-loopback requests are
  rejected with an explanation.
- AC-NFR0401-02: persisted credentials are not plaintext; invalidated sessions
  cannot approve gates.
- AC-NFR0401-03: secrets do not appear in artifacts, manifests, events, logs,
  errors or E2E artifacts; agents only see required non-secret capabilities.
- AC-NFR0401-04: requests with wrong identity/run/revision or replay are
  rejected with no partial success; matching requests execute once.
"""

from __future__ import annotations

import pytest

from louke.runtime.security import (
    CredentialStore,
    LoopbackGuard,
    ReplayDetectedError,
    RequestValidator,
    SecretRedactor,
)


# -- AC-NFR0401-01 ------------------------------------------------------------


def test_ac_nfr0401_01_default_loopback_binding():
    """AC-NFR0401-01: server binds to loopback by default."""
    guard = LoopbackGuard()
    assert guard.default_host() == "127.0.0.1"


def test_ac_nfr0401_01_non_loopback_request_rejected():
    """AC-NFR0401-01: non-loopback requests are rejected."""
    guard = LoopbackGuard()
    with pytest.raises(PermissionError):
        guard.assert_loopback("192.168.1.1")


# -- AC-NFR0401-02 ------------------------------------------------------------


def test_ac_nfr0401_02_credentials_not_plaintext():
    """AC-NFR0401-02: stored credentials are not plaintext."""
    store = CredentialStore()
    store.set_principal_credential(principal_id="alice", credential="secret-token")

    raw = store.dump()
    assert "secret-token" not in raw
    assert store.verify("alice", "secret-token") is True


def test_ac_nfr0401_02_invalidated_session_cannot_approve():
    """AC-NFR0401-02: invalidated session cannot approve gates."""
    store = CredentialStore()
    store.set_principal_credential(principal_id="alice", credential="token")
    store.invalidate_session("alice")

    assert store.can_approve("alice") is False


# -- AC-NFR0401-03 ------------------------------------------------------------


def test_ac_nfr0401_03_secrets_redacted_everywhere():
    """AC-NFR0401-03: secrets are redacted from artifacts, logs and errors."""
    redactor = SecretRedactor()
    redactor.register_secret("super-secret-token")

    payload = {
        "manifest": {"token": "super-secret-token"},
        "log": "used super-secret-token",
        "error": "auth failed with super-secret-token",
    }
    sanitized = redactor.redact(payload)
    assert "super-secret-token" not in str(sanitized)


def test_ac_nfr0401_03_agent_sees_only_capability_identity():
    """AC-NFR0401-03: agent manifest contains non-secret capability identity."""
    redactor = SecretRedactor()
    redactor.register_secret("api-key")

    manifest = {"agent": "devon", "tools": ["git.read"], "secret": "api-key"}
    safe = redactor.redact(manifest)

    assert safe["agent"] == "devon"
    assert safe["tools"] == ["git.read"]
    assert safe["secret"] == "***"


# -- AC-NFR0401-04 ------------------------------------------------------------


def test_ac_nfr0401_04_wrong_identity_rejected():
    """AC-NFR0401-04: wrong identity/run/revision is rejected."""
    validator = RequestValidator(expected_principal="alice", expected_run="run_001", expected_revision="rev_1")

    with pytest.raises(PermissionError):
        validator.validate(principal="bob", run="run_001", revision="rev_1")


def test_ac_nfr0401_04_replay_rejected():
    """AC-NFR0401-04: replayed request is rejected."""
    validator = RequestValidator(expected_principal="alice", expected_run="run_001", expected_revision="rev_1")

    validator.validate(principal="alice", run="run_001", revision="rev_1", nonce="n1")
    with pytest.raises(ReplayDetectedError):
        validator.validate(principal="alice", run="run_001", revision="rev_1", nonce="n1")


def test_ac_nfr0401_04_matching_request_executed_once():
    """AC-NFR0401-04: matching request executes once."""
    validator = RequestValidator(expected_principal="alice", expected_run="run_001", expected_revision="rev_1")

    validator.validate(principal="alice", run="run_001", revision="rev_1", nonce="n1")
    validator.validate(principal="alice", run="run_001", revision="rev_1", nonce="n2")
    assert validator.execution_count == 2
