#!/usr/bin/env bats

setup() {
    TEST_DIR="$(mktemp -d)"
    SPECFORGE_HOME="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
    export SPECFORGE_HOME
    cd "$TEST_DIR"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "UT-001-01: init creates project directory" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    [ -d "test-project" ]
}

@test "UT-001-02: init fails when directory exists" {
    mkdir test-project
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -ne 0 ]
}

@test "UT-002-01: init creates agents/ with agent files" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    AGENT_COUNT=$(ls test-project/agents/*.md 2>/dev/null | wc -l)
    [ "$AGENT_COUNT" -ge 19 ]
}

@test "UT-002-02: init creates templates/ with 8 files" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    TEMPLATE_COUNT=$(ls test-project/templates/*.md 2>/dev/null | wc -l)
    [ "$TEMPLATE_COUNT" -ge 8 ]
}

@test "UT-002-03: init creates wiki/pages/" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    [ -d "test-project/wiki/pages" ]
}

@test "UT-002-04: init creates wiki/decisions/" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    [ -d "test-project/wiki/decisions" ]
}

@test "UT-002-05: init creates .specforge/project/" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    [ -d "test-project/.specforge/project" ]
}

@test "UT-003-01: init prints onboarding guidance" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    [[ "$output" =~ 下一步 ]] || [[ "$output" =~ [Nn]ext ]]
}

@test "UT-003-02: init prints model recommendations" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    [[ "$output" =~ deepseek ]] || [[ "$output" =~ kimi ]]
}
