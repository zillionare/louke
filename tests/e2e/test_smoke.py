import pytest


@pytest.mark.e2e
def test_e2e_marker_works():
    """AC-NFR0001-01: e2e smoke - verify the e2e marker is wired and a trivial assertion holds."""
    assert True
