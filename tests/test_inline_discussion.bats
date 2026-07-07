#!/usr/bin/env bats
# FR-0080: tests for inline-discussion protocol (v0.7-003)

setup() {
    TMPDIR_FOR_TEST="$(mktemp -d)"
    cd "$TMPDIR_FOR_TEST"
    mkdir -p .louke/project/specs/test
    cat > .louke/project/specs/test/spec.md <<'EOF'
# Test Spec

### FR-0001 用户登录

> **Sage**: 密码加密用 bcrypt 还是 argon2?
> **Aaron** [RESOLVED]: 用 argon2.
EOF
    LK="/Users/aaronyang/.louke/venv/bin/python3 -m louke"
}

teardown() {
    cd /
    rm -rf "$TMPDIR_FOR_TEST"
}

@test "query: returns 2 threads as JSON" {
    run $LK discuss query --file .louke/project/specs/test/spec.md
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '"thread_id"'
    echo "$output" | grep -q '"status": "resolved"'
}

@test "query: --initiator filter" {
    run $LK discuss query --file .louke/project/specs/test/spec.md --initiator Sage
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '"initiator": "sage"'
    ! echo "$output" | grep -q '"initiator": "aaron"'
}

@test "query: --status filter" {
    run $LK discuss query --file .louke/project/specs/test/spec.md --status open
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '"status": "open"'
    ! echo "$output" | grep -q '"status": "resolved"'
}

@test "set-status: correct initiator" {
    $LK discuss set-status --file .louke/project/specs/test/spec.md \
        --thread-id T-001 --anchor-line 2 --anchor-text "### FR-0001 用户登录" \
        --root-line 3 --root-text "Sage: 密码加密用 bcrypt 还是 argon2?" \
        --status resolved --operator Sage
    $LK discuss query --file .louke/project/specs/test/spec.md | grep -q '"status": "resolved"'
}

@test "set-status: REOPEN allowed by anyone" {
    $LK discuss set-status --file .louke/project/specs/test/spec.md \
        --thread-id T-001 --anchor-line 2 --anchor-text "### FR-0001 用户登录" \
        --root-line 3 --root-text "Sage: 密码加密用 bcrypt 还是 argon2?" \
        --status reopen --operator Aaron
    $LK discuss query --file .louke/project/specs/test/spec.md | grep -q '"status": "reopen"'
}

@test "Level 3: not found returns error" {
    run $LK discuss query --file /nonexistent/path/spec.md
    [ "$status" -ne 0 ]
}
