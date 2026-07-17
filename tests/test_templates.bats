#!/usr/bin/env bats

TEMPLATES_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/templates"

@test "UT-011-01: prd.md exists" {
    [ -f "$TEMPLATES_DIR/prd.md" ]
}

@test "UT-011-02: spec.md exists" {
    [ -f "$TEMPLATES_DIR/spec.md" ]
}

@test "UT-011-03: issues.md exists" {
    [ -f "$TEMPLATES_DIR/issues.md" ]
}

@test "UT-011-04: test-plan.md exists" {
    [ -f "$TEMPLATES_DIR/test-plan.md" ]
}

@test "UT-011-05: task-plan.md exists" {
    [ -f "$TEMPLATES_DIR/task-plan.md" ]
}

@test "UT-011-06: task-log.md exists" {
    [ -f "$TEMPLATES_DIR/task-log.md" ]
}

@test "UT-011-07: acceptance.md exists" {
    [ -f "$TEMPLATES_DIR/acceptance.md" ]
}

@test "UT-011-08: bug-fix.md exists" {
    [ -f "$TEMPLATES_DIR/bug-fix.md" ]
}

@test "UT-012-01: prd.md has all required level-2 headings" {
    for heading in "Background" "Goals" "Acceptance Criteria" "Out of Scope" "Risks"; do
        run grep -q "^## ${heading}" "$TEMPLATES_DIR/prd.md"
        [ "$status" -eq 0 ] || { echo "Missing heading: ## ${heading}" >&2; false; }
    done
}

@test "UT-012-02: spec.md has all required level-2 headings" {
    for heading in "Functional Requirements" "Non-Functional Requirements" "Clarification Log"; do
        run grep -q "^## ${heading}" "$TEMPLATES_DIR/spec.md"
        [ "$status" -eq 0 ] || { echo "Missing heading: ## ${heading}" >&2; false; }
    done
}

@test "UT-012-04: spec.md does not duplicate Story narrative sections" {
    run grep -Eq "^## (User Stories|Usage Scenarios)$" "$TEMPLATES_DIR/spec.md"
    [ "$status" -ne 0 ] || { echo "spec.md must not duplicate story.md narrative sections" >&2; false; }
}

@test "UT-012-03: task-log.md has all required level-2 headings" {
    for heading in "Phase 1: Red" "Phase 2: Green" "Phase 3: Refactor" "Keeper"; do
        run grep -q "^## ${heading}" "$TEMPLATES_DIR/task-log.md"
        [ "$status" -eq 0 ] || { echo "Missing heading: ## ${heading}" >&2; false; }
    done
}
