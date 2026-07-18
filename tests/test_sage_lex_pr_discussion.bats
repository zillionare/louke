#!/usr/bin/env bats
# Sage / Lex switched to IDE-based inline discussion flow after spec 004
# (replaces old PR-based review). Only assertions related to the current flow + new architecture are kept.

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

@test "SAGE-ANALYSIS-001: Sage checks Happy Path and Devon-only implementability" {
    run grep -q "Happy Path 每一步" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
    run grep -q "Devon 只读取 spec.md 和 acceptance.md" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
}

@test "SAGE-ANALYSIS-002: Sage checks human-facing interaction dimensions and inherited contracts" {
    run grep -q "面向人的交互合同" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
    run grep -q "一个 BS 到一个 FR 的编号映射" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
    run grep -q "artifact identity、revision/digest 和需求锚点" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ]
}

@test "LEX-BOUNDARY-001: Lex does not repeat program validation" {
    run grep -Eq "lk agent lex (verify-acceptance|verify-issue|verify-project|quote-check)" "$AGENTS_DIR/Lex.md"
    [ "$status" -ne 0 ]
}

@test "LEX-SEMANTIC-001: Lex checks Story coverage and assertability" {
    run grep -q "Happy Path" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
    run grep -q "可断言" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
}

@test "LEX-SEMANTIC-002: Lex independently rejects incomplete interaction contracts" {
    run grep -q "面向人的交互完整性" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
    run grep -q "只映射到一个 FR 编号" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
    run grep -q "不得只证明后台状态发生变化" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
}

@test "SCRIBE-DISCOVERY-001: Scribe captures interaction facts without designing UI" {
    run grep -q "交互闭环" "$AGENTS_DIR/Scribe.md"
    [ "$status" -eq 0 ]
    run grep -q "不设计组件树、CSS 或内部 API" "$AGENTS_DIR/Scribe.md"
    [ "$status" -eq 0 ]
    run grep -q "复用现有界面/交互" "$AGENTS_DIR/Scribe.md"
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
