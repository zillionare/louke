#!/usr/bin/env bats
# Test Maestro: process decision markers ([PASS] / [REJECT]) exist in the decision framework.
# v0.6+ revision: removed ID-001 / ID-002 — session startup identity consistency check
# has been moved from Maestro workflow to an independent orchestrator (check_identity.py)
# called explicitly before each Maestro startup, no longer a step in Maestro workflow;
# ID-003b's "[PASS+warning]" marker design has been deprecated, current design uses
# pass-with-warning status instead of a marker string.

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/agents"

@test "MAESTRO-ID-003a: maestro_has_pass_marker" {
    run grep -qF "[PASS]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}

@test "MAESTRO-ID-003c: maestro_has_reject_marker" {
    run grep -qF "[REJECT]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}
