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

@test "SCOUT-010-005: Scout continues in current local workspace after repo creation" {
    run grep -qE "(current local workspace|already running in)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not explain current-workspace behavior"
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

@test "SCOUT-010-007: Scout writes project.toml as the foundation source of truth" {
    run grep -qE "project\\.toml" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not mention project.toml output"
        false
    }
}

@test "SCOUT-010-008: Scout writes story to story.md" {
    run grep -qiE "(write.*story\\.md|Writing `story\\.md`|story\\.md)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not write story to story.md"
        false
    }
}
