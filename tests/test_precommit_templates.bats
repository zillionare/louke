#!/usr/bin/env bats

PRE_COMMIT_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/templates/pre-commit"

assert_fixed_rev() {
    local file="$1"
    while IFS= read -r line; do
        case "$line" in
            *main*|*master*)
                echo "Forbidden branch reference in ${file}: $line" >&2
                false
                ;;
        esac
    done < <(grep -E '^\s*rev:' "$file")
}

@test "FR-0200 AC-1 base.yaml exists with 6 hooks" {
    [ -f "$PRE_COMMIT_DIR/base.yaml" ]
    for hook in trailing-whitespace end-of-file-fixer check-yaml check-toml check-merge-conflict check-added-large-files; do
        run grep -Eq "^\s*-\s+id:\s*${hook}\s*$" "$PRE_COMMIT_DIR/base.yaml"
        [ "$status" -eq 0 ] || { echo "Missing hook id: $hook" >&2; false; }
    done
}

@test "FR-0200 AC-1 base.yaml uses fixed rev tags" {
    assert_fixed_rev "$PRE_COMMIT_DIR/base.yaml"
}

@test "FR-0200 AC-2 each language template exists with fixed rev" {
    for lang in python node go rust java; do
        [ -f "$PRE_COMMIT_DIR/${lang}.yaml" ]
        assert_fixed_rev "$PRE_COMMIT_DIR/${lang}.yaml"
    done
}

@test "FR-0200 AC-2-python includes ruff + mypy hooks" {
    run grep -q "astral-sh/ruff-pre-commit" "$PRE_COMMIT_DIR/python.yaml"
    [ "$status" -eq 0 ]
    run grep -q "mirrors-mypy" "$PRE_COMMIT_DIR/python.yaml"
    [ "$status" -eq 0 ]
}

@test "FR-0200 AC-2-go includes golangci-lint + gofmt + go-test" {
    run grep -qE "(dnephin|dominikh)/pre-commit-golang" "$PRE_COMMIT_DIR/go.yaml"
    [ "$status" -eq 0 ]
    run grep -q "golangci-lint" "$PRE_COMMIT_DIR/go.yaml"
    [ "$status" -eq 0 ]
    run grep -qE "go-fmt|gofmt" "$PRE_COMMIT_DIR/go.yaml"
    [ "$status" -eq 0 ]
    run grep -qE "go-unit-tests|go-test|go_unit_tests" "$PRE_COMMIT_DIR/go.yaml"
    [ "$status" -eq 0 ]
}

@test "FR-0200 AC-2-node includes eslint hook" {
    run grep -q "mirrors-eslint" "$PRE_COMMIT_DIR/node.yaml"
    [ "$status" -eq 0 ]
}

@test "FR-0200 AC-2-rust includes rustfmt + clippy" {
    run grep -q "pre-commit-rust" "$PRE_COMMIT_DIR/rust.yaml"
    [ "$status" -eq 0 ]
    run grep -qE "id:\s*(rustfmt|fmt)" "$PRE_COMMIT_DIR/rust.yaml"
    [ "$status" -eq 0 ]
    run grep -qE "id:\s*(clippy|cargo-check)" "$PRE_COMMIT_DIR/rust.yaml"
    [ "$status" -eq 0 ]
}

@test "FR-0200 AC-2-java includes checkstyle + google-java-format" {
    run grep -q "pre-commit-java" "$PRE_COMMIT_DIR/java.yaml"
    [ "$status" -eq 0 ]
    run grep -q "checkstyle" "$PRE_COMMIT_DIR/java.yaml"
    [ "$status" -eq 0 ]
    run grep -q "google-java-format" "$PRE_COMMIT_DIR/java.yaml"
    [ "$status" -eq 0 ]
}

@test "FR-0200 AC-3 concatenation snippet files exist" {
    [ -f "$PRE_COMMIT_DIR/ci-snippet.yml" ]
    [ -f "$PRE_COMMIT_DIR/README.md" ]
}
