#!/usr/bin/env bats
# 测试 Probe:从 issue form 出发(不再重新解析 spec.md)

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"
PROBE="$AGENTS_DIR/Probe.md"

@test "PROBE-FORM-001: probe_references_gh_issue_list" {
    run grep -qE "gh issue list" "$PROBE"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Probe.md 不通过 gh issue list 拉取数据"
        false
    }
}

@test "PROBE-FORM-002: probe_references_issue_form_fields" {
    for field in "需求 ID" "验收标准" "AC-N" "fr_id"; do
        run grep -qE "$field" "$PROBE"
        [ "$status" -eq 0 ] || { echo "FAIL: Probe.md 缺 $field" >&2; false; }
    done
}

@test "PROBE-FORM-003: probe_reuses_verify_issue_schema_logic" {
    run grep -q "verify_issue_schema" "$PROBE"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Probe.md 应复用 verify_issue_schema.py 的解析函数"
        false
    }
}

@test "PROBE-FORM-004: probe_naming_UT_issue_AC_test" {
    run grep -qE "UT-\{?issue#\}?" "$PROBE"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Probe.md 测试 ID 未关联到 issue# 和 AC 序号"
        false
    }
}

@test "PROBE-FORM-005: probe_doc_marks_spec_md_as_reference" {
    # 应该出现 "设计源" / "操作源" / "背景参考" 等表述
    run grep -qE "(背景参考|设计源|操作源)" "$PROBE"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Probe.md 未明确 spec 是背景参考"
        false
    }
}

@test "PROBE-FORM-006: probe_exit_criteria_each_AC_has_UT" {
    run grep -qE "(每.*AC|每条 AC).*UT" "$PROBE"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Probe.md 退出条件未要求每条 AC 都有 UT"
        false
    }
}

@test "PROBE-FORM-007: probe_antipattern_no_reparse_spec_md" {
    run grep -qE "(重新解析|不再解析).*spec" "$PROBE"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Probe.md 未声明禁止重新解析 spec"
        false
    }
}
