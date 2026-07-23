"""Unit contracts for context-aware, non-repeating Guide messages."""

from louke.web.guide_context import GuideMessageLedger


def test_guide_message_is_not_repeated_when_status_revision_is_unchanged() -> None:
    """AC-FR1401-02: repeated login does not append duplicate reminders."""
    ledger = GuideMessageLedger()

    assert ledger.should_announce("workspace-1", "status-1")
    ledger.mark_seen("workspace-1", "status-1")
    assert not ledger.should_announce("workspace-1", "status-1")
    assert ledger.should_announce("workspace-1", "status-2")


def test_context_change_marks_old_message_historical() -> None:
    """AC-FR1401-01: messages from another object are not current facts."""
    ledger = GuideMessageLedger()
    ledger.append("workspace-1", "status-1", "Review the Story")
    ledger.append("workspace-2", "status-2", "Review another Story")

    messages = ledger.messages("workspace-2")

    assert messages[0].historical
    assert not messages[1].historical
