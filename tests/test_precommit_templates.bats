#!/usr/bin/env bats

PC_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)/louke/templates/pre-commit"

@test "FR-0200 AC-1 base.yaml exists with 6 hooks" {
    [ -f "$PC_DIR/base.yaml" ]
    for hook in trailing-whitespace end-of-file-fixer check-yaml check-toml check-merge-conflict check-added-large-files; do
        run grep -Eq "^\s*-\s+id:\s*${hook}\s*$" "$PC_DIR/base.yaml"
        [ "$status" -eq 0 ] || { echo "Missing hook id: $hook" >&2; false; }
    done
}

@test "FR-0200 AC-1 base.yaml uses fixed rev tags" {
    while IFS= read -r line; do
        case "$line" in
            *main*|*master*)
                echo "Forbidden branch reference in base.yaml: $line" >&2
                false
                ;;
        esac
    done < <(grep -E '^\s*rev:' "$PC_DIR/base.yaml")
}

@test "FR-0200 AC-2 each language template exists with fixed rev" {
    for lang in python node go rust java; do
        [ -f "$PC_DIR/${lang}.yaml" ]
        while IFS= read -r line; do
            case "$line" in
                *main*|*master*)
                    echo "Forbidden branch reference in ${lang}.yaml: $line" >&2
                    false
                    ;;
            esac
        done < <(grep -E '^\s*rev:' "$PC_DIR/${lang}.yaml")
    done
}

@test "FR-0200 AC-2-python includes ruff + mypy hooks" {
    run grep -q "astral-sh/ruff-pre-commit" "$PC_DIR/python.yaml"
    [ "$status" -eq 0 ]
    run grep -q "mirrors-mypy" "$PC_DIR/python.yaml"
    [ "$status" -eq 0 ]
}

@test "FR-0200 AC-2-go includes golangci-lint + gofmt + go-test" {
    run grep -qE "(dnephin|dominikh)/pre-commit-golang" "$PC_DIR/go.yaml"
    [ "$status" -eq 0 ]
    run grep -q "golangci-lint" "$PC_DIR/go.yaml"
    [ "$status" -eq 0 ]
    run grep -qE "go-fmt|gofmt" "$PC_DIR/go.yaml"
    [ "$status" -eq 0 ]
    run grep -qE "go-unit-tests|go-test|go_unit_tests" "$PC_DIR/go.yaml"
    [ "$status" -eq 0 ]
}

@test "FR-0200 AC-2-node includes eslint hook" {
    run grep -q "mirrors-eslint" "$PC_DIR/node.yaml"
    [ "$status" -eq 0 ]
}

@test "FR-0200 AC-2-rust includes rustfmt + clippy" {
    run grep -q "pre-commit-rust" "$PC_DIR/rust.yaml"
    [ "$status" -eq 0 ]
    run grep -qE "id:\s*(rustfmt|fmt)" "$PC_DIR/rust.yaml"
    [ "$status" -eq 0 ]
    run grep -qE "id:\s*(clippy|cargo-check)" "$PC_DIR/rust.yaml"
    [ "$status" -eq 0 ]
}

@test "FR-0200 AC-2-java includes checkstyle + google-java-format" {
    run grep -q "pre-commit-java" "$PC_DIR/java.yaml"
    [ "$status" -eq 0 ]
    run grep -q "checkstyle" "$PC_DIR/java.yaml"
    [ "$status" -eq 0 ]
    run grep -q "google-java-format" "$PC_DIR/java.yaml"
    [ "$status" -eq 0 ]
}

@test "FR-0200 AC-3 concatenation snippet files exist" {
    [ -f "$PC_DIR/ci-snippet.yml" ]
    [ -f "$PC_DIR/README.md" ]
}
