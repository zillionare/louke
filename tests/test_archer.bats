#!/usr/bin/env bats
# 测试 Archer:test-plan.md 必须 (1) 引用 verify_issue_schema.py,
# (2) 定义 AC-FRXXX-YY 追溯约定, (3) 定义 lk archer ci-scan CI 门禁。
# v0.5-008 起: 原 Probe 角色由 Archer 合并。
# v0.5-011 修订: 删 FORM-005/006/007 (旧 "spec 是参考 / 每条 AC 都要 UT / 不再解析 spec" 表述),
# 改 FORM-001 (合并到 issue schema 引用) / FORM-002 (保留 issue form 字段) / FORM-004 (改 AC-FRXXX-YY 命名约定)

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"
ARCHER="$AGENTS_DIR/Archer.md"

@test "ARCHER-FORM-001: archer_references_issue_schema_via_verify_issue_schema" {
    # Archer 通过 verify_issue_schema.py 拿 issue 列表 + 校验 schema
    # (Lex 阶段二负责创建 issue, Archer 只读)
    run grep -q "verify_issue_schema" "$ARCHER"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Archer.md 应引用 verify_issue_schema.py 拿 issue 数据"
        false
    }
}

@test "ARCHER-FORM-002: archer_documents_AC_traceability" {
    # AC 追溯约定是 AC-FRXXX-YY (取代旧的"fr_id"字段)
    run grep -qE "AC-(FR|NFR|FRXXX)" "$ARCHER"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Archer.md 未定义 AC-FRXXX-YY 追溯约定"
        false
    }
}

@test "ARCHER-FORM-003: archer_reuses_verify_issue_schema_logic" {
    run grep -q "verify_issue_schema" "$ARCHER"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Archer.md 应复用 verify_issue_schema.py 的解析函数"
        false
    }
}

@test "ARCHER-FORM-004: archer_documents_CI_gate_command" {
    # CI 门禁用 lk archer ci-scan (取代旧的 specforge ci-scan)
    run grep -qE "(lk archer ci-scan|ci-scan)" "$ARCHER"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Archer.md 未定义 lk archer ci-scan CI 门禁"
        false
    }
}
