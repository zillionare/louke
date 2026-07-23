"""Unit contracts for non-secret Setup and evidence projections."""

from louke.web.secret_redaction import redact_text


def test_redaction_removes_credentials_and_url_userinfo() -> None:
    """AC-NFR0101-01: user-visible evidence never contains raw secrets."""
    text = "password=credential-canary remote=https://user:token@example/repo"

    redacted = redact_text(text)

    assert "credential-canary" not in redacted
    assert "user:token" not in redacted
    assert "[REDACTED]" in redacted
