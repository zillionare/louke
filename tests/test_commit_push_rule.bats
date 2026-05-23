#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "PUSH-001: Forge mentions git push after each commit" {
    run grep -qE "(git push|立即推送|push.*after.*commit|commit.*之后.*push)" "$AGENTS_DIR/Forge.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Forge.md does not mention pushing after commit"
        false
    }
}

@test "PUSH-002: Forge mentions push triggers CI and status updates" {
    run grep -qE "(push.*CI|push.*trigger|push.*status|推送.*CI|推送.*状态)" "$AGENTS_DIR/Forge.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Forge.md does not mention that push triggers CI/status"
        false
    }
}

@test "PUSH-003: Hunter mentions git push after each commit" {
    run grep -qE "(git push|立即推送|push.*after.*commit|commit.*之后.*push)" "$AGENTS_DIR/Hunter.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Hunter.md does not mention pushing after commit"
        false
    }
}
