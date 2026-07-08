#!/usr/bin/env bats
# Test Archer: test-plan.md must (1) reference verify_issue_schema.py,
# (2) define AC-FRXXX-YY traceability convention, (3) define lk agent archer ci-scan CI gate.
# v0.5-008+: original Probe role merged into Archer.
# v0.5-011 revision: removed FORM-005/006/007 (old "spec is reference / each AC needs UT / no longer parse spec" wording),
# changed to FORM-001 (merged into issue schema reference) / FORM-002 (keep issue form fields) / FORM-004 (change AC-FRXXX-YY naming convention)
# v0.6+ revision: removed FORM-001 / FORM-003 — Lex phase 2 already validates issue schema via verify_issue_schema,
# Archer only reads issue list and closes the loop via `lk agent archer ci-scan` schema reverse lookup; explicit reference to verify_issue_schema
# responsibility has been pushed down to ci-scan, FORM-004 already covers it.

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/agents"
ARCHER="$AGENTS_DIR/Archer.md"

@test "ARCHER-FORM-002: archer_documents_AC_traceability" {
    # AC traceability convention is AC-FRXXX-YY (replaces old "fr_id" field)
    run grep -qE "AC-(FR|NFR|FRXXX)" "$ARCHER"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Archer.md does not define AC-FRXXX-YY traceability convention"
        false
    }
}

@test "ARCHER-FORM-004: archer_documents_CI_gate_command" {
    # CI gate uses lk agent archer ci-scan (replaces old specforge ci-scan)
    run grep -qE "(lk agent archer ci-scan|ci-scan)" "$ARCHER"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Archer.md does not define lk agent archer ci-scan CI gate"
        false
    }
}
