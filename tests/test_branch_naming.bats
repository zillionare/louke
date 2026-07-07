#!/usr/bin/env bats
#
# v0.5-011: some BRANCH-* tests removed because spec/{spec-id} convention was retired.
# Current louke branch conventions (see Maestro.md branch convention section):
#   - Single active branch: releases/{version} (Devon does not create task-level branches)
#   - Historical releases can exist; humans decide when to delete
#   - Bug fixes: fix/{issue-number} → merge to main + merge to current release
# BRANCH-002/003/004 still cover the currently active branch conventions.

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/agents"

@test "BRANCH-002: Scout does NOT use a dedicated branch" {
    run grep -qE "scout/\{version\}" "$AGENTS_DIR/Scout.md"
    [ "$status" -ne 0 ] || {
        echo "FAIL: Scout.md should not mention scout/{version} branch — Scout works on default branch"
        false
    }
}

@test "BRANCH-003: Devon does NOT create per-task branches (works on releases/{version})" {
    # v0.5+ Devon works directly on the single active branch releases/{version}, does not create feat/{spec-id}/...
    run grep -qE "feat/\{spec-id\}" "$AGENTS_DIR/Devon.md"
    [ "$status" -ne 0 ] || {
        echo "FAIL: Devon.md should not create feat/{spec-id}/{task-id} task-level branches — commit on releases/{version} instead"
        false
    }
    # Must explicitly state "work on releases/{version}"
    run grep -qE "releases/\{version\}" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Devon.md does not declare working on releases/{version}"
        false
    }
}

@test "BRANCH-004: Maestro documents fix/{issue-number} for bugfix branch" {
    # Bug fixes still use fix/{issue-number} branch (created by Maestro during M-BUGFIX phase)
    run grep -qE "fix/\{issue-number\}" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Maestro.md does not declare fix/{issue-number} branch convention"
        false
    }
}
