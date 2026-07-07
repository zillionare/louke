#!/usr/bin/env bats
# Sage / Lex switched to IDE-based inline discussion flow after spec 004
# (replaces old PR-based review). Only assertions related to the current flow + new architecture are kept.

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/agents"

# ---------- New architecture: issue form + schema validator ----------

@test "SAGE-FORM-001: sage_knows_issue_form_path" {
    run grep -q "ISSUE_TEMPLATE" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Sage.md does not reference .github/ISSUE_TEMPLATE"
        false
    }
}

@test "SAGE-FORM-002: sage_uses_form_fields_to_construct_body" {
    for field in "Requirement ID" "Spec Link" "Acceptance Criteria"; do
        run grep -q "$field" "$AGENTS_DIR/Sage.md"
        [ "$status" -eq 0 ] || { echo "FAIL: Sage.md missing field $field" >&2; false; }
    done
}

@test "SAGE-FORM-003: sage_uses_lowercase_fr_XXX_anchor" {
    # A literal fr-NNN placeholder is sufficient; no longer requires exact \d{3} format
    run grep -qE "fr-[0-9]{3}" "$AGENTS_DIR/Sage.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Sage.md does not use lowercase fr-NNN anchor"
        false
    }
}

@test "LEX-SCHEMA-001: lex_runs_verify_issue_schema_py" {
    run grep -q "verify_issue_schema.py" "$AGENTS_DIR/Lex.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Lex.md does not reference verify_issue_schema.py"
        false
    }
}

@test "LEX-SCHEMA-002: lex_lists_L1_to_L8_validation_items" {
    for level in L1 L2 L3 L4 L5 L6 L7 L8; do
        run grep -q "$level " "$AGENTS_DIR/Lex.md"
        [ "$status" -eq 0 ] || { echo "FAIL: Lex.md does not list $level" >&2; false; }
    done
}

@test "LEX-SCHEMA-003: lex_exit_criteria_includes_schema_validation" {
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
