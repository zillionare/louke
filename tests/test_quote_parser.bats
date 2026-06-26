#!/usr/bin/env bats

# quote_parser.py 测试 (spec 004-quote-dialogue)
# 覆盖 FR-017/018/025/026

setup() {
    TEST_DIR="$(mktemp -d)"
    export SPECFORGE_HOME
    SPECFORGE_HOME="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    FIXTURE="$SPECFORGE_HOME/tests/fixtures/spec-with-quotes.md"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "QP_T01_basic_parse: parses 12 quotes from fixture" {
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "total quotes: 12" ]]
}

@test "QP_T02_open_count: counts 6 [open] quotes" {
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "open: 6" ]]
}

@test "QP_T03_resolved_count: counts 3 resolved quotes" {
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "resolved: 3" ]]
}

@test "QP_T04_is_ready_false: 6 open means not ready" {
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "is_ready: False" ]]
}

@test "QP_T05_check_ready_exit_1: --check-ready exits 1 when not ready" {
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --check-ready "$FIXTURE"
    [ "$status" -eq 1 ]
}

@test "QP_T06_nested_depth_3: detects depth 3 quote" {
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --format json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"3":' ]]
}

@test "QP_T07_nested_depth_4: detects depth 4 quote (FR-024)" {
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --format json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"4":' ]]
}

@test "QP_T08_code_fence_excluded: code block > not parsed as quote" {
    # Fixture has code block containing "> **Sage:** ... [open]"
    # If parser included it, total would be 13 instead of 12
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "total quotes: 12" ]]
}

@test "QP_T09_blocked_by_FR: detects [blocked-by-001]" {
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --format json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"blocked_by": 1' ]]
}

@test "QP_T10_check_ready_exit_0: spec_with_0_open_exit_0" {
    EMPTY_SPEC="$TEST_DIR/empty.md"
    cat > "$EMPTY_SPEC" <<'EOF'
# empty spec

> **Sage:** resolved ✓ resolved
EOF
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --check-ready "$EMPTY_SPEC"
    [ "$status" -eq 0 ]
}

@test "QP_T11_speaker_counts: counts speakers correctly" {
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --format json "$FIXTURE"
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"Sage"' ]]
    [[ "$output" =~ '"Aaron"' ]]
    [[ "$output" =~ '"Lex"' ]]
}

@test "QP_T12_json_format: --format json produces valid JSON" {
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --format json "$FIXTURE"
    [ "$status" -eq 0 ]
    echo "$output" | python3 -c "import sys, json; json.load(sys.stdin)"
}

@test "QP_T13_nonexistent_spec: exits 2 on missing file" {
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" "$TEST_DIR/does-not-exist.md"
    [ "$status" -eq 2 ]
}

@test "QP_T14_no_quotes_at_all: empty file is_ready=True" {
    EMPTY_SPEC="$TEST_DIR/no-quotes.md"
    : > "$EMPTY_SPEC"
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --check-ready "$EMPTY_SPEC"
    [ "$status" -eq 0 ]
}

@test "QP_T15_list_marker_excluded: list dash markers not parsed as quote" {
    # Fixture has list markers like "- 项目 A" — none should be quotes
    # All 12 quotes in fixture are depth >= 1, not 0
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --format json "$FIXTURE"
    [ "$status" -eq 0 ]
    # No quote should have depth 0 (would mean false-positive on list markers)
    [[ ! "$output" =~ '"depth": 0' ]]
}

@test "QP_T16_self_parse_spec004: spec 004 self-parses with status markers" {
    # This is the dogfood check: spec 004 must follow its own format
    # so quote_parser.py can detect its open quotes correctly.
    SPEC004="$SPECFORGE_HOME/.specforge/project/specs/v0.4-004-quote-dialogue/spec.md"
    [ -f "$SPEC004" ]
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" "$SPEC004"
    [ "$status" -eq 0 ]
    # All Sage quotes must end with status marker (parser only counts those)
    [[ ! "$output" =~ "total quotes: 0" ]]
}

@test "QP_T17_no_status_means_open: quote without status marker = pending (Aaron's design)" {
    # Per FR-017 update from Aaron: "[open] marker is unnecessary,
    # absence of ✓ resolved = pending". This is the default state.
    TEST_SPEC="$TEST_DIR/no-status.md"
    cat > "$TEST_SPEC" <<'EOF'
# test

### FR-001 some requirement

> **Sage:** a question without explicit status

> **Aaron:** reply without status
EOF
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" "$TEST_SPEC"
    [ "$status" -eq 0 ]
    # Both should be detected as open (pending) and kept (not explanatory)
    # because they belong to a unit
    [[ "$output" =~ "total quotes: 2" ]]
    [[ "$output" =~ "open: 2" ]]
    [[ "$output" =~ "resolved: 0" ]]
    [[ "$output" =~ "is_ready: False" ]]
}

@test "QP_T18_explicit_resolved_overrides: checkmark_resolved_still_works" {
    # Backward compat: explicit ✓ resolved still marks as resolved
    TEST_SPEC="$TEST_DIR/mixed-status.md"
    cat > "$TEST_SPEC" <<'EOF'
# test

> **Sage:** resolved explicitly ✓ resolved

> **Sage:** no status (default pending)
EOF
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" "$TEST_SPEC"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "total quotes: 2" ]]
    [[ "$output" =~ "open: 1" ]]
    [[ "$output" =~ "resolved: 1" ]]
}

@test "QP_T19_owner_role_detection: agent names get role=agent" {
    TEST_SPEC="$TEST_DIR/agent-quote.md"
    cat > "$TEST_SPEC" <<'EOF'
### FR-001 test

> **Sage:** my question
EOF
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --format json "$TEST_SPEC"
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"owner_close_role": "agent"' ]]
}

@test "QP_T20_owner_role_detection_user: non-agent names get role=user" {
    TEST_SPEC="$TEST_DIR/user-quote.md"
    cat > "$TEST_SPEC" <<'EOF'
### FR-001 test

> **Aaron:** my question
EOF
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --format json "$TEST_SPEC"
    [ "$status" -eq 0 ]
    [[ "$output" =~ '"owner_close_role": "user"' ]]
}

@test "QP_T21_check_violations_clean: no violations when roles match" {
    TEST_SPEC="$TEST_DIR/clean.md"
    cat > "$TEST_SPEC" <<'EOF'
> **Sage:** my own question ✓ resolved
> **Aaron:** user note
EOF
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --check-violations "$TEST_SPEC"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "no ownership violations" ]]
}

@test "QP_T22_check_violations_user_closed: user_quote_closed_by_anyone_is_violation" {
    TEST_SPEC="$TEST_DIR/violation.md"
    cat > "$TEST_SPEC" <<'EOF'
> **Aaron:** user note ✓ resolved
EOF
    run python3 "$SPECFORGE_HOME/tools/quote_parser.py" --check-violations "$TEST_SPEC"
    [ "$status" -eq 1 ]
    [[ "$output" =~ "OWNERSHIP VIOLATIONS" ]]
}