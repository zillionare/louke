#!/usr/bin/env bats
#
# v0.5-011: 部分 BRANCH-* 测试因 spec/{spec-id} 约定退役而删除.
# 当前 holdpoint 分支约定 (见 Maestro.md 分支约定段):
#   - 活跃分支唯一: releases/{version} (Devon 不创建任务级分支)
#   - 历史 release 可存在, 人类决定何时删
#   - Bug 修复: fix/{issue-number} → 合 main + 合当前 release
# BRANCH-002/003/004 仍覆盖当前活跃的分支约定.

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "BRANCH-002: Scout does NOT use a dedicated branch" {
    run grep -qE "scout/\{version\}" "$AGENTS_DIR/Scout.md"
    [ "$status" -ne 0 ] || {
        echo "FAIL: Scout.md should not mention scout/{version} branch — Scout works on default branch"
        false
    }
}

@test "BRANCH-003: Devon does NOT create per-task branches (works on releases/{version})" {
    # v0.5+ Devon 直接在唯一活跃分支 releases/{version} 上工作, 不创建 feat/{spec-id}/...
    run grep -qE "feat/\{spec-id\}" "$AGENTS_DIR/Devon.md"
    [ "$status" -ne 0 ] || {
        echo "FAIL: Devon.md 不应再创建 feat/{spec-id}/{task-id} 任务级分支 — 改在 releases/{version} 上提交"
        false
    }
    # 必须明确写"在 releases/{version} 上工作"
    run grep -qE "releases/\{version\}" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Devon.md 未声明在 releases/{version} 上工作"
        false
    }
}

@test "BRANCH-004: Maestro documents fix/{issue-number} for bugfix branch" {
    # Bug 修复仍使用 fix/{issue-number} 分支 (由 Maestro 在 M-BUGFIX 阶段创建)
    run grep -qE "fix/\{issue-number\}" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Maestro.md 未声明 fix/{issue-number} 分支约定"
        false
    }
}
