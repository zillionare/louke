#!/usr/bin/env bats
# L1-L5 acceptance.md structural validation tests (verify_acceptance.py)

REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"
PY="python3 -m louke"

setup() {
    WORK="$BATS_TEST_TMPDIR/proj"
    mkdir -p "$WORK/.louke/project/specs/test"
    cd "$WORK"
    cat > .louke/project/specs/test/spec.md <<'EOF'
# Test Spec

### FR-0001 User Login

Requirement content.
EOF
    SPEC_FILE=".louke/project/specs/test/spec.md"
    ACC_FILE=".louke/project/specs/test/acceptance.md"
}

@test "L1 fail: acceptance.md missing" {
    run $PY agent lex verify-acceptance --spec test --spec-file "$SPEC_FILE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"acceptance.md missing"* ]]
}

@test "L1 fail: acceptance.md empty" {
    printf '' > "$ACC_FILE"
    run $PY agent lex verify-acceptance --spec test --spec-file "$SPEC_FILE" --acceptance-file "$ACC_FILE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"is empty"* ]]
}

@test "L2 fail: spec FR missing in acceptance" {
    cat > "$ACC_FILE" <<'EOF'
# Acceptance

## NFR-0010 performance

### AC-1
- response < 200ms
EOF
    run $PY agent lex verify-acceptance --spec test --spec-file "$SPEC_FILE" --acceptance-file "$ACC_FILE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"missing"* ]]
}

@test "L3 fail: AC numbering not sequential" {
    cat > "$ACC_FILE" <<'EOF'
# Acceptance

## FR-0001

### AC-1
- valid bullet

### AC-3
- valid bullet
EOF
    run $PY agent lex verify-acceptance --spec test --spec-file "$SPEC_FILE" --acceptance-file "$ACC_FILE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"not sequential"* ]] || [[ "$output" == *"AC numbering"* ]]
}

@test "L4 fail: AC has no bullets" {
    cat > "$ACC_FILE" <<'EOF'
# Acceptance

## FR-0001

### AC-1
EOF
    run $PY agent lex verify-acceptance --spec test --spec-file "$SPEC_FILE" --acceptance-file "$ACC_FILE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"missing bullet"* ]] || [[ "$output" == *"AC content invalid"* ]]
}

@test "L4 fail: AC has placeholder {{...}}" {
    cat > "$ACC_FILE" <<'EOF'
# Acceptance

## FR-0001

### AC-1
    - {{TODO: replace this}} # issue #207
EOF
    run $PY agent lex verify-acceptance --spec test --spec-file "$SPEC_FILE" --acceptance-file "$ACC_FILE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"placeholder"* ]]
}

@test "L5 fail: ghost FR not in spec" {
    cat > "$ACC_FILE" <<'EOF'
# Acceptance

## FR-0001

### AC-1
- valid bullet

## FR-0099

### AC-1
- ghost FR
EOF
    run $PY agent lex verify-acceptance --spec test --spec-file "$SPEC_FILE" --acceptance-file "$ACC_FILE"
    [ "$status" -eq 1 ]
    [[ "$output" == *"not present in spec"* ]] || [[ "$output" == *"ghost"* ]] || [[ "$output" == *"FR-0099"* ]]
}

@test "L1-L5 all pass (happy path)" {
    cat > "$ACC_FILE" <<'EOF'
# Acceptance

## FR-0001

### AC-1
- valid acceptance criterion

### AC-2
- another valid criterion
EOF
    run $PY agent lex verify-acceptance --spec test --spec-file "$SPEC_FILE" --acceptance-file "$ACC_FILE"
    [ "$status" -eq 0 ]
    [[ "$output" == *"checks passed"* ]]
}
