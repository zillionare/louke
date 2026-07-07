#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/agents"

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

# --- Identity consistency check ---

@test "SCOUT-ID-001: scout_step4_references_check_identity_py" {
    run grep -qF "check_identity.py" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not reference check_identity.py in Step 4"
        false
    }
}

@test "SCOUT-ID-002: scout_id_check_before_issue_permission_smoke" {
    # Step 4a should be identity consistency, 4b is issue/PR smoke test
    run grep -qE "4a.*identity consistency|identity consistency.*4a" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ]
}

@test "SCOUT-ID-003: scout_exit_criteria_includes_identity_consistent" {
    run grep -qF "identity consistent" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md exit criteria does not include identity consistent"
        false
    }
}
