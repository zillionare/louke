#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
PY="python3 -m louke"

setup() {
    WORK="$BATS_TEST_TMPDIR/proj"
    mkdir -p "$WORK"
    cd "$WORK"
    git init -q -b main
    git config user.email "bot@example.com"
    git config user.name "bot"
}

@test "FR-0100 AC-2: Scout.md contains Step 5 install pre-commit hook" {
    run grep -q "Step 5: 安装 pre-commit hook" "$REPO_ROOT/louke/agents/Scout.md"
    [ "$status" -eq 0 ]
}

@test "FR-0100 AC-7: install-precommit subcommand exists and --help exits 0" {
    run $PY agent scout install-precommit --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"install-precommit"* ]]
}

@test "FR-0100 AC-3/AC-4: detects python from pyproject.toml and merges base+python config" {
    cp "$REPO_ROOT/tests/fixtures/pyproject-toml/python/pyproject.toml" .
    run $PY agent scout install-precommit
    [ "$status" -eq 0 ]
    [ -f .pre-commit-config.yaml ]
    run grep -q "pre-commit-hooks" .pre-commit-config.yaml
    [ "$status" -eq 0 ]
    run grep -q "ruff-pre-commit" .pre-commit-config.yaml
    [ "$status" -eq 0 ]
    run grep -q "mirrors-mypy" .pre-commit-config.yaml
    [ "$status" -eq 0 ]
}

@test "FR-0100 AC-5: pre-commit install creates .git/hooks/pre-commit" {
    cp "$REPO_ROOT/tests/fixtures/pyproject-toml/python/pyproject.toml" .
    run $PY agent scout install-precommit
    [ "$status" -eq 0 ]
    [ -f .git/hooks/pre-commit ]
}

@test "FR-0100 AC-6: project-info.md records Pre-commit installed line" {
    cp "$REPO_ROOT/tests/fixtures/pyproject-toml/python/pyproject.toml" .
    mkdir -p .louke/project
    printf '%s\n' \
        "# Project Info" \
        "- **Version**: v0.1" \
        > .louke/project/project-info.md
    run $PY agent scout install-precommit
    [ "$status" -eq 0 ]
    run grep -qE "Pre-commit\\*\\*:[[:space:]]*installed[[:space:]]*\\(python[[:space:]]*\\+[[:space:]]*base\\)" .louke/project/project-info.md
    [ "$status" -eq 0 ]
}

@test "FR-0100 AC-7: --force overwrites existing .pre-commit-config.yaml" {
    cp "$REPO_ROOT/tests/fixtures/pyproject-toml/python/pyproject.toml" .
    printf '%s\n' "repos: []" > .pre-commit-config.yaml
    run $PY agent scout install-precommit --force
    [ "$status" -eq 0 ]
    run grep -q "pre-commit-hooks" .pre-commit-config.yaml
    [ "$status" -eq 0 ]
}

@test "FR-0100 AC-3: detection priority picks pyproject.toml over package.json" {
    cp "$REPO_ROOT/tests/fixtures/pyproject-toml/python/pyproject.toml" .
    printf '{"name":"demo"}\n' > package.json
    run $PY agent scout install-precommit
    [ "$status" -eq 0 ]
    run grep -q "ruff-pre-commit" .pre-commit-config.yaml
    [ "$status" -eq 0 ]
    run grep -q "mirrors-eslint" .pre-commit-config.yaml
    [ "$status" -ne 0 ]
}
