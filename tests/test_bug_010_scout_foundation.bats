#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/agents"

# --- Collect project metadata ---

@test "SCOUT-010-001: Scout asks user for story/PRD" {
    grep -q "Ask the user for" "$AGENTS_DIR/Scout.md" || {
        echo "FAIL: Scout.md does not ask user for input"
        false
    }
    grep -qE "Story.*/.*PRD" "$AGENTS_DIR/Scout.md" || {
        echo "FAIL: Scout.md does not mention Story/PRD"
        false
    }
}

@test "SCOUT-010-002: Scout asks user for version number" {
    grep -q "Ask the user for" "$AGENTS_DIR/Scout.md" || {
        echo "FAIL: Scout.md does not ask user for input"
        false
    }
    grep -qE "[Vv]ersion number" "$AGENTS_DIR/Scout.md" || {
        echo "FAIL: Scout.md does not ask for version number"
        false
    }
}

@test "SCOUT-010-003: Scout asks user for repo name" {
    grep -q "Ask the user for" "$AGENTS_DIR/Scout.md" || {
        echo "FAIL: Scout.md does not ask user for input"
        false
    }
    grep -qE "[Rr]epo name" "$AGENTS_DIR/Scout.md" || {
        echo "FAIL: Scout.md does not ask for repo name"
        false
    }
}

# --- Create Repo ---

@test "SCOUT-010-004: Scout creates repo via gh if not exists" {
    run grep -qE "gh repo create" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not use gh repo create"
        false
    }
}

@test "SCOUT-010-005: Scout initializes local workspace if repo was just created" {
    run grep -qE "(git clone|git init|local.*workspace)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not initialize local workspace"
        false
    }
}

# --- Project configuration ---

@test "SCOUT-010-006: Scout uses {repo}-{version} as project name" {
    run grep -qE "(\{repo\}.*\{version\}|repo.*-.*version)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not use {repo}-{version} project naming"
        false
    }
}

@test "SCOUT-010-007: Scout links default repository to project" {
    run grep -qE "(default repository|default repo|link.*repo)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not link default repo to project"
        false
    }
}

@test "SCOUT-010-008: Scout writes story to project README" {
    run grep -qiE "(write.*story.*README|story.*README|Writing.*story)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not write story to project README"
        false
    }
}
