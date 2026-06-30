#!/usr/bin/env bats
# v0.6-008 P0-B: Sage create-issues / record-lock / verify-project

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

@test "SAGE-CREATE-ISSUES: project-info missing -> exit 1 with actionable msg" {
    mkdir -p .louke/project/specs/v0.6-008-test
    printf '<a id="fr-0001"></a>\n### FR-0001 demo\n' > .louke/project/specs/v0.6-008-test/spec.md
    run $PY sage create-issues --spec v0.6-008-test
    [ "$status" -ne 0 ]
    [[ "$output" == *"Repo field missing"* ]]
}

@test "SAGE-CREATE-ISSUES: project-info missing Release Branch -> exit 1 with actionable msg" {
    mkdir -p .louke/project/specs/v0.6-008-test
    printf '<a id="fr-0001"></a>\n### FR-0001 demo\n' > .louke/project/specs/v0.6-008-test/spec.md
    cat > .louke/project/project-info.md <<'EOF'
# Project Info

- **Version**: v0.6
- **Repo**: github.com/foo/bar
- **Project**: bar-v0.6
- **Project ID**: https://github.com/users/foo/projects/1
- **Spec ID**: v0.6-008-test
- **Smoke Test Issue**: #1 (closed)
- **Smoke Test PR**: #2 (closed)
- **DoD**: d
- **Security Audit**: disabled
- **Current Stage**: M-FOUND
- **Backlog Project**: https://github.com/users/foo/projects/2
- **Created**: 2026-06-30
EOF
    run $PY sage create-issues --spec v0.6-008-test
    [ "$status" -ne 0 ]
    [[ "$output" == *"Release Branch field missing"* ]]
}

@test "SAGE-CREATE-ISSUES: 0 FR anchors -> exit 0 with '0 created, 0 skipped'" {
    mkdir -p .louke/project/specs/v0.6-008-test
    printf 'no anchors\n' > .louke/project/specs/v0.6-008-test/spec.md
    cat > .louke/project/project-info.md <<'EOF'
- **Repo**: github.com/foo/bar
- **Release Branch**: `releases/v0.6`
- **Project ID**: https://github.com/users/foo/projects/1
EOF
    run $PY sage create-issues --spec v0.6-008-test
    [ "$status" -eq 0 ]
    [[ "$output" == *"0 created, 0 skipped"* ]]
}

@test "SAGE-RECORD-LOCK: missing --confirm -> User signal error" {
    run $PY sage record-lock --spec v0.6-008-test
    [ "$status" -ne 0 ]
    [[ "$output" == *"User signal"* ]]
}

@test "LEX-VERIFY-PROJECT: project-info missing -> exit 1 with actionable msg" {
    run $PY lex verify-project --spec v0.6-008-test
    [ "$status" -ne 0 ]
    [[ "$output" == *"Project URL missing"* ]] || [[ "$output" == *"scout foundation"* ]]
}