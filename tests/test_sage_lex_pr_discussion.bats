#!/usr/bin/env bats
# Semantic contracts for Story discovery, Spec conversion, and independent review.

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/agents"

# ---------- v0.14 semantic/program boundary ----------

@test "SAGE-BOUNDARY-001: Sage does not drive program side effects" {
    run grep -Eq "lk agent sage (commit-spec|quote-check|create-issues|record-lock)" "$AGENTS_DIR/Sage.md"
    [ "$status" -ne 0 ]
}

@test "SAGE-BOUNDARY-002: inline discussion is default and question is fallback" {
    run grep -q "question.*例外" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
    run grep -q "inline discussion" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
}

@test "SAGE-INTEGRATION-001: Sage derives an end-to-end path in the existing product" {
    run grep -q "Product Integration Pass" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
    run grep -q "现有上下文 → 入口/触发 → 关键动作 → 可见结果 → 继续/返回" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
    run grep -q "自然挂载点" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
    run grep -q "孤立页面" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
}

@test "SAGE-INFERENCE-001: Sage resolves stable derivations without asking Human" {
    run grep -q "可追溯、无实质竞争方案的稳定推导" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
    run grep -q "Human 沉默不批准" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
    run grep -q "每轮最多提出三个产品问题" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
    run grep -q "普通默认不要求逐项映射" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
}

@test "LEX-BOUNDARY-001: Lex does not repeat program validation" {
    run grep -Eq "lk agent lex (verify-acceptance|verify-issue|verify-project|quote-check)" "$AGENTS_DIR/Lex.md"
    [ "$status" -ne 0 ]
}

@test "LEX-SEMANTIC-001: Lex checks complete product integration and assertability" {
    run grep -q "完整操作路径与有机集成" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
    run grep -q "现有上下文 → 入口/触发 → 关键动作 → 结果位置 → 继续/返回" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
    run grep -q "可断言" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
}

@test "LEX-SEMANTIC-002: Lex rejects both structural gaps and micro over-specification" {
    run grep -q "结构缺失" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
    run grep -q "微观过度规定" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
    run grep -q "普通行为未被逐字写入 Spec，不是 blocker" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
}

@test "SCRIBE-DISCOVERY-001: Scribe asks minimally and infers ordinary behavior" {
    run grep -q "推导优先于提问" "$AGENTS_DIR/Scribe.md"
    [ "$status" -eq 0 ]
    run grep -q "每轮默认提出 0–2 个问题，最多 3 个" "$AGENTS_DIR/Scribe.md"
    [ "$status" -eq 0 ]
    run grep -q "现有上下文 → 入口 → 关键动作 → 可见结果 → 继续/返回" "$AGENTS_DIR/Scribe.md"
    [ "$status" -eq 0 ]
    run grep -q "无确认永久删除" "$AGENTS_DIR/Scribe.md"
    [ "$status" -eq 0 ]
}

@test "SCRIBE-DISCOVERY-002: Scribe does not regress to a mandatory questionnaire" {
    run grep -q "你必须提出以下问题" "$AGENTS_DIR/Scribe.md"
    [ "$status" -ne 0 ]
    run grep -q "至少识别出 3 条关键假设和 3 条主要风险" "$AGENTS_DIR/Scribe.md"
    [ "$status" -ne 0 ]
}

@test "DEVON-INFERENCE-001: Devon implements ordinary defaults without inventing product policy" {
    run grep -q "Spec/Acceptance 不会枚举所有普通交互细节" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
    run grep -q "它们不是“额外功能”" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
    run grep -q "不得自行发明入口、权限、作用范围、业务政策" "$AGENTS_DIR/Devon.md"
    [ "$status" -eq 0 ]
}

@test "RUNTIME-SCOPE-001: Maestro checks Spec scope before Lex" {
    run grep -q "spec_scope_check" "$AGENTS_DIR/Maestro.md"
    [ "$status" -eq 0 ]
}

@test "NO-CLERK: Clerk.md has been removed" {
    run [ ! -f "$AGENTS_DIR/Clerk.md" ]
    [ "$status" -eq 0 ] || {
        echo "FAIL: Clerk.md still exists, should have been removed after merge into Lex"
        false
    }
}

@test "NO-AUDITOR: Auditor.md has been removed" {
    run [ ! -f "$AGENTS_DIR/Auditor.md" ]
    [ "$status" -eq 0 ] || {
        echo "FAIL: Auditor.md still exists, should have been removed after merge into Lex"
        false
    }
}
