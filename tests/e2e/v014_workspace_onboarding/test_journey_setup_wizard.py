"""E2E journey: continuous Setup Wizard (legacy six-step flow).

WITHDRAWN per Prism review F-001 (2026-07-24): this file drove
the retired continuous Setup Wizard
(``/setup/identity → /setup/repository → /setup/dependencies →
/setup/review → /setup/applying → /setup/complete``). The locked
v0.14-004 baseline replaces that with a two-context Setup:

  1. ``/setup`` shows the first-user form.
  2. Once the first user is persisted, the page switches to the
     ``opencode probe`` view.
  3. On ``ModelCheck.state == passed`` and manifest CAS success,
     the page redirects to ``/workbench?activity=projects``.

The entire suite is marked ``pytest.skip`` so the v0.14-004
``ac-trace`` gate does not count its AC tokens. Real E2E coverage
lives under:

* ``tests/e2e/v014_workspace_onboarding/test_journey_minimal_setup.py``
* ``tests/integration/v014_workspace_onboarding/test_ac_fr0101_0301_0201__if_setup01_02_03.py``
"""

from __future__ import annotations

import pytest

# AC-FR0101-01 withdrawn; tracked in #323
pytestmark = pytest.mark.skip(
    reason=(
        "spec: withdrawn continuous Setup Wizard (Prism review F-001); "
        "see test_journey_minimal_setup.py and "
        "test_ac_fr0101_0301_0201__if_setup01_02_03.py for the v0.14-004 "
        "two-context Setup contract. "
        "AC-FR0101-01 withdrawn; tracked in #323."
    )
)


def test_withdrawn_wizard_journey_placeholder():
    """Placeholder marking this file as withdrawn.

    The Prism review identified that the original eight assertions
    drove six-step wizard URLs (``/setup/identity``, ``/setup/repository``,
    ``/setup/dependencies``, ``/setup/review``, ``/setup/applying``,
    ``/setup/complete``) which are no longer reachable on the locked
    baseline. Furthermore, ``test_wizard_review_shows_apply_summary_*``
    used ``page.request.post(...)`` to skip the dependencies step in
    violation of the anti-cheat principle (Prism review E-003).
    """
    assert "withdrawn" != "active"  # pragma: no cover - withdrawn suite placeholder
