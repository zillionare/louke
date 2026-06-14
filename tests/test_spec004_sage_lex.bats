#!/usr/bin/env bats

# spec 004 task-plan tests
# FR-021: Sage.md no gh api
# FR-022: Lex.md no gh api reviews
# FR-023: README contains IDE flow

setup() {
    TEST_DIR="$(mktemp -d)"
    export SPECFORGE_HOME
    SPECFORGE_HOME="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "T01_sage_no_gh_api_pulls" {
    run grep -E "gh api (repos|pulls)" "$SPECFORGE_HOME/agents/Sage.md"
    [ "$status" -ne 0 ]
}

@test "T02_sage_no_pr_create_or_merge" {
    # Match actual command invocations, not comments mentioning absence
    run grep -E "^\s*gh pr (create|merge)" "$SPECFORGE_HOME/agents/Sage.md"
    [ "$status" -ne 0 ]
}

@test "T03_lex_no_gh_api_reviews" {
    run grep -E "^\s*gh api.*reviews" "$SPECFORGE_HOME/agents/Lex.md"
    [ "$status" -ne 0 ]
}

@test "T04_readme_has_ide_or_quote" {
    run grep -E "(IDE|quote)" "$SPECFORGE_HOME/README.md"
    [ "$status" -eq 0 ]
}

@test "T05_sage_references_quote_parser" {
    run grep -F "tools/quote_parser.py" "$SPECFORGE_HOME/agents/Sage.md"
    [ "$status" -eq 0 ]
}

@test "T06_lex_references_quote_parser" {
    run grep -F "tools/quote_parser.py" "$SPECFORGE_HOME/agents/Lex.md"
    [ "$status" -eq 0 ]
}