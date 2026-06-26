#!/usr/bin/env bats
#
# v0.5-011: 部分 BRANCH-* 测试因 spec/{spec-id} 约定退役而删除.
# 当前 specforge 的分支约定见 ADR 005 (releases/{version} / feat/{spec-id}/{task-id} / fix/{issue-number}).
# 保留的 BRANCH-002/003/004/005 仍覆盖当前活跃的分支约定.

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

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
