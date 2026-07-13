"""Shared pytest configuration for louke tests.

Registers project-level markers (e.g. ``e2e``) so that ``-m e2e`` selection
and ``--markers`` listing work without an explicit pytest.ini.
"""


def pytest_configure(config):
    """Register the ``e2e`` marker for end-to-end browser tests (Playwright).

    Args:
        config: the pytest Config object.
    """
    config.addinivalue_line("markers", "e2e: end-to-end browser test (Playwright)")
