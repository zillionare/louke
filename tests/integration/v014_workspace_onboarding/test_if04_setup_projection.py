"""IF-04: SetupProjection — continuous Wizard and step visibility.

WITHDRAWN per Prism review F-001 (2026-07-24): this file drove
the deprecated ``SetupJourney``/``SetupStep`` six-step wizard which
has been retired in favor of the v0.14-004 two-context Setup
(``first_user`` + ``opencode_probe``).

The entire suite is marked ``pytest.skip`` so that running the
suite does not execute the retired behaviour. Real v0.14-004
coverage lives under:

* ``test_ac_fr0101_0301_0201__if_setup01_02_03.py`` — IF-SETUP-01/02
* ``test_ac_fr0001__if_web01_setup_gate.py`` — IF-WEB-01
* ``test_ac_fr1501_nfr01_04__if_compat_audit.py`` — IF-IDENTITY-01

Note: ``check_ac_traceability.py --tests tests`` still scans this
file for ``AC-FR*`` / ``AC-NFR*`` tokens. The legacy tokens in the
original suite (before it was shrunk to the placeholder) are not
present any more, so the 44/44 AC closure is sourced entirely
from the new ``test_ac_*.py`` files. When the legacy
``louke.web.setup_journey`` module is deleted, this file will be
deleted alongside it.
"""

from __future__ import annotations

import pytest

# AC-FR0101-01 withdrawn; tracked in #323
pytestmark = pytest.mark.skip(
    reason=(
        "spec: withdrawn continuous Setup Wizard (Prism review F-001); "
        "see test_ac_fr0101_0301_0201__if_setup01_02_03.py for the "
        "IF-SETUP-01 contract and test_ac_fr0001__if_web01_setup_gate.py "
        "for the IF-WEB-01 gate. "
        "AC-FR0101-01 withdrawn; tracked in #323."
    )
)


def test_withdrawn_setupprojection_placeholder():
    """Placeholder marking this file as withdrawn.

    The Prism review found the original six assertions drove the
    deprecated ``SetupJourney``/``SetupStep`` enumeration. The locked
    v0.14-004 baseline no longer has these steps; the new contract
    lives in ``test_ac_fr0101_0301_0201__if_setup01_02_03.py``.
    """
    assert "withdrawn" != "active"  # pragma: no cover - withdrawn suite placeholder
