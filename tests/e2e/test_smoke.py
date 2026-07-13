import pytest


@pytest.mark.e2e
def test_e2e_marker_works():
    """AC-NFR0001-01: e2e marker 已在 pytest 配置 + lk e2e CLI 模块可调用."""
    from louke.e2e import register_subcommand

    assert callable(register_subcommand)
