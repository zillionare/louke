#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
DEVON_PY="$REPO_ROOT/louke/devon.py"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

setup() {
    TEST_REPO="$(mktemp -d)"
}

teardown() {
    cd "$REPO_ROOT" || true
    rm -rf "$TEST_REPO"
}

init_tmp_repo() {
    cd "$TEST_REPO" || exit 1
    git init -q
    git config user.email "devon@example.com"
    git config user.name "Devon"
    echo init > file.txt
    git add file.txt
    git commit -q -m "chore: init"
}

@test "FR-0400 AC-3: --phase red exits non-zero with deprecation message" {
    init_tmp_repo
    echo change > file.txt
    git add file.txt
    run python -m louke agent devon commit-rgr \
        --phase red --issue 42 --message "dummy"
    [ "$status" -ne 0 ]
    [[ "$output" == *"--phase red 已废弃 (v0.7-001)"* ]] || {
        echo "stderr/output: $output" >&2
        false
    }
}

@test "FR-0400 AC-4: --phase green feature produces feat: green + Closes" {
    init_tmp_repo
    echo change > file.txt
    git add file.txt
    python -m louke agent devon commit-rgr \
        --phase green --issue 42 --message "FR-0400 test" --label feature
    msg="$(git log -1 --pretty=%B)"
    [[ "$msg" == "feat: green"* ]] || { echo "msg=$msg" >&2; false; }
    [[ "$msg" == *"Closes #42"* ]] || { echo "msg=$msg" >&2; false; }
}

@test "FR-0400 AC-4: --phase green fix produces fix: green + Closes" {
    init_tmp_repo
    echo change > file.txt
    git add file.txt
    python -m louke agent devon commit-rgr \
        --phase green --issue 85 --message "FR-0500 test" --label fix
    msg="$(git log -1 --pretty=%B)"
    [[ "$msg" == "fix: green"* ]] || { echo "msg=$msg" >&2; false; }
    [[ "$msg" == *"Closes #85"* ]] || { echo "msg=$msg" >&2; false; }
}

@test "FR-0400 AC-5: --phase refactor produces refactor: prefix without Closes" {
    init_tmp_repo
    echo change > file.txt
    git add file.txt
    python -m louke agent devon commit-rgr \
        --phase refactor --issue 86 --message "FR-0600 cleanup" --label feature
    msg="$(git log -1 --pretty=%B)"
    [[ "$msg" == "refactor:"* ]] || { echo "msg=$msg" >&2; false; }
    [[ "$msg" != *"Closes"* ]] || { echo "msg=$msg" >&2; false; }
}

@test "FR-0400 AC-6: RGR_PREFIX no longer contains red tuple keys" {
    run grep -Eq "\('feature',\s*'red'\)|\('fix',\s*'red'\)" "$DEVON_PY"
    [ "$status" -ne 0 ]
}
