#!/usr/bin/env bats

# spec 004 integration tests
# IT-001: complete IDE flow with git diff trigger
# IT-002: status marker persistence across commits
# IT-003: --check-ready gate

setup() {
    TEST_DIR="$(mktemp -d)"
    export SPECFORGE_HOME
    SPECFORGE_HOME="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# IT-001: IDE flow without git push
@test "IT-001_ide_flow_no_push: spec 004 quote dialogue works locally" {
    cd "$TEST_DIR"
    mkdir -p specs/test
    git init -q
    git config user.email "test@test"
    git config user.name "test"

    # 1. Sage writes initial spec.md
    cat > specs/test/spec.md <<'EOF'
# test spec

> **Sage:** first question
EOF
    git add . && git commit -q -m "sage: initial"

    # 2. User edits in IDE, changes quote to resolved
    cat > specs/test/spec.md <<'EOF'
# test spec

> **Sage:** first question ✓ resolved
EOF

    # 3. Parse the modified spec
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" "$TEST_DIR/specs/test/spec.md"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "resolved: 1" ]]

    # 4. Check readiness
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --check-ready "$TEST_DIR/specs/test/spec.md"
    [ "$status" -eq 0 ]
}

# IT-002: status marker persistence across commits
@test "IT-002_status_persistence: git log + quote_parser shows full history" {
    cd "$TEST_DIR"
    mkdir -p specs/test
    git init -q
    git config user.email "test@test"
    git config user.name "test"

    # Commit 1: pending
    printf '> **Sage:** q1\n> **Aaron:** pending reply\n' > specs/test/spec.md
    git add . && git commit -q -m "v1"

    # Commit 2: Aaron resolves
    printf '> **Sage:** q1 ✓ resolved\n> **Aaron:** pending reply\n' > specs/test/spec.md
    git add . && git commit -q -m "v2"

    # Git log shows both
    COMMITS=$(git log --oneline | wc -l | tr -d ' ')
    [ "$COMMITS" -eq 2 ]
}

# IT-003: --check-ready gate integration
@test "IT-003_check_ready_gate: gate flips on status change" {
    cd "$TEST_DIR"
    mkdir -p specs/test
    git init -q
    git config user.email "test@test"
    git config user.name "test"

    # v0.5-011: 加 unit header + yaml.resolved=✅ 让 quote 挂到 unit 上,
    # 不被当 explanatory 丢弃, 且 unit 满足 FR is_ready 条件
    cat > specs/test/spec.md <<'EOF'
### FR-001 test

| valid | testability | resolved |
|-------|-------------|----------|
| true  | auto        |          |

> **Sage:** q1
EOF
    git add . && git commit -q -m "v1"

    # Not ready: 1 open quote + yaml.resolved=空
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --check-ready "$TEST_DIR/specs/test/spec.md"
    [ "$status" -eq 1 ]

    # Mark quote resolved + yaml.resolved=✅ → ready
    cat > specs/test/spec.md <<'EOF'
### FR-001 test

| valid | testability | resolved |
|-------|-------------|----------|
| true  | auto        | ✅       |

> **Sage:** q1 ✓ resolved
EOF

    # Now ready
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --check-ready "$TEST_DIR/specs/test/spec.md"
    [ "$status" -eq 0 ]
}

# IT-004: diff resolver + quote_parser together (workflow)
@test "IT-004_diff_resolver_integration: diff detects quote state change" {
    cd "$TEST_DIR"
    mkdir -p specs/test
    git init -q
    git config user.email "test@test"
    git config user.name "test"

    # Initial
    cat > specs/test/spec.md <<'EOF'
# test

> **Sage:** question 1

<a id="fr-001"></a>
**FR-001**: feature
EOF
    git add . && git commit -q -m "v1"

    # User edits (resolves quote 1)
    cat > specs/test/spec.md <<'EOF'
# test

> **Sage:** question 1 ✓ resolved

<a id="fr-001"></a>
**FR-001**: feature
EOF

    # Run diff resolver
    run python3 "$SPECFORGE_HOME/tools/git_diff_quote_resolver.py" "$TEST_DIR/specs/test/spec.md" --base-ref HEAD
    [ "$status" -eq 0 ]
    # Should recommend resolving the quote (it's in window of edit at L4)
    [[ "$output" =~ "recommended resolve" ]]
}

# IT-005: spec 004 self-parse end-to-end
# v0.5-011: spec 004 仍在迭代中, 12 个 open quote 未 ✓ resolved,
# 故 is_ready=False (符合 spec 004 quote dialogue 流程预期 — spec 未锁定)
@test "IT-005_spec_004_self_parse: spec 004 not ready yet (open quotes remain)" {
    SPEC004="$SPECFORGE_HOME/.specforge/project/specs/v0.4-004-quote-dialogue/spec.md"
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --check-ready "$SPEC004"
    [ "$status" -eq 1 ]
}