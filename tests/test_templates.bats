#!/usr/bin/env bats

TEMPLATES_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/templates"

@test "UT-011-01: prd.md exists" {
    [ -f "$TEMPLATES_DIR/prd.md" ]
}

@test "UT-011-02: spec.md exists" {
    [ -f "$TEMPLATES_DIR/spec.md" ]
}

@test "UT-011-03: issues.md exists" {
    [ -f "$TEMPLATES_DIR/issues.md" ]
}

@test "UT-011-04: test-plan.md exists" {
    [ -f "$TEMPLATES_DIR/test-plan.md" ]
}

@test "UT-011-05: task-plan.md exists" {
    [ -f "$TEMPLATES_DIR/task-plan.md" ]
}

@test "UT-011-06: task-log.md exists" {
    [ -f "$TEMPLATES_DIR/task-log.md" ]
}

@test "UT-011-07: acceptance.md exists" {
    [ -f "$TEMPLATES_DIR/acceptance.md" ]
}

@test "UT-011-08: bug-fix.md exists" {
    [ -f "$TEMPLATES_DIR/bug-fix.md" ]
}

@test "UT-011-09: story.md exists" {
    [ -f "$TEMPLATES_DIR/story.md" ]
}

@test "UT-012-01: prd.md has all required level-2 headings" {
    for heading in "Background" "Goals" "Acceptance Criteria" "Out of Scope" "Risks"; do
        run grep -q "^## ${heading}" "$TEMPLATES_DIR/prd.md"
        [ "$status" -eq 0 ] || { echo "Missing heading: ## ${heading}" >&2; false; }
    done
}

@test "UT-012-02: spec.md has all required level-2 headings" {
    for heading in "功能需求" "非功能需求" "澄清记录"; do
        run grep -q "^## ${heading}" "$TEMPLATES_DIR/spec.md"
        [ "$status" -eq 0 ] || { echo "Missing heading: ## ${heading}" >&2; false; }
    done
}

@test "UT-012-04: spec.md does not duplicate Story narrative sections" {
    run grep -Eq "^## (用户故事|使用场景)$" "$TEMPLATES_DIR/spec.md"
    [ "$status" -ne 0 ] || { echo "spec.md must not duplicate story.md narrative sections" >&2; false; }
}

@test "UT-012-05: spec.md declares the 30 active requirement limit" {
    run grep -q "最多包含 30 个有效 FR；NFR 不计入" "$TEMPLATES_DIR/spec.md"
    [ "$status" -eq 0 ]
}

@test "UT-012-08: spec.md uses parser-supported Chinese metadata columns" {
    run grep -q "| 有效需求 | 可测性 | 是否已决定 |" "$TEMPLATES_DIR/spec.md"
    [ "$status" -eq 0 ]
    run grep -q "\*\*来源\*\*" "$TEMPLATES_DIR/spec.md"
    [ "$status" -eq 0 ]
}

@test "UT-012-06: story.md captures a lean end-to-end product path" {
    for heading in "用户意图" "核心操作路径" "范围、约束与例外" "重要推导与证据" "开放产品决定"; do
        run grep -q "^## .*${heading}" "$TEMPLATES_DIR/story.md"
        [ "$status" -eq 0 ] || { echo "Missing Story heading containing: ${heading}" >&2; false; }
    done
    run grep -q "起点上下文" "$TEMPLATES_DIR/story.md"
    [ "$status" -eq 0 ]
    run grep -q "继续/返回" "$TEMPLATES_DIR/story.md"
    [ "$status" -eq 0 ]
}

@test "UT-012-07: story.md does not require generic questionnaire fields or quotas" {
    for stale_field in "用户规模" "使用频次" "网络环境" "升级与迁移" "量化指标 1" "### A-01" "### R-01"; do
        run grep -Fq "$stale_field" "$TEMPLATES_DIR/story.md"
        [ "$status" -ne 0 ] || { echo "Story template still requires stale field: ${stale_field}" >&2; false; }
    done
}

@test "UT-012-03: task-log.md has all required level-2 headings" {
    for heading in "Phase 1: Red" "Phase 2: Green" "Phase 3: Refactor" "Keeper"; do
        run grep -q "^## ${heading}" "$TEMPLATES_DIR/task-log.md"
        [ "$status" -eq 0 ] || { echo "Missing heading: ## ${heading}" >&2; false; }
    done
}
