#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "BRANCH-001: Sage uses spec/{spec-id} branch naming convention" {
    run grep -qE "spec/\{spec-id\}" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Sage.md does not mention spec/{spec-id} branch convention"
        false
    }
}

@test "BRANCH-002: Scout does NOT use a dedicated branch" {
    run grep -qE "scout/\{version\}" "$AGENTS_DIR/Scout.md"
    [ "$status" -ne 0 ] || {
        echo "FAIL: Scout.md should not mention scout/{version} branch — Scout works on default branch"
        false
    }
}

@test "BRANCH-003: Forge uses feat/{spec-id}/{task-id} branch naming convention" {
    run grep -qE "feat/\{spec-id\}/\{task-id\}" "$AGENTS_DIR/Forge.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Forge.md does not mention feat/{spec-id}/{task-id} branch convention"
        false
    }
}

@test "BRANCH-004: Hunter uses fix/{issue-number} branch naming convention" {
    run grep -qE "fix/\{issue-number\}" "$AGENTS_DIR/Hunter.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Hunter.md does not mention fix/{issue-number} branch convention"
        false
    }
}

@test "BRANCH-005: Archer references feat/{spec-id}/{task-id} branch convention" {
    run grep -qE "feat/\{spec-id\}/\{task-id\}" "$AGENTS_DIR/Archer.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Archer.md does not mention feat/{spec-id}/{task-id} branch convention"
        false
    }
}

@test "BRANCH-006: Maestro documents branch naming conventions (3 types, no scout)" {
    run grep -qE "spec/\{spec-id\}" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Maestro.md does not mention spec/{spec-id} branch convention"
        false
    }
    run grep -qE "feat/\{spec-id\}/\{task-id\}" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Maestro.md does not mention feat/{spec-id}/{task-id} branch convention"
        false
    }
    run grep -qE "fix/\{issue-number\}" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Maestro.md does not mention fix/{issue-number} branch convention"
        false
    }
    run grep -qE "scout/\{version\}" "$AGENTS_DIR/Maestro.md"
    [ "$status" -ne 0 ] || {
        echo "FAIL: Maestro.md should not mention scout/{version} branch — Scout works on default branch"
        false
    }
}

@test "BRANCH-007: Lex references spec/{spec-id} branch convention" {
    run grep -qE "spec/\{spec-id\}" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Lex.md does not mention spec/{spec-id} branch convention"
        false
    }
}

@test "BRANCH-008: Sage uses gh api for PR inline comments" {
    run grep -qE "gh api.*pulls.*comments" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Sage.md does not mention gh api for PR inline comments"
        false
    }
}

@test "BRANCH-009: Lex uses gh api for PR reviews" {
    run grep -qE "gh api.*pulls.*reviews" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Lex.md does not mention gh api for PR reviews"
        false
    }
}

@test "BRANCH-010: Lex uses gh api for PR inline comments" {
    run grep -qE "gh api.*pulls.*comments" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Lex.md does not mention gh api for PR inline comments"
        false
    }
}
