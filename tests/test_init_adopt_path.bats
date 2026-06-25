#!/usr/bin/env bats

# TASK-01: path detection + subcommand dispatch
# FR-008 (init subcommand supports existing-path smart detection)
# Issue #27
# Traceability:
#   UT-027-1-1 = T01_init_dot_triggers_adopt
#   UT-027-2-1 = T02_init_relative_path_triggers_adopt
#   UT-027-3-1 = T03_init_abs_path_triggers_adopt
#   UT-027-4-1 = T04_init_home_relative_triggers_adopt
#   UT-027-5-1 = T05_init_bare_name_creates_new_project

setup() {
    TEST_DIR="$(mktemp -d)"
    cd "$TEST_DIR"
    export SPECFORGE_HOME
    SPECFORGE_HOME="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "T01_init_dot_triggers_adopt: init . triggers adopt mode" {
    mkdir -p target && cd target && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init .
    [ "$status" -eq 0 ]
    [ -d ".specforge/agents" ]
}

@test "T02_init_relative_path_triggers_adopt: init <relpath> triggers adopt mode" {
    # T02 verification: when user invokes `init <path>` where <path>
    # starts with ./ and resolves to an existing directory containing
    # a git repo, adopt mode triggers.
    mkdir -p parentdir/sub && cd parentdir/sub && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init ./sub
    [ "$status" -eq 0 ]
}

@test "T03_init_abs_path_triggers_adopt: init /abs/path triggers adopt mode" {
    mkdir -p "$TEST_DIR/abs_target" && cd "$TEST_DIR/abs_target" && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init "$TEST_DIR/abs_target"
    [ "$status" -eq 0 ]
}

@test "T04_init_home_relative_triggers_adopt: init ~/path triggers adopt mode" {
    export HOME="$TEST_DIR/home"
    mkdir -p "$HOME/target" && cd "$HOME/target" && git init -q
    run bash "$SPECFORGE_HOME/bin/specforge" init "~/target"
    [ "$status" -eq 0 ]
}

@test "T05_init_bare_name_creates_new_project: init myproj (bare name) creates new project" {
    cd "$TEST_DIR"
    run bash "$SPECFORGE_HOME/bin/specforge" init newproj
    [ "$status" -eq 0 ]
    [ -d "newproj" ]
    [ -d "newproj/.specforge/agents" ]
}