#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
DEVON_MD="$REPO_ROOT/louke/agents/Devon.md"

@test "FR-0500 AC-1: Devon.md §8 anti-patterns list contains --no-verify" {
    [ -f "$DEVON_MD" ]
    run grep -qE "(--no-verify|no-verify)" "$DEVON_MD"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Devon.md §8 does not mention --no-verify" >&2
        false
    }
}

@test "FR-0500 AC-2: Devon.md §6.2 push rules ban --no-verify" {
    [ -f "$DEVON_MD" ]
    run grep -qE "(--no-verify|no-verify)" "$DEVON_MD"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Devon.md §6.2 does not ban --no-verify" >&2
        false
    }
    # Ensure the mention appears in or after the push rules section
    run awk '/^## 6\. /{found=1} found && /(--no-verify|no-verify)/{print; exit}' "$DEVON_MD"
    [ -n "$output" ] || {
        echo "FAIL: --no-verify ban not in §6 push rules" >&2
        false
    }
}
