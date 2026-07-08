#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

setup() {
    WORK="$(mktemp -d)"
    cd "$WORK" || exit 1
}

teardown() {
    cd "$REPO_ROOT" || true
    rm -rf "$WORK"
}

write_base_fixture() {
    mkdir -p .louke/project/specs/demo app tests/e2e
    cat > .louke/project/specs/demo/test-plan.md <<'EOF'
## 测试策略

- unit
- integration
- e2e
EOF
    cat > .louke/project/specs/demo/interfaces.md <<'EOF'
# Interfaces
EOF
    cat > .louke/project/specs/demo/architecture.md <<'EOF'
## 模块划分

- api

## FR mapping

- FR-0001 -> api
EOF
}

@test "validate-arch rejects missing [e2e].run and writes fail artifact" {
    write_base_fixture
    cat > .louke/project/project.toml <<'EOF'
[meta]
spec_id = "demo"
test_framework = "pytest"

[e2e]
paths = ["tests/e2e"]
cwd = "app"
EOF

    run python -m louke agent archer validate-arch --spec demo
    [ "$status" -ne 0 ]
    [[ "$output" == *"missing [e2e].run"* ]]
    [ -f .louke/project/stage-results/demo/M-ARCH/author-result.json ]
}

@test "validate-arch rejects missing host-project e2e path" {
    write_base_fixture
    cat > .louke/project/project.toml <<'EOF'
[meta]
spec_id = "demo"
test_framework = "pytest"

[e2e]
cwd = "app"
run = "pytest -q tests/e2e"
paths = ["tests/missing-e2e"]
EOF

    run python -m louke agent archer validate-arch --spec demo
    [ "$status" -ne 0 ]
    [[ "$output" == *"[e2e].paths target does not exist"* ]]
}

@test "validate-arch passes when [e2e] contract and roots are complete" {
    write_base_fixture
    cat > .louke/project/project.toml <<'EOF'
[meta]
spec_id = "demo"
test_framework = "pytest"

[e2e]
cwd = "app"
run = "pytest -q ../tests/e2e"
paths = ["tests/e2e"]
EOF

    run python -m louke agent archer validate-arch --spec demo
    [ "$status" -eq 0 ] || {
        echo "$output" >&2
        false
    }
    [[ "$output" == *"architecture OK"* ]]
}
