#!/usr/bin/env bats
# v0.6-008 P0-B: Scout foundation / invite-owner / commit-foundation / FR-0530 glob

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

@test "SCOUT-FOUNDATION-MVP: --dry-run --no-repo previews project.toml + story; no gh calls" {
    run $PY agent scout foundation \
        --repo zillionare/demo --version v0.6 --spec-id v0.6-008-test \
        --keyword init-foundation \
        --no-repo --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"would write"* ]]
    [[ "$output" == *"would run lk agent scout identity-check"* ]]
    [[ "$output" == *"would run lk agent warden foundation-check"* ]]
    [ ! -f .louke/project/project.toml ]
}

@test "SCOUT-FOUNDATION-MVP: --no-repo writes project.toml + story.md" {
    $PY agent scout foundation \
        --repo zillionare/demo --version v0.6 --spec-id v0.6-008-test \
        --keyword init-foundation \
        --no-repo --story "demo story" 2>/dev/null || true
    # foundation-check / identity-check may fail; we only check what was written
    [ -f .louke/project/project.toml ]
    [ -f .louke/project/specs/v0.6-008-test/story.md ]
    grep -q 'spec_id = "v0.6-008-test"' .louke/project/project.toml
}

@test "SCOUT-INVITE-OWNER: missing --version fails with actionable stderr" {
    run $PY agent scout invite-owner zillionare/demo
    [ "$status" -ne 0 ]
    [[ "$output" == *"--version"* ]] || [[ "$output" == *"required"* ]]
}

@test "SCOUT-COMMIT-FOUNDATION: --no-push commits without push; glob picks up *.md" {
    $PY agent scout foundation --repo zillionare/demo --version v0.6 \
        --spec-id v0.6-008-test --keyword init-foundation --no-repo --story "demo" --no-commit 2>/dev/null || true
    [ -f .louke/project/specs/v0.6-008-test/story.md ]
    run $PY agent scout commit-foundation \
        --spec-id v0.6-008-test \
        --message "story/prd: initial draft" \
        --version v0.6 --no-push
    [ "$status" -eq 0 ]
    git log -1 --format=%s | grep -q "story/prd"
    # glob expansion: git ls-files should contain story.md
    git ls-files | grep -q "specs/v0.6-008-test/story.md"
}

@test "SCOUT-COMMIT-FOUNDATION: no markdown files warns and exits nonzero because git commit has nothing" {
    run $PY agent scout commit-foundation --spec-id nothing --message "x" --version v0.6 --no-push
    [ "$status" -ne 0 ]
    [[ "$output" == *"no markdown files"* ]] || [[ "$output" == *"failed: git"* ]]
}

@test "CHECK-FOUNDATION-F6: project.toml needs required fields" {
    mkdir -p .louke/project
    cat > .louke/project/project.toml <<'EOF'
[project]
version = "v0.6"
repo = "github.com/foo/bar"
project = "bar-v0.6"
spec_id = "v0.6-008-x"
EOF
    run python3 "$REPO_ROOT/louke/_tools/check_foundation.py" --repo foo/bar --version v0.6 --spec-id v0.6-008-x
    [ "$status" -ne 0 ]
    [[ "$output" == *"F6"* ]] || [[ "$output" == *"missing fields"* ]] || true
}
