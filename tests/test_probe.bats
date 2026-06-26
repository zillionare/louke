#!/usr/bin/env bats
# 测试 Probe:从 spec 需求生成 test-plan.md (策略文档,不是测试用例清单)
# v0.5-008 重写后: Probe 引用 verify_issue_schema.py + AC-FRXXX-YY 追溯约定 + ci-scan
# v0.5-011 修订: 删 FORM-005/006/007 (旧 "spec 是参考 / 每条 AC 都要 UT / 不再解析 spec" 表述),
# 改 FORM-001 (合并到 issue schema 引用) / FORM-002 (保留 issue form 字段) / FORM-004 (改 AC-FRXXX-YY 命名约定)

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"
PROBE="$AGENTS_DIR/Probe.md"

@test "PROBE-FORM-001: probe_references_issue_schema_via_verify_issue_schema" {
    # v0.5-008 起, Probe 通过 verify_issue_schema.py 拿 issue 列表 + 校验 schema
    # (代替旧的 gh issue list 拉数据 — 那是 Lex 阶段二的事, Probe 只读)
    run grep -q "verify_issue_schema" "$PROBE"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Probe.md 应引用 verify_issue_schema.py 拿 issue 数据"
        false
    }
}

@test "PROBE-FORM-002: probe_documents_AC_traceability" {
    # v0.5-008 起, AC 追溯约定是 AC-FRXXX-YY (取代旧的"fr_id"字段)
    run grep -qE "AC-(FR|NFR|FRXXX)" "$PROBE"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Probe.md 未定义 AC-FRXXX-YY 追溯约定"
        false
    }
}

@test "PROBE-FORM-003: probe_reuses_verify_issue_schema_logic" {
    run grep -q "verify_issue_schema" "$PROBE"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Probe.md 应复用 verify_issue_schema.py 的解析函数"
        false
    }
}

@test "PROBE-FORM-004: probe_documents_CI_gate_command" {
    # v0.5-008 起, CI 门禁用 specforge ci-scan (取代旧的 UT-XXX 命名)
    run grep -qE "(specforge ci-scan|ci-scan)" "$PROBE"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Probe.md 未定义 specforge ci-scan CI 门禁"
        false
    }
}
