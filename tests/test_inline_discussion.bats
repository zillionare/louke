#!/usr/bin/env bats
# FR-0080: tests for inline-discussion protocol (v0.7-003)

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
PY="python3 -m louke"

setup() {
    WORK="$BATS_TEST_TMPDIR/proj"
    mkdir -p "$WORK"
    cd "$WORK"
    mkdir -p .louke/project/specs/test
    cat > .louke/project/specs/test/spec.md <<'EOF'
# Test Spec

### FR-0001 用户登录

> **Sage**: 密码加密用 bcrypt 还是 argon2?
>> **Aaron**: 用 argon2.

### FR-0002 密码重置

> **Sage**: 邮件还是短信验证?
EOF
}

@test "query: returns threads as JSON with 5-tuple" {
    run $PY discuss query --file .louke/project/specs/test/spec.md
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '"thread_id"'
    echo "$output" | grep -q '"initiator": "sage"'
    echo "$output" | grep -q '"reply_count": 1'
    echo "$output" | grep -q '"anchor_line"'
    echo "$output" | grep -q '"root_text"'
}

@test "query: --initiator filter" {
    run $PY discuss query --file .louke/project/specs/test/spec.md --initiator Sage
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '"initiator": "sage"'
    ! echo "$output" | grep -q '"initiator": "aaron"'
}

@test "query: --status filter" {
    run $PY discuss query --file .louke/project/specs/test/spec.md --status open
    [ "$status" -eq 0 ]
    echo "$output" | grep -q '"status": "open"'
    ! echo "$output" | grep -q '"status": "resolved"'
}

@test "query: --blocker returns 3 categories and reopened blockers" {
    # Fixture with 5 threads covering all 3 blocker categories + a reopened
    # blocker + 1 non-match:
    #   T-001: Sage initiated, no replies, open          → unanswered (Sage is blocker)
    #   T-002: Sage initiated, Aaron replied, open       → unresolved (Sage is blocker)
    #   T-003: Aaron initiated, @Sage mentioned, open    → awaiting_my_reply (Sage is blocker)
    #   T-004: Sage initiated, replied, reopen          → unresolved (Sage is blocker)
    #   T-005: Aaron initiated, no mentions, open      → should NOT appear for --blocker Sage
    cat > .louke/project/specs/test/blocker_spec.md <<'EOF'
# Blocker Test Spec

### FR-0001 unanswered

> **Sage**: should use bcrypt or argon2?

### FR-0002 unresolved

> **Sage**: email or SMS for 2FA?
>> **Aaron**: email is simpler.

### FR-0003 awaiting

> **Aaron**: @Sage what about rate limiting?

### FR-0004 reopened

> **Sage** [REOPEN]: still needs a decision.
>> **Aaron**: the earlier answer is no longer sufficient.

### FR-0005 not-for-sage

> **Aaron**: lex should review this.
EOF
    run $PY discuss query --file .louke/project/specs/test/blocker_spec.md --blocker Sage
    [ "$status" -eq 0 ]
    # Should return 4 threads: T-001 (unanswered), T-002/T-004 (unresolved),
    # T-003 (awaiting), including the reopened T-004.
    COUNT=$(echo "$output" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
    [ "$COUNT" -eq 4 ]
    # T-001: unanswered (Sage initiated, 0 replies)
    echo "$output" | grep -q '"initiator": "sage"'
    # T-002: unresolved (Sage initiated, 1 reply)
    echo "$output" | python3 -c "
import sys, json
threads = json.load(sys.stdin)
sage_threads = [t for t in threads if t['initiator'] == 'sage']
assert any(t['reply_count'] == 0 for t in sage_threads), 'missing unanswered'
assert any(t['reply_count'] > 0 for t in sage_threads), 'missing unresolved'
"
    # T-003: awaiting (Aaron initiated, @Sage mentioned)
    echo "$output" | python3 -c "
import sys, json
threads = json.load(sys.stdin)
awaiting = [t for t in threads if 'sage' in t.get('mentioned_agents', [])]
assert len(awaiting) >= 1, 'missing awaiting_my_reply'
"
    # T-005: should NOT appear (Aaron initiated, no mention of Sage)
    ! echo "$output" | grep -q 'not-for-sage'
}

@test "query: --check-ready returns is_ready + blockers" {
    run $PY discuss query --file .louke/project/specs/test/spec.md --check-ready
    [ "$status" -eq 1 ]
    echo "$output" | grep -q '"is_ready": false'
    echo "$output" | grep -q '"ready_blockers"'
}

@test "set-status: RESOLVED by initiator succeeds" {
    run $PY discuss set-status --file .louke/project/specs/test/spec.md \
        --thread-id T-001 --anchor-line 3 --anchor-text "### FR-0001 用户登录" \
        --root-line 5 --root-text "Sage: 密码加密用 bcrypt 还是 argon2?" \
        --status resolved --operator Sage
    [ "$status" -eq 0 ]
    run $PY discuss query --file .louke/project/specs/test/spec.md --status resolved
    echo "$output" | grep -q '"status": "resolved"'
}

@test "set-status: RESOLVED by non-initiator fails" {
    run $PY discuss set-status --file .louke/project/specs/test/spec.md \
        --thread-id T-001 --anchor-line 3 --anchor-text "### FR-0001 用户登录" \
        --root-line 5 --root-text "Sage: 密码加密用 bcrypt 还是 argon2?" \
        --status resolved --operator Aaron
    [ "$status" -ne 0 ]
    [[ "$output" == *"only initiator"* ]]
}

@test "set-status: REOPEN by anyone succeeds" {
    # First resolve by initiator
    $PY discuss set-status --file .louke/project/specs/test/spec.md \
        --thread-id T-001 --anchor-line 3 --anchor-text "### FR-0001 用户登录" \
        --root-line 5 --root-text "Sage: 密码加密用 bcrypt 还是 argon2?" \
        --status resolved --operator Sage
    # Then reopen by non-initiator
    run $PY discuss set-status --file .louke/project/specs/test/spec.md \
        --thread-id T-001 --anchor-line 3 --anchor-text "### FR-0001 用户登录" \
        --root-line 5 --root-text "Sage: 密码加密用 bcrypt 还是 argon2?" \
        --status reopen --operator Aaron
    [ "$status" -eq 0 ]
    run $PY discuss query --file .louke/project/specs/test/spec.md --status reopen
    echo "$output" | grep -q '"status": "reopen"'
}

@test "start: creates new thread" {
    run $PY discuss start --file .louke/project/specs/test/spec.md \
        --anchor-line 3 --speaker Lex "需要考虑 rate limiting"
    [ "$status" -eq 0 ]
    [[ "$output" == *"created"* ]]
    run $PY discuss query --file .louke/project/specs/test/spec.md --initiator Lex
    echo "$output" | grep -q '"initiator": "lex"'
}

@test "reply: adds reply to existing thread" {
    run $PY discuss reply --file .louke/project/specs/test/spec.md \
        --thread-id T-002 --anchor-line 8 --anchor-text "### FR-0002 密码重置" \
        --root-line 10 --root-text "Sage: 邮件还是短信验证?" \
        --speaker Aaron "邮件 + 短信双因子"
    [ "$status" -eq 0 ]
    [[ "$output" == *"reply added"* ]]
    run $PY discuss query --file .louke/project/specs/test/spec.md --initiator Sage
    echo "$output" | grep -q '"reply_count": 1'
}

@test "edit: changes comment body (only original author)" {
    run $PY discuss edit --file .louke/project/specs/test/spec.md \
        --thread-id T-001 --anchor-line 3 --anchor-text "### FR-0001 用户登录" \
        --root-line 5 --root-text "Sage: 密码加密用 bcrypt 还是 argon2?" \
        --depth 1 --speaker Sage "密码加密用 argon2 还是 scrypt?"
    [ "$status" -eq 0 ]
    [[ "$output" == *"edited"* ]]
    run $PY discuss query --file .louke/project/specs/test/spec.md
    echo "$output" | grep -q "scrypt"
}

@test "Level 0: find_thread with exact 5-tuple" {
    # set-status uses find_thread internally; exact anchor + root should succeed
    run $PY discuss set-status --file .louke/project/specs/test/spec.md \
        --thread-id T-001 --anchor-line 3 --anchor-text "### FR-0001 用户登录" \
        --root-line 5 --root-text "Sage: 密码加密用 bcrypt 还是 argon2?" \
        --status resolved --operator Sage
    [ "$status" -eq 0 ]
}

@test "Level 2: find_thread with wrong anchor_line but correct root_text" {
    # Pass wrong anchor_line but correct root_text; Level 2 should still find it
    run $PY discuss set-status --file .louke/project/specs/test/spec.md \
        --thread-id T-001 --anchor-line 999 --anchor-text "nonexistent" \
        --root-line 5 --root-text "Sage: 密码加密用 bcrypt 还是 argon2?" \
        --status resolved --operator Sage
    [ "$status" -eq 0 ]
}

@test "Level 3: not found returns error" {
    run $PY discuss set-status --file .louke/project/specs/test/spec.md \
        --thread-id T-999 --anchor-line 999 --anchor-text "nonexistent" \
        --root-line 999 --root-text "nonexistent" \
        --status resolved --operator Sage
    [ "$status" -ne 0 ]
    [[ "$output" == *"not found"* ]]
}

@test "query: nonexistent file returns error" {
    run $PY discuss query --file /nonexistent/path/spec.md
    [ "$status" -ne 0 ]
}
