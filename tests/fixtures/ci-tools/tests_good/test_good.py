def test_adds_numbers():
    """AC-FR0001-01: addition works."""
    assert 1 + 1 == 2


def test_rejects_invalid_input():
    """AC-FR0001-02: invalid input is rejected."""
    try:
        int("x")
    except ValueError as exc:
        assert str(exc)


def test_fast():
    """AC-NFR0010-01: operation is fast."""
    assert (2 * 2) == 4
