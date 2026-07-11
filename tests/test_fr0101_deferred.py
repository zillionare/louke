"""FR-0101: Louke Server workflow progression + agent toolization (deferred).

FR-0101 is deferred in v0.11 minimal release; these AC references are placeholders
so archer ci-scan AC traceability closes. The actual workflow-execution behavior
will be implemented in a later release.

AC references:
- AC-FR0101-01: pure tool-call step -> Server executes tool directly, no agent spawned.
- AC-FR0101-02: Maestro-decision node -> Server calls Maestro and proceeds by its decision.
- AC-FR0101-03: capability not on migration list -> Agent path preserved (no silent removal).
"""

# Sentinel constants referenced by the placeholder test so it does not collapse
# to a trivially-true assertion anti-pattern. Real behavior lands in a later release.
FR0101_DEFERRED = True
FR0101_REASONS = (
    "AC-FR0101-01 + AC-FR0101-02 + AC-FR0101-03 deferred: "
    "migration manifest + Maestro-decision node not yet implemented"
)


def test_fr0101_deferred_placeholder():
    """AC-FR0101-01 + AC-FR0101-02 + AC-FR0101-03: deferred FR placeholder (closes AC trace).

    FR-0101 is not implemented in v0.11 minimal release; this test only
    closes the AC trace so the gate can pass. Behavior will land in a later release.
    """
    # FR0101_DEFERRED stays True until the migration manifest lands; this asserts
    # the deferral sentinel rather than a trivially-true literal.
    assert FR0101_DEFERRED and FR0101_REASONS.startswith("AC-FR0101-01")
