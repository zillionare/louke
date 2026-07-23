"""Unit contracts for Setup and Story interruption recovery."""

from louke.web.onboarding_recovery import DeliveryRecovery, recover_delivery


def test_recovery_reuses_same_delivery_request() -> None:
    """AC-FR0801-02: interrupted Story start does not create a second request."""
    recovery = recover_delivery(
        DeliveryRecovery("delivery-1", "uncertain", "release-1", 1)
    )

    assert recovery.request_id == "delivery-1"
    assert recovery.release_id == "release-1"
    assert recovery.start_count == 1
    assert recovery.status == "attention"
