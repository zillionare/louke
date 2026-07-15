"""Shared pytest configuration for the integration test layer.

Mirrors the path-based auto-marking used by ``tests/e2e/conftest.py``: every
test collected under ``tests/integration/`` is marked ``integration`` so
``pytest -m integration`` selects it without requiring each test function to
add ``@pytest.mark.integration`` explicitly.

See gap-analysis §3 P1-1 / issue #177 (S4: test layering reflow).
"""

from __future__ import annotations

import pytest


def pytest_collection_modifyitems(config, items):
    """Auto-mark every test under ``tests/integration/`` as ``integration``.

    Args:
        config: the pytest Config object.
        items: the collected test items; modified in place.
    """
    for item in items:
        if "tests/integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
