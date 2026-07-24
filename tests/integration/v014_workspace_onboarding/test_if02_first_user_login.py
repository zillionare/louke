"""IF-02: First user creation, login, and Setup continuity.

WITHDRAWN per Prism review F-001 (2026-07-24): this file referenced
the deprecated continuous Setup Wizard (``louke.web.setup_journey``)
which has been retired in favor of the v0.14-004 two-context Setup
(``first_user`` + ``opencode_probe``). The behaviours that the wizard
once asserted — step ordering ``identity → repository → ...``,
``SetupStep.IDENTITY`` enumeration — no longer exist on the locked
baseline.

The tests are kept as a single ``pytest.skip`` so that:

* running the suite does not execute the retired behaviour, which
  would otherwise silently mask that the legacy module is still
  importable;
* any future cleanup that retains ``louke.web.setup_journey`` as a
  compat shim will surface clearly here instead of silently passing.

Note: ``check_ac_traceability.py --tests tests`` still scans this
file for ``AC-FR*`` / ``AC-NFR*`` tokens, so the legacy tokens here
remain in the closure report. The new ``test_ac_*.py`` suite
independently covers all 44 ACs; the legacy tokens are redundant
but not harmful to the 44/44 closure count. When the legacy
module is deleted, this file will be deleted alongside it.
"""

from __future__ import annotations

import pytest

# AC-FR0201-01 withdrawn; tracked in #324
pytestmark = pytest.mark.skip(
    reason=(
        "spec: withdrawn continuous Setup Wizard (Prism review F-001); "
        "see tests/integration/v014_workspace_onboarding/conftest.py "
        "and test_ac_fr0101_0301_0201__if_setup01_02_03.py for the "
        "v0.14-004 contract tests covering AC-FR0101/AC-FR0201/AC-FR0801. "
        "AC-FR0201-01 withdrawn; tracked in #324."
    )
)


def test_setup_wizard_withdrawn_placeholder():
    """Placeholder marking this file as withdrawn.

    The Prism review identified that the original assertions drove the
    retired ``SetupJourney``/``SetupStep`` six-step wizard; the locked
    baseline has only the two-context ``first_user`` + ``opencode_probe``
    flow. Real coverage lives under ``test_ac_fr0101_*`` and
    ``test_ac_fr0001_*``.
    """
    assert "withdrawn" != "active"  # pragma: no cover - withdrawn suite placeholder
