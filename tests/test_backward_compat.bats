#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "NFR-0010 AC-6: task-log.md no longer references test: red" {
    run grep -q "test: red" "$REPO_ROOT/louke/templates/task-log.md"
    [ "$status" -ne 0 ]
}

@test "NFR-0010 AC-6: task-log.md references feat: green or refactor:" {
    run grep -qE "feat:\\s*green|refactor:" "$REPO_ROOT/louke/templates/task-log.md"
    [ "$status" -eq 0 ]
}

@test "NFR-0010 AC-7: bug-fix.md no longer references test: red" {
    run grep -q "test: red" "$REPO_ROOT/louke/templates/bug-fix.md"
    [ "$status" -ne 0 ]
}

@test "NFR-0010 AC-7: bug-fix.md references fix: green or refactor:" {
    run grep -qE "fix:\\s*green|refactor:" "$REPO_ROOT/louke/templates/bug-fix.md"
    [ "$status" -eq 0 ]
}
