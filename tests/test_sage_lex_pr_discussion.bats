#!/usr/bin/env bats
# Sage / Lex 在 spec 004 之后改为 IDE-based quote dialogue 流程
# (取代旧 PR-based review)。仅保留与当前流程 + 新架构相关的断言。

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

# ---------- 新架构:issue form + schema 验证器 ----------

@test "SAGE-FORM-001: Sage 知道 issue form 路径" {
    run grep -q "ISSUE_TEMPLATE" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Sage.md 不引用 .github/ISSUE_TEMPLATE"
        false
    }
}

@test "SAGE-FORM-002: Sage 用 form 字段 (需求 ID / Spec 链接 / 验收标准) 构造 body" {
    for field in "需求 ID" "Spec 链接" "验收标准"; do
        run grep -q "$field" "$AGENTS_DIR/Sage.md"
        [ "$status" -eq 0 ] || { echo "FAIL: Sage.md 缺字段 $field" >&2; false; }
    done
}

@test "SAGE-FORM-003: Sage 使用小写 fr-XXX 锚点" {
    # 用 fr-NNN 字面占位符即可, 不再要求精确的 \d{3} 写法
    run grep -qE "fr-[0-9]{3}" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Sage.md 未使用小写 fr-NNN 锚点"
        false
    }
}

@test "LEX-SCHEMA-001: Lex 运行 verify_issue_schema.py" {
    run grep -q "verify_issue_schema.py" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Lex.md 未引用 verify_issue_schema.py"
        false
    }
}

@test "LEX-SCHEMA-002: Lex 列出 L1-L8 验证项" {
    for level in L1 L2 L3 L4 L5 L6 L7 L8; do
        run grep -q "$level " "$AGENTS_DIR/Lex.md"
        [ "$status" -eq 0 ] || { echo "FAIL: Lex.md 未列 $level" >&2; false; }
    done
}

@test "LEX-SCHEMA-003: Lex 退出条件包含 schema 验证" {
    run grep -q "verify_issue_schema.py" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ]
    run grep -q "Schema" "$AGENTS_DIR/Lex.md"
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

