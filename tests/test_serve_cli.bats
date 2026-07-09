#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

@test "serve CLI: help includes project-root flag" {
    run python -m louke serve --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--project-root"* ]]
}

@test "serve CLI: non-louke directory exits non-zero" {
    WORK="$(mktemp -d)"
    cd "$WORK" || exit 1
    run python -m louke serve --host 127.0.0.1 --port 8765
    [ "$status" -ne 0 ]
    [[ "$output" == *"project.toml"* ]]
}
