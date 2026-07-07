#!/usr/bin/env bats
# Test v0.6-009+ additions: lk upgrade supports --index / --pre / --dry-run

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

# Use PYTHONPATH so lk uses local source (avoid venv installing old version)
LK_BIN="/Users/aaronyang/.local/bin/lk"

setup() {
    export PYTHONPATH="$REPO_ROOT"
}

teardown() {
    rm -f /tmp/louke_upgrade_test_*
}

@test "lk upgrade --help shows new options" {
    run "$LK_BIN" upgrade --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--index"* ]]
    [[ "$output" == *"--pre"* ]]
    [[ "$output" == *"--dry-run"* ]]
}

@test "lk upgrade --dry-run does not actually execute pip" {
    run "$LK_BIN" upgrade --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"Running:"* ]]
    [[ "$output" == *"pip install --upgrade louke"* ]]
    # Should not have 'Successfully installed' output
    [[ ! "$output" == *"Successfully installed"* ]]
}

@test "lk upgrade --dry-run --index URL translates to pip --index-url" {
    run "$LK_BIN" upgrade --dry-run --index https://test.pypi.org/simple/
    [ "$status" -eq 0 ]
    [[ "$output" == *"--index-url https://test.pypi.org/simple/"* ]]
}

@test "lk upgrade --dry-run --pre adds --pre flag" {
    run "$LK_BIN" upgrade --dry-run --pre
    [ "$status" -eq 0 ]
    [[ "$output" == *"--pre"* ]]
}

@test "lk upgrade --dry-run --index URL --pre adds both flags" {
    run "$LK_BIN" upgrade --dry-run --index https://example.com/pypi/ --pre
    [ "$status" -eq 0 ]
    [[ "$output" == *"--index-url https://example.com/pypi/"* ]]
    [[ "$output" == *"--pre"* ]]
}

@test "lk upgrade unknown options are forwarded to pip as-is" {
    # pip's own --force-reinstall option should be passed through
    run "$LK_BIN" upgrade --dry-run --force-reinstall
    [ "$status" -eq 0 ]
    [[ "$output" == *"--force-reinstall"* ]]
    # Our louke-level options should not be added
    [[ ! "$output" == *"--index-url"* ]]
}
