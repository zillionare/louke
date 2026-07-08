#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/agents"

@test "SCOUT-PROJECT-001: Scout creates release project with repo-version title" {
    run grep -qE "project .*\\{repo_name\\}-\\{version\\}|Project: \\{repo\\}-\\{version\\}|repo-\\{version\\}" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not specify project title format"
        false
    }
}

@test "SCOUT-PROJECT-002: Scout ensures per-repo backlog project exists" {
    run grep -qE "backlog Project|\\{repo_name\\}-backlog|backlog project" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not mention backlog project"
        false
    }
}

@test "SCOUT-PROJECT-003: Scout adds owner as project collaborator" {
    run grep -qE "invite-owner|collaborator" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not define collaborator step"
        false
    }
}

# --- Identity consistency check ---

@test "SCOUT-ID-001: scout_step2_references_check_identity_py" {
    run grep -qF "check_identity.py" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not reference check_identity.py in identity step"
        false
    }
}

@test "SCOUT-ID-002: scout_id_check_runs_before_foundation smoke test" {
    run grep -qE "Step 2: Call `lk agent scout identity-check`" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ]
}

@test "SCOUT-ID-003: scout_exit_criteria_includes_identity_consistent" {
    run grep -qF "identity consistent" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md exit criteria does not include identity consistent"
        false
    }
}
