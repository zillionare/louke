#!/usr/bin/env bats
# 测试 Maestro:会话启动身份一致性检查

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "MAESTRO-ID-001: Maestro 工作流第 1 步后必跑身份检查" {
    run grep -qE "会话启动冒烟|check_identity" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Maestro.md 工作流未含会话启动冒烟"
        false
    }
}

@test "MAESTRO-ID-002: Maestro 明确 [拒绝] 状态拒绝启动" {
    run grep -qF "[拒绝]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || { echo "FAIL: 缺 [拒绝]" >&2; false; }
    run grep -qF "拒绝启动" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ] || { echo "FAIL: 缺 '拒绝启动'" >&2; false; }
}

@test "MAESTRO-ID-003a: Maestro 含 [通过] 标记" {
    run grep -qF "[通过]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}

@test "MAESTRO-ID-003b: Maestro 含 [通过+警告] 标记" {
    run grep -qF "[通过+警告]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}

@test "MAESTRO-ID-003c: Maestro 含 [拒绝] 标记" {
    run grep -qF "[拒绝]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}
