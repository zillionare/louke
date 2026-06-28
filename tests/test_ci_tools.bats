#!/usr/bin/env bats

setup() {
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    FIX="$REPO_ROOT/tests/fixtures/ci-tools"
}

@test "CI_TOOLS_T01_check_acs_pass: all AC references found" {
    run python3 "$REPO_ROOT/tools/check_acs.py" --acceptance "$FIX/acceptance.md" --tests "$FIX/tests_good"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "3/3" ]]
}

@test "CI_TOOLS_T02_check_acs_missing_and_unknown_fail" {
    run python3 "$REPO_ROOT/tools/check_acs.py" --acceptance "$FIX/acceptance.md" --tests "$FIX/tests_bad"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "missing" ]]
    [[ "$output" =~ "unknown" ]]
}

@test "CI_TOOLS_T03_check_acs_json: emits valid JSON" {
    run python3 "$REPO_ROOT/tools/check_acs.py" --acceptance "$FIX/acceptance.md" --tests "$FIX/tests_good" --json
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['ok'] is True; assert d['total_ac'] == 3"
}

@test "CI_TOOLS_T04_check_acs_baseline: missing can be downgraded" {
    BASE="$BATS_TEST_TMPDIR/base.txt"
    printf 'AC-FR001-02\nAC-NFR010-01\n' > "$BASE"
    run python3 "$REPO_ROOT/tools/check_acs.py" --acceptance "$FIX/acceptance.md" --tests "$FIX/tests_bad" --legacy-baseline "$BASE"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "unknown" ]]
    [[ "$output" =~ "baseline" ]]
}

@test "CI_TOOLS_T05_check_assertions_pass: good tests pass hygiene" {
    run python3 "$REPO_ROOT/tools/check_assertions.py" --tests "$FIX/tests_good"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "pass" ]]
}

@test "CI_TOOLS_T06_check_assertions_fail: bad patterns fail" {
    run python3 "$REPO_ROOT/tools/check_assertions.py" --tests "$FIX/tests_bad"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "FAKE-001" ]]
    [[ "$output" =~ "FAKE-004" ]]
    [[ "$output" =~ "FAKE-005" ]]
}

@test "CI_TOOLS_T07_check_assertions_json: emits valid JSON" {
    run python3 "$REPO_ROOT/tools/check_assertions.py" --tests "$FIX/tests_bad" --json
    [ "$status" -ne 0 ]
    echo "$output" | python3 -c "import json,sys; d=json.load(sys.stdin); assert d['ok'] is False; assert d['violations']"
}

@test "CI_TOOLS_T08_ci_scan_pass: tools/ci_scan.py aggregates both tools" {
    run python3 "$REPO_ROOT/tools/ci_scan.py" --acceptance "$FIX/acceptance.md" --spec fixtures --tests "$FIX/tests_good"
    [ "$status" -eq 0 ]
}

@test "CI_TOOLS_T09_test_plan_template: strategy doc, no coverage matrix table" {
    TEMPLATE="$REPO_ROOT/templates/test-plan.md"
    grep -q "测试策略" "$TEMPLATE"
    grep -q "AC 追溯约定" "$TEMPLATE"
    grep -q "lk archer ci-scan" "$TEMPLATE"
    ! grep -q "覆盖矩阵" "$TEMPLATE" || grep -q "不在 test-plan 表格" "$TEMPLATE"
}
