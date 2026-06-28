#!/usr/bin/env bats
# 测试 Maestro:流程判定 marker ([通过] / [拒绝]) 在决策框架中存在。
# v0.6+ 修订: 删 ID-001 / ID-002 — 会话启动身份一致性检查已从 Maestro 流程下沉到
# 独立 orchestrator (check_identity.py) 在每次 Maestro 启动前显式调用, 不再是
# Maestro 工作流的 step 1; ID-003b 的 "[通过+警告]" marker 设计已弃用, 现行
# 设计用 pass-with-warning 状态而非 marker 字符串。

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "MAESTRO-ID-003a: maestro_has_pass_marker" {
    run grep -qF "[通过]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}

@test "MAESTRO-ID-003c: maestro_has_reject_marker" {
    run grep -qF "[拒绝]" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}
