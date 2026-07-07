#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/agents"

@test "PUSH-001: Devon mentions git push after each commit" {
    run grep -qE "(git push|push.*after.*commit|commit.*then.*push|immediately.*push)" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Devon.md does not mention pushing after commit"
        false
    }
}

@test "PUSH-002: Devon mentions push triggers CI and status updates" {
    run grep -qE "(push.*CI|push.*trigger|push.*status)" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Devon.md does not mention that push triggers CI/status"
        false
    }
}
