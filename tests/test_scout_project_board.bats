#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

@test "SCOUT-PROJECT-001: Scout creates project with title format repo-slug v{version}" {
    run grep -qF "gh project create --title" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not specify project title format"
        false
    }
}

@test "SCOUT-PROJECT-002: Scout configures status board with Backlog/In Progress/Pending Verify/Done" {
    run grep -qE "(Backlog|In [Pp]rogress|Pending Verify|Done).*(pink|red|yellow|green)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not configure status board columns"
        false
    }
}

@test "SCOUT-PROJECT-003: Scout sets up status field with these 4 options" {
    run grep -qE "(status|Status).*(Backlog|In Progress|Pending Verify|Done)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not define status field options"
        false
    }
}

# ---------- 身份一致性检查 ----------

@test "SCOUT-ID-001: scout_step4_references_check_identity_py" {
    run grep -qF "check_identity.py" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md 未在 Step 4 引用 check_identity.py"
        false
    }
}

@test "SCOUT-ID-002: scout_id_check_before_issue_permission_smoke" {
    # Step 4a 应该是身份一致性,4b 才是 issue/PR 冒烟
    run grep -qE "4a.*身份一致性|身份一致性.*4a" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ]
}

@test "SCOUT-ID-003: scout_exit_criteria_includes_identity_consistent" {
    run grep -qF "身份一致" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md 退出条件未含身份一致"
        false
    }
}
