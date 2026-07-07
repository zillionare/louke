#!/usr/bin/env bats
# v0.6-008 P0-B: Sage create-issues / record-lock / verify-project
# fix-002: project-info.md → project.toml

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
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

@test "SAGE-CREATE-ISSUES: project.toml missing -> exit 1 with actionable msg" {
    mkdir -p .louke/project/specs/v0.6-008-test
    printf '<a id="fr-0001"></a>\n### FR-0001 demo\n' > .louke/project/specs/v0.6-008-test/spec.md
    run $PY agent sage create-issues --spec v0.6-008-test
    [ "$status" -ne 0 ]
    [[ "$output" == *"Repo field missing"* ]]
}

@test "SAGE-CREATE-ISSUES: project.toml missing Release Branch -> exit 1 with actionable msg" {
    mkdir -p .louke/project/specs/v0.6-008-test
    printf '<a id="fr-0001"></a>\n### FR-0001 demo\n' > .louke/project/specs/v0.6-008-test/spec.md
    mkdir -p .louke/project
    cat > .louke/project/project.toml <<'EOF'
[project]
repo = "github.com/foo/bar"
EOF
    run $PY agent sage create-issues --spec v0.6-008-test
    [ "$status" -ne 0 ]
    [[ "$output" == *"Release Branch field missing"* ]]
}

@test "SAGE-CREATE-ISSUES: 0 FR anchors -> exit 0 with '0 created, 0 skipped'" {
    mkdir -p .louke/project/specs/v0.6-008-test
    printf 'no anchors\n' > .louke/project/specs/v0.6-008-test/spec.md
    mkdir -p .louke/project
    cat > .louke/project/project.toml <<'EOF'
[project]
repo = "github.com/foo/bar"
release_branch = "releases/v0.6"
project_id = "https://github.com/users/foo/projects/1"
EOF
    run $PY agent sage create-issues --spec v0.6-008-test
    [ "$status" -eq 0 ]
    [[ "$output" == *"0 created, 0 skipped"* ]]
}

@test "SAGE-RECORD-LOCK: missing --confirm -> User signal error" {
    run $PY agent sage record-lock --spec v0.6-008-test
    [ "$status" -ne 0 ]
    [[ "$output" == *"User signal"* ]]
}

@test "LEX-VERIFY-PROJECT: project.toml missing -> exit 1 with actionable msg" {
    run $PY agent lex verify-project --spec v0.6-008-test
    [ "$status" -ne 0 ]
    [[ "$output" == *"Project URL missing"* ]] || [[ "$output" == *"scout foundation"* ]]
}
