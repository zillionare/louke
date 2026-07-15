"""NFR-0401: loopback identity and secret security e2e.

Covers AC-NFR0401-01..04. Per test-plan §1.1 (black-box declaration) and §6.9
(non-functional specialty) these tests observe the security primitives through
their public ``LoopbackGuard`` / ``CredentialStore`` / ``SecretRedactor`` /
``RequestValidator`` surface - the observable exits described in
interfaces.md §1 (contract: loopback-only listener, no plaintext credentials,
secrets redacted from artifacts/manifests/events/logs/errors, wrong
identity/run/revision/replay rejected). The v0.12 M-DEV HTTP project API is
not yet implemented; these public outputs are the contract surface, mirroring
the established pattern in ``test_fr2301_legacy_adoption__e2e.py``.

Expected loopback hosts, redaction markers and idempotency contract come from
acceptance.md AC-NFR0401-01..04 (the spec), not from implementation output.

AC references:
- AC-NFR0401-01: Web defaults to loopback; non-loopback hosts are rejected
  with a message explaining the unsupported security premise.
- AC-NFR0401-02: credentials are not stored as plaintext; an
  exited/invalidated session cannot forge identity or continue approving.
- AC-NFR0401-03: secrets are redacted from Project artifacts, context
  manifest, events, logs, error responses and E2E artifacts; the Agent only
  observes the restricted non-secret capability identity.
- AC-NFR0401-04: wrong identity/run/revision/replay requests are rejected
  with no partial success; a matching request executes exactly once.
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

# Fixed secret and identity values - driven by the test fixtures, not derived
# from implementation output. High-entropy-looking tokens stand in for real
# provider/GitHub/session secrets.
_PROVIDER_SECRET = "sk-proj-1234567890abcdefABCDEF"
_GITHUB_TOKEN = "ghp_abcdef0123456789abcdef0123456789"
_PRINCIPAL = "alice"
_RUN = "run_001"
_REVISION = "rev_001"
_NONCE = "nonce-abc-001"


# ---------------------------------------------------------------------------
# AC-NFR0401-01: Web defaults to loopback, non-loopback rejected
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_nfr0401_01_default_host_is_loopback():
    """AC-NFR0401-01: the default Web host is a loopback address.

    When the user has not configured external authentication or transport
    protection, the Web server must default to loopback only.
    """
    guard = LoopbackGuard()

    default = guard.default_host()

    assert default in {"127.0.0.1", "::1", "localhost"}
    # The loopback guard must accept its own default without raising.
    guard.assert_loopback(default)


@pytest.mark.e2e
def test_ac_nfr0401_01_non_loopback_host_rejected():
    """AC-NFR0401-01: a non-loopback host is rejected with a security-premise message.

    Binding to a non-loopback host without external transport protection must
    be rejected; the message must explain that the premise is unsupported in
    this release.
    """
    guard = LoopbackGuard()

    with pytest.raises(PermissionError) as exc:
        guard.assert_loopback("0.0.0.0")

    msg = str(exc.value).lower()
    assert "loopback" in msg or "non-loopback" in msg
    assert "not supported" in msg or "unsupported" in msg


@pytest.mark.e2e
def test_ac_nfr0401_01_loopback_variants_accepted():
    """AC-NFR0401-01: IPv4, IPv6 and hostname loopback variants are accepted.

    The loopback guard must accept 127.0.0.1, ::1 and localhost so the user is
    not forced to a single loopback notation.
    """
    guard = LoopbackGuard()

    for host in ("127.0.0.1", "::1", "localhost"):
        # Must not raise.
        guard.assert_loopback(host)


# ---------------------------------------------------------------------------
# AC-NFR0401-02: credentials not plaintext; invalidated session cannot approve
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_nfr0401_02_credentials_not_stored_as_plaintext():
    """AC-NFR0401-02: stored credentials do not appear in the persisted dump.

    The credential store must hash credentials before storage; the audit dump
    must not contain the plaintext credential.
    """
    store = CredentialStore()
    store.set_principal_credential(_PRINCIPAL, _PROVIDER_SECRET)

    dumped = store.dump()

    # The plaintext secret must never appear in the persisted representation.
    assert _PROVIDER_SECRET not in dumped
    # The dump must mask the credential value explicitly.
    assert "***" in dumped


@pytest.mark.e2e
def test_ac_nfr0401_02_valid_credential_verifies_and_can_approve():
    """AC-NFR0401-02: a valid credential verifies and the session may approve.

    After establishing a principal credential, ``verify`` must accept the
    correct credential and ``can_approve`` must return True.
    """
    store = CredentialStore()
    store.set_principal_credential(_PRINCIPAL, _PROVIDER_SECRET)

    assert store.verify(_PRINCIPAL, _PROVIDER_SECRET) is True
    assert store.can_approve(_PRINCIPAL) is True


@pytest.mark.e2e
def test_ac_nfr0401_02_wrong_credential_rejected():
    """AC-NFR0401-02: an incorrect credential does not verify.

    A wrong credential must not pass verification even when a principal exists.
    """
    store = CredentialStore()
    store.set_principal_credential(_PRINCIPAL, _PROVIDER_SECRET)

    assert store.verify(_PRINCIPAL, "wrong-secret") is False


@pytest.mark.e2e
def test_ac_nfr0401_02_invalidated_session_cannot_approve():
    """AC-NFR0401-02: an exited/invalidated session cannot approve gates.

    After ``invalidate_session``, the principal must no longer be able to
    approve; the credential may still verify but approval is blocked, so an
    exited session cannot forge identity or continue approving.
    """
    store = CredentialStore()
    store.set_principal_credential(_PRINCIPAL, _PROVIDER_SECRET)
    assert store.can_approve(_PRINCIPAL) is True

    store.invalidate_session(_PRINCIPAL)

    assert store.can_approve(_PRINCIPAL) is False


@pytest.mark.e2e
def test_ac_nfr0401_02_unknown_principal_cannot_approve():
    """AC-NFR0401-02: a principal with no established credential cannot approve.

    An unknown principal must neither verify nor be able to approve, so a
    session cannot be forged from nothing.
    """
    store = CredentialStore()

    assert store.verify("mallory", _PROVIDER_SECRET) is False
    assert store.can_approve("mallory") is False


# ---------------------------------------------------------------------------
# AC-NFR0401-03: secrets redacted from artifacts/manifests/events/logs/errors
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_nfr0401_03_secret_redacted_from_string_payload():
    """AC-NFR0401-03: a registered secret is redacted from a string payload.

    When external adapters use provider/GitHub/session secrets, those secrets
    must not appear in any user-facing string output (artifacts, manifests,
    events, logs, error responses).
    """
    redactor = SecretRedactor()
    redactor.register_secret(_PROVIDER_SECRET)
    redactor.register_secret(_GITHUB_TOKEN)

    log_line = (
        f"calling provider with token={_PROVIDER_SECRET} and github={_GITHUB_TOKEN}"
    )

    redacted = redactor.redact(log_line)

    assert _PROVIDER_SECRET not in redacted
    assert _GITHUB_TOKEN not in redacted
    assert "***" in redacted


@pytest.mark.e2e
def test_ac_nfr0401_03_secret_redacted_from_nested_manifest():
    """AC-NFR0401-03: secrets are redacted from nested dict/list context manifests.

    The context manifest (interfaces.md §5 task/context manifest) must not
    expose raw secrets in any nested field; the Agent must only observe the
    restricted non-secret capability identity.
    """
    redactor = SecretRedactor()
    redactor.register_secret(_PROVIDER_SECRET)

    manifest = {
        "task_id": "task_001",
        "capability": "semantic-result/v1",
        "env": {"PROVIDER_KEY": _PROVIDER_SECRET},
        "instructions": [f"use key {_PROVIDER_SECRET} to call the model"],
        "nested": {"deep": [_PROVIDER_SECRET]},
    }

    redacted = redactor.redact(manifest)

    # The non-secret fields must survive.
    assert redacted["task_id"] == "task_001"
    assert redacted["capability"] == "semantic-result/v1"
    # The secret must be gone from every nesting level.
    assert _PROVIDER_SECRET not in redacted["env"]["PROVIDER_KEY"]
    assert _PROVIDER_SECRET not in redacted["instructions"][0]
    assert _PROVIDER_SECRET not in redacted["nested"]["deep"][0]
    assert "***" in redacted["env"]["PROVIDER_KEY"]


@pytest.mark.e2e
def test_ac_nfr0401_03_unregistered_secret_not_redacted():
    """AC-NFR0401-03: only registered secrets are redacted.

    The redactor must not blanket-replace arbitrary values; only secrets
    explicitly registered are masked, so the manifest retains honest
    non-secret content.
    """
    redactor = SecretRedactor()
    redactor.register_secret(_PROVIDER_SECRET)

    payload = f"public={_GITHUB_TOKEN} private={_PROVIDER_SECRET}"

    redacted = redactor.redact(payload)

    # The registered secret is redacted.
    assert _PROVIDER_SECRET not in redacted
    # The unregistered token is left intact (it is not a registered secret).
    assert _GITHUB_TOKEN in redacted


@pytest.mark.e2e
def test_ac_nfr0401_03_error_response_redacts_secret():
    """AC-NFR0401-03: an error response does not leak the secret.

    When an error message includes the secret (e.g. an adapter failure), the
    redactor must scrub it before the response reaches the user.
    """
    redactor = SecretRedactor()
    redactor.register_secret(_PROVIDER_SECRET)

    error_response = f"provider call failed: auth rejected for {_PROVIDER_SECRET}"

    redacted = redactor.redact(error_response)

    assert _PROVIDER_SECRET not in redacted
    assert "***" in redacted


# ---------------------------------------------------------------------------
# AC-NFR0401-04: wrong identity/run/revision/replay rejected, no partial success
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_nfr0401_04_wrong_principal_rejected():
    """AC-NFR0401-04: a request with the wrong principal is rejected.

    Approve/cancel/model-rebind/resource-terminate requests must carry the
    correct principal; a mismatch must be rejected.
    """
    validator = RequestValidator(
        expected_principal=_PRINCIPAL,
        expected_run=_RUN,
        expected_revision=_REVISION,
    )

    with pytest.raises(PermissionError) as exc:
        validator.validate(principal="mallory", run=_RUN, revision=_REVISION)

    assert "principal" in str(exc.value).lower()
    # No execution occurred.
    assert validator.execution_count == 0


@pytest.mark.e2e
def test_ac_nfr0401_04_wrong_run_rejected():
    """AC-NFR0401-04: a request targeting the wrong run is rejected.

    A run mismatch must be rejected with no partial success.
    """
    validator = RequestValidator(
        expected_principal=_PRINCIPAL,
        expected_run=_RUN,
        expected_revision=_REVISION,
    )

    with pytest.raises(PermissionError) as exc:
        validator.validate(principal=_PRINCIPAL, run="run_other", revision=_REVISION)

    assert "run" in str(exc.value).lower()
    assert validator.execution_count == 0


@pytest.mark.e2e
def test_ac_nfr0401_04_wrong_revision_rejected():
    """AC-NFR0401-04: a request bound to the wrong revision is rejected.

    A revision mismatch must be rejected so a stale request cannot mutate
    state at an unexpected revision.
    """
    validator = RequestValidator(
        expected_principal=_PRINCIPAL,
        expected_run=_RUN,
        expected_revision=_REVISION,
    )

    with pytest.raises(PermissionError) as exc:
        validator.validate(principal=_PRINCIPAL, run=_RUN, revision="rev_stale")

    assert "revision" in str(exc.value).lower()
    assert validator.execution_count == 0


@pytest.mark.e2e
def test_ac_nfr0401_04_replay_detected_rejected():
    """AC-NFR0401-04: a replayed request (same nonce) is rejected.

    A request nonce may only be used once; the second use of the same nonce
    must raise ReplayDetectedError and not execute again.
    """
    validator = RequestValidator(
        expected_principal=_PRINCIPAL,
        expected_run=_RUN,
        expected_revision=_REVISION,
    )

    # First use of the nonce executes.
    validator.validate(principal=_PRINCIPAL, run=_RUN, revision=_REVISION, nonce=_NONCE)
    assert validator.execution_count == 1

    # Replay: same nonce must be rejected.
    with pytest.raises(ReplayDetectedError):
        validator.validate(
            principal=_PRINCIPAL, run=_RUN, revision=_REVISION, nonce=_NONCE
        )

    # Execution count must not have advanced - no partial success.
    assert validator.execution_count == 1


@pytest.mark.e2e
def test_ac_nfr0401_04_matching_request_executes_exactly_once():
    """AC-NFR0401-04: a matching request with a fresh nonce executes exactly once.

    Two distinct nonces for the same valid request each execute exactly once,
    proving that the validator is not rejecting all requests, only replays.
    """
    validator = RequestValidator(
        expected_principal=_PRINCIPAL,
        expected_run=_RUN,
        expected_revision=_REVISION,
    )

    validator.validate(
        principal=_PRINCIPAL, run=_RUN, revision=_REVISION, nonce="nonce-1"
    )
    validator.validate(
        principal=_PRINCIPAL, run=_RUN, revision=_REVISION, nonce="nonce-2"
    )

    assert validator.execution_count == 2


@pytest.mark.e2e
def test_ac_nfr0401_04_validation_without_nonce_does_not_execute():
    """AC-NFR0401-04: validating without a nonce checks identity but does not execute.

    A request validated without a nonce (e.g. a read-only check) must still
    verify principal/run/revision but must not count as an execution.
    """
    validator = RequestValidator(
        expected_principal=_PRINCIPAL,
        expected_run=_RUN,
        expected_revision=_REVISION,
    )

    validator.validate(principal=_PRINCIPAL, run=_RUN, revision=_REVISION)

    assert validator.execution_count == 0
