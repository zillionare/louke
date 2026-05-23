#!/usr/bin/env bats

AGENTS_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/agents"

# --- 收集项目信息 ---

@test "SCOUT-010-001: Scout asks user for story/PRD" {
    run grep -qE "(询问|ask|收集|拿到).*(story|故事|PRD|需求)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not ask user for story/PRD"
        false
    }
}

@test "SCOUT-010-002: Scout asks user for version number" {
    run grep -qE "(询问|ask|收集|拿到).*(版本|version)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not ask user for version number"
        false
    }
}

@test "SCOUT-010-003: Scout asks user for repo name" {
    run grep -qE "(询问|ask|收集|拿到).*(repo|仓库)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not ask user for repo name"
        false
    }
}

# --- 创建 Repo ---

@test "SCOUT-010-004: Scout creates repo via gh if not exists" {
    run grep -qE "gh repo create" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not use gh repo create"
        false
    }
}

@test "SCOUT-010-005: Scout initializes local workspace if repo was just created" {
    run grep -qE "(git clone|git init|本地.*工作区|local.*workspace)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not initialize local workspace"
        false
    }
}

# --- Project 配置 ---

@test "SCOUT-010-006: Scout uses {repo}-{version} as project name" {
    run grep -qE "(\{repo\}.*\{version\}|repo.*-.*version|项目名.*repo.*version)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not use {repo}-{version} project naming"
        false
    }
}

@test "SCOUT-010-007: Scout links default repository to project" {
    run grep -qE "(default repository|默认.*仓库|关联.*repo)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not link default repo to project"
        false
    }
}

@test "SCOUT-010-008: Scout writes story to project README" {
    run grep -qE "(project.*README|写入.*story|write.*story.*README)" "$AGENTS_DIR/Scout.md"
    [ "$status" -eq 0 ] || {
        echo "FAIL: Scout.md does not write story to project README"
        false
    }
}
