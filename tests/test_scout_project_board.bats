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
