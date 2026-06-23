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

@test "UT-002-01: init creates .specforge/agents/ with agent files" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    AGENT_COUNT=$(ls test-project/.specforge/agents/*.md 2>/dev/null | wc -l)
    [ "$AGENT_COUNT" -ge 19 ]
    # v0.5-005: root MUST NOT have agents/
    [ ! -d "test-project/agents" ]
}

@test "UT-002-02: init creates .specforge/templates/ with 8 files" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    TEMPLATE_COUNT=$(ls test-project/.specforge/templates/*.md 2>/dev/null | wc -l)
    [ "$TEMPLATE_COUNT" -ge 8 ]
    # v0.5-005: root MUST NOT have templates/
    [ ! -d "test-project/templates" ]
}

@test "UT-002-03: init creates .specforge/wiki/pages/ (v0.5-005: was wiki/pages/)" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    [ -d "test-project/.specforge/wiki/pages" ]
    [ ! -d "test-project/wiki" ]
}

@test "UT-002-04: init creates .specforge/wiki/decisions/ (v0.5-005: was wiki/decisions/)" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    [ -d "test-project/.specforge/wiki/decisions" ]
}

@test "UT-002-06: init creates .specforge/raw/sources/ (v0.5-005: was raw/sources/)" {
    run bash "$SPECFORGE_HOME/bin/specforge" init test-project
    [ "$status" -eq 0 ]
    [ -d "test-project/.specforge/raw/sources" ]
    [ ! -d "test-project/raw" ]
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
