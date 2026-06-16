#!/usr/bin/env bats
#
# verify_acceptance.py tests (FR-080 acceptance tracking table)
# Lex stage-1 structural check: validates Sage's acceptance.md is qualified

setup() {
    TEST_DIR="$(mktemp -d)"
    export TEST_DIR
    export SPECFORGE_HOME
    SPECFORGE_HOME="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
}

teardown() {
    [ -n "$TEST_DIR" ] && rm -rf "$TEST_DIR"
}

# --- L1: file exists ---

@test "VA-T01-missing-acceptance: acceptance.md missing -> L1 reject" {
    cat > "$TEST_DIR/spec.md" <<'SPEC_EOF'
# Demo

## FR-010 draw circle
SPEC_EOF

    run python3 "$SPECFORGE_HOME/tools/verify_acceptance.py" --offline \
        --spec-file "$TEST_DIR/spec.md" \
        --acceptance-file "$TEST_DIR/acceptance.md"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "L1" ]]
    [[ "$output" =~ "拒绝" ]]
}

# --- L2: FR/NFR sections present ---

@test "VA-T02-missing-fr-section: spec has FR-020 but acceptance omits -> L2 reject" {
    cat > "$TEST_DIR/spec.md" <<'SPEC_EOF'
# Demo

## FR-010 draw circle
## FR-020 draw square
SPEC_EOF
    cat > "$TEST_DIR/acceptance.md" <<'ACC_EOF'
# Demo

## FR-010 draw circle

### AC-1
- center (0,0)
ACC_EOF

    run python3 "$SPECFORGE_HOME/tools/verify_acceptance.py" --offline \
        --spec-file "$TEST_DIR/spec.md" \
        --acceptance-file "$TEST_DIR/acceptance.md"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "L2" ]]
    [[ "$output" =~ "缺少" ]]
    [[ "$output" =~ "FR-020" ]]
}

# --- L3: AC numbering sequential ---

@test "VA-T03-ac-not-sequential: AC skips a number -> L3 reject" {
    cat > "$TEST_DIR/spec.md" <<'SPEC_EOF'
# Demo

## FR-010 draw circle
SPEC_EOF
    cat > "$TEST_DIR/acceptance.md" <<'ACC_EOF'
# Demo

## FR-010 draw circle

### AC-1
- condition one

### AC-3
- condition three (skips AC-2)
ACC_EOF

    run python3 "$SPECFORGE_HOME/tools/verify_acceptance.py" --offline \
        --spec-file "$TEST_DIR/spec.md" \
        --acceptance-file "$TEST_DIR/acceptance.md"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "L3" ]]
    [[ "$output" =~ "连续" ]]
}

# --- L4: AC content non-empty, no placeholders ---

@test "VA-T04-placeholder: AC contains {placeholder} -> L4 reject" {
    cat > "$TEST_DIR/spec.md" <<'SPEC_EOF'
# Demo

## FR-010 draw circle
SPEC_EOF
    cat > "$TEST_DIR/acceptance.md" <<'ACC_EOF'
# Demo

## FR-010 draw circle

### AC-1
- {placeholder}
ACC_EOF

    run python3 "$SPECFORGE_HOME/tools/verify_acceptance.py" --offline \
        --spec-file "$TEST_DIR/spec.md" \
        --acceptance-file "$TEST_DIR/acceptance.md"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "L4" ]]
    [[ "$output" =~ "占位符" ]]
}

@test "VA-T05-empty-ac: AC node has no bullets -> L4 reject" {
    cat > "$TEST_DIR/spec.md" <<'SPEC_EOF'
# Demo

## FR-010 draw circle
SPEC_EOF
    cat > "$TEST_DIR/acceptance.md" <<'ACC_EOF'
# Demo

## FR-010 draw circle

### AC-1

### AC-2
- real content
ACC_EOF

    run python3 "$SPECFORGE_HOME/tools/verify_acceptance.py" --offline \
        --spec-file "$TEST_DIR/spec.md" \
        --acceptance-file "$TEST_DIR/acceptance.md"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "L4" ]]
    [[ "$output" =~ "AC-1" ]]
    [[ "$output" =~ "缺少项目符号内容" ]]
}

# --- L5: reverse coverage (ghost FR) ---

@test "VA-T06-ghost-fr: acceptance references FR-999 not in spec -> L5 reject" {
    cat > "$TEST_DIR/spec.md" <<'SPEC_EOF'
# Demo

## FR-010 draw circle
SPEC_EOF
    cat > "$TEST_DIR/acceptance.md" <<'ACC_EOF'
# Demo

## FR-010 draw circle

### AC-1
- center (0,0)

## FR-999 ghost

### AC-1
- should not exist
ACC_EOF

    run python3 "$SPECFORGE_HOME/tools/verify_acceptance.py" --offline \
        --spec-file "$TEST_DIR/spec.md" \
        --acceptance-file "$TEST_DIR/acceptance.md"
    [ "$status" -ne 0 ]
    [[ "$output" =~ "L5" ]]
    [[ "$output" =~ "FR-999" ]]
}

# --- Happy path: all pass ---

@test "VA-T07-full-compliant: complete acceptance -> all 5 pass exit 0" {
    cat > "$TEST_DIR/spec.md" <<'SPEC_EOF'
# Demo

## FR-010 draw circle
## FR-020 draw square
## NFR-010 performance
SPEC_EOF
    cat > "$TEST_DIR/acceptance.md" <<'ACC_EOF'
# Demo

## FR-010 draw circle

### AC-1
- center (0,0), radius 0.5m
- after one call, object count +1

### AC-2
- radius 0 raises ValueError
- negative radius raises ValueError

## FR-020 draw square

### AC-1
- side 1m, square border visible

## NFR-010 performance

### AC-1
- 1000 calls under 100ms
ACC_EOF

    run python3 "$SPECFORGE_HOME/tools/verify_acceptance.py" --offline \
        --spec-file "$TEST_DIR/spec.md" \
        --acceptance-file "$TEST_DIR/acceptance.md"
    [ "$status" -eq 0 ]
    [[ "$output" =~ "L1 \[通过\]" ]]
    [[ "$output" =~ "L2 \[通过\]" ]]
    [[ "$output" =~ "L3 \[通过\]" ]]
    [[ "$output" =~ "L4 \[通过\]" ]]
    [[ "$output" =~ "L5 \[通过\]" ]]
    [[ "$output" =~ "5 项校验全部通过" ]]
}
