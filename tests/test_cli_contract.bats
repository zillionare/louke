#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

@test "CLI contract: unknown top-level agent command exits non-zero" {
    run python -m louke archer ci-scan --spec demo
    [ "$status" -ne 0 ]
    [[ "$output" == *"unknown command 'archer'"* ]]
}

@test "CLI contract: agent router still accepts archer ci-scan" {
    WORK="$(mktemp -d)"
    cd "$WORK" || exit 1
    mkdir -p .louke/project/specs/demo tests
    cat > .louke/project/specs/demo/acceptance.md <<'EOF'
<a id="ac-fr-0001"></a>

## FR-0001

### AC-1
- Works.
EOF
    cat > tests/test_trace.py <<'EOF'
def test_trace():
    """AC-FR0001-01: works."""
    assert 2 == 2
EOF

    run python -m louke agent archer ci-scan --spec demo --tests tests
    [ "$status" -eq 0 ]
}
