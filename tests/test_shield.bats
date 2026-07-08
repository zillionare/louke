#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

setup() {
    TEST_REPO="$(mktemp -d)"
    cd "$TEST_REPO" || exit 1
    git init -q
    git config user.email "shield@example.com"
    git config user.name "Shield"
    mkdir -p .louke/project
}

teardown() {
    cd "$REPO_ROOT" || true
    rm -rf "$TEST_REPO"
}

@test "shield run-e2e fails fast when [e2e].run is missing" {
    cat > .louke/project/project.toml <<'EOF'
[meta]
project = "demo"
EOF

    run python -m louke agent shield run-e2e
    [ "$status" -ne 0 ]
    [[ "$output" == *"missing [e2e].run"* ]]
}

@test "shield run-e2e executes host-project command from configured cwd" {
    mkdir -p app
    cat > .louke/project/project.toml <<'EOF'
[e2e]
cwd = "app"
run = "./run-e2e.sh"
EOF
    cat > app/run-e2e.sh <<'EOF'
#!/usr/bin/env bash
echo "host e2e ran from $(pwd)"
exit 0
EOF
    chmod +x app/run-e2e.sh

    run python -m louke agent shield run-e2e
    [ "$status" -eq 0 ] || {
        echo "$output" >&2
        false
    }
    [[ "$output" == *"host e2e ran from"* ]]
    [[ "$output" == *"/app"* ]]
}

@test "shield commit-e2e rejects .louke paths" {
    cat > .louke/project/project.toml <<'EOF'
[meta]
project = "demo"
EOF

    run python -m louke agent shield commit-e2e \
        --message "cover demo" \
        --paths .louke/project/specs/v0.7-001/tests/e2e
    [ "$status" -ne 0 ]
    [[ "$output" == *"must point to host-project assets, not .louke/"* ]]
}
