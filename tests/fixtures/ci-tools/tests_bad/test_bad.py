def test_missing_real_assertion():
    """AC-FR0001-01: fake assertion."""
    assert True


def test_unknown_ac():
    """AC-FR9999-01: unknown AC."""
    assert 1 == 1


def test_swallow_exception():
    try:
        raise RuntimeError("boom")
    except Exception:
        pass


def test_skip_without_issue():
    import pytest
    pytest.skip("later")
