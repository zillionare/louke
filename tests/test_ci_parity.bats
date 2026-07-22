#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "FR-0700 AC-1: canonical workflow contains pre-commit run --all-files step" {
    run grep -q "Run pre-commit on all files" "$REPO_ROOT/.github/workflows/louke-ci.yml"
    [ "$status" -eq 0 ]
    run grep -q "pre-commit run --all-files" "$REPO_ROOT/.github/workflows/louke-ci.yml"
    [ "$status" -eq 0 ]
}

@test "FR-0700 AC-2: root .pre-commit-config.yaml exists" {
    [ -f "$REPO_ROOT/.pre-commit-config.yaml" ]
}

@test "FR-0700 AC-2: root .pre-commit-config.yaml merges base.yaml + python.yaml" {
    run grep -q "ruff-pre-commit" "$REPO_ROOT/.pre-commit-config.yaml"
    [ "$status" -eq 0 ]
    run grep -q "mirrors-mypy" "$REPO_ROOT/.pre-commit-config.yaml"
    [ "$status" -eq 0 ]
    run grep -q "check-yaml" "$REPO_ROOT/.pre-commit-config.yaml"
    [ "$status" -eq 0 ]
}

@test "FR-0700 AC-4: pre-commit README links to ci-snippet.yml" {
    run grep -q "ci-snippet.yml" "$REPO_ROOT/louke/templates/pre-commit/README.md"
    [ "$status" -eq 0 ]
}
