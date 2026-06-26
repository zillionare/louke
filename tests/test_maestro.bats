#!/usr/bin/env bats
# 测试 Maestro:会话启动身份一致性检查

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "MAESTRO-ID-001: maestro_step1_requires_identity_check" {
    run grep -qE "会话启动冒烟|check_identity" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Maestro.md 工作流未含会话启动冒烟"
        false
    }
}

@test "MAESTRO-ID-002: maestro_reject_status_blocks_startup" {
    run grep -qF "[拒绝]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || { echo "FAIL: 缺 [拒绝]" >&2; false; }
    run grep -qF "拒绝启动" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || { echo "FAIL: 缺 '拒绝启动'" >&2; false; }
}

@test "MAESTRO-ID-003a: maestro_has_pass_marker" {
    run grep -qF "[通过]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}

@test "MAESTRO-ID-003b: maestro_has_pass_with_warning_marker" {
    run grep -qF "[通过+警告]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}

@test "MAESTRO-ID-003c: maestro_has_reject_marker" {
    run grep -qF "[拒绝]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}
