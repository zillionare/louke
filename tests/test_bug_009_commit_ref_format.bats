#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "BUG-009-RED: Devon should specify commit reference format (owner/repo@sha)" {
    run grep -qF "owner/repo@sha" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Devon.md does not mention owner/repo@sha format for referencing commits"
        false
    }
}

@test "BUG-009-RED: Devon should forbid bare short SHA in comments" {
    run grep -qE "(禁止|avoid|do not|should not|always use).*(bare|short|裸).*sha" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Devon.md does not forbid bare short SHA references in GitHub comments"
        false
    }
}
