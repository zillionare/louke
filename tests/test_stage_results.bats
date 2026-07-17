#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

setup() {
    WORK="$(mktemp -d)"
    cd "$WORK" || exit 1
    git init -q
    git config user.email "stage-results@example.com"
    git config user.name "Stage Results"
}

teardown() {
    cd "$REPO_ROOT" || true
    rm -rf "$WORK"
}

write_arch_fixture() {
    mkdir -p .louke/project/specs/demo tests/e2e
    cat > .louke/project/project.toml <<'EOF'
[project]
spec_id = "demo"
current_stage = "M-ARCH"

[meta]
test_framework = "pytest"

[e2e]
run = "python -c \"print('e2e-ok')\""
paths = ["tests/e2e"]
EOF
    cat > .louke/project/specs/demo/spec.md <<'EOF'
# Spec
EOF
    cat > .louke/project/specs/demo/acceptance.md <<'EOF'
<a id="ac-fr-0001"></a>

## FR-0001

### AC-1
- Works.
EOF
    cat > .louke/project/specs/demo/test-plan.md <<'EOF'
## 测试策略

- unit
- integration
- e2e
EOF
    cat > .louke/project/specs/demo/interfaces.md <<'EOF'
# Interfaces
EOF
    cat > .louke/project/specs/demo/architecture.md <<'EOF'
## 模块划分

- api

## FR mapping

- FR-0001 -> api
EOF
}

write_dev_fixture() {
    write_arch_fixture
    mkdir -p tests
    cat > tests/test_trace.py <<'EOF'
def test_trace():
    """AC-FR0001-01: works."""
    assert 2 == 2
EOF
    git add .
    git commit -q -m "chore: init"
    printf '\n# extra\n' >> tests/test_trace.py
    git add tests/test_trace.py
    git commit -q -m "feat: green – #1 – add trace"
    python -m louke agent prism review \
        --stage M-DEV \
        --spec-id demo \
        --commit-range HEAD~1..HEAD \
        --reviewed-target tests/test_trace.py >/dev/null
}

@test "stage-results: M-ARCH advance requires Prism review artifact" {
    write_arch_fixture

    run python -m louke agent maestro advance --stage M-ARCH --spec-id demo
    [ "$status" -ne 0 ]
    [[ "$output" == *"missing artifact"* ]]
    [ -f .louke/project/stage-results/demo/M-ARCH/author-result.json ]
}

@test "stage-results: M-ARCH advance passes with author + review artifacts" {
    write_arch_fixture
    python -m louke agent archer validate-arch --spec demo >/dev/null
    python -m louke agent prism review-arch \
        --spec-id demo \
        --reviewed-target .louke/project/specs/demo/architecture.md >/dev/null

    run python -m louke agent maestro advance --stage M-ARCH --spec-id demo
    [ "$status" -eq 0 ] || {
        echo "$output" >&2
        false
    }
    [[ "$output" == *"advanced to M-LOCK"* ]]
}

@test "stage-results: M-ARCH rejects review artifact with wrong source_command" {
    write_arch_fixture
    python -m louke agent archer validate-arch --spec demo >/dev/null
    python -m louke agent prism review-arch --spec-id demo >/dev/null
    python - <<'PY'
import json
from pathlib import Path
from louke.stage_results import _payload_hash

path = Path('.louke/project/stage-results/demo/M-ARCH/review-result.json')
data = json.loads(path.read_text(encoding='utf-8'))
data['metadata']['source_command'] = 'record-review'
data['output_hash'] = _payload_hash({k: v for k, v in data.items() if k != 'output_hash'})
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY

    run python -m louke agent maestro advance --stage M-ARCH --spec-id demo
    [ "$status" -ne 0 ]
    [[ "$output" == *"artifact metadata mismatch"* ]]
}

@test "stage-results: M-TESTPLAN advance requires Prism review artifact" {
    write_arch_fixture

    run python -m louke agent maestro advance --stage M-TESTPLAN --spec-id demo
    [ "$status" -ne 0 ]
    [[ "$output" == *"missing artifact"* ]]
    [ -f .louke/project/stage-results/demo/M-TESTPLAN/author-result.json ]
}

@test "stage-results: M-ARCH pass artifact cannot be minted via record-review" {
    write_arch_fixture

    run python -m louke agent prism record-review \
        --stage M-ARCH \
        --spec-id demo \
        --verdict pass \
        --reviewed-target .louke/project/specs/demo/architecture.md
    [ "$status" -ne 0 ]
    [[ "$output" == *"must come from a Prism review command"* ]]
}

@test "stage-results: M-TESTPLAN advance passes with author + review artifacts" {
    write_arch_fixture
    python -m louke agent archer validate-test-plan --spec demo >/dev/null
    python -m louke agent prism review-testplan \
        --spec-id demo \
        --reviewed-target .louke/project/specs/demo/test-plan.md >/dev/null

    run python -m louke agent maestro advance --stage M-TESTPLAN --spec-id demo
    [ "$status" -eq 0 ] || {
        echo "$output" >&2
        false
    }
    [[ "$output" == *"advanced to M-ARCH"* ]]
}

@test "stage-results: M-TESTPLAN rejects review artifact with missing source_command" {
    write_arch_fixture
    python -m louke agent archer validate-test-plan --spec demo >/dev/null
    python -m louke agent prism review-testplan --spec-id demo >/dev/null
    python - <<'PY'
import json
from pathlib import Path
from louke.stage_results import _payload_hash

path = Path('.louke/project/stage-results/demo/M-TESTPLAN/review-result.json')
data = json.loads(path.read_text(encoding='utf-8'))
metadata = data.get('metadata') or {}
metadata.pop('source_command', None)
data['metadata'] = metadata
data['output_hash'] = _payload_hash({k: v for k, v in data.items() if k != 'output_hash'})
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
PY

    run python -m louke agent maestro advance --stage M-TESTPLAN --spec-id demo
    [ "$status" -ne 0 ]
    [[ "$output" == *"artifact metadata mismatch"* ]]
}

@test "stage-results: M-TESTPLAN pass artifact cannot be minted via record-review" {
    write_arch_fixture

    run python -m louke agent prism record-review \
        --stage M-TESTPLAN \
        --spec-id demo \
        --verdict pass \
        --reviewed-target .louke/project/specs/demo/test-plan.md
    [ "$status" -ne 0 ]
    [[ "$output" == *"must come from a Prism review command"* ]]
}

@test "stage-results: M-DEV advance requires Prism review artifact and writes Keeper gate artifact" {
    write_dev_fixture

    run python -m louke agent maestro advance --stage M-DEV --spec-id demo --commit-range HEAD~1..HEAD
    [ "$status" -eq 0 ] || {
        echo "$output" >&2
        false
    }
    [ -f .louke/project/stage-results/demo/M-DEV/review-result.json ]
    [ -f .louke/project/stage-results/demo/M-DEV/gate-result.json ]
}

@test "stage-results: M-DEV pass artifact cannot be minted via record-review" {
    write_dev_fixture

    run python -m louke agent prism record-review \
        --stage M-DEV \
        --spec-id demo \
        --verdict pass \
        --commit-range HEAD~1..HEAD \
        --reviewed-target tests/test_trace.py
    [ "$status" -ne 0 ]
    [[ "$output" == *"must come from a Prism review command"* ]]
}

@test "stage-results: stale contract bundle blocks M-ARCH advance" {
    write_arch_fixture
    python -m louke agent archer validate-arch --spec demo >/dev/null
    python -m louke agent prism review-arch \
        --spec-id demo \
        --reviewed-target .louke/project/specs/demo/architecture.md >/dev/null
    printf '\n# drift\n' >> .louke/project/specs/demo/spec.md

    run python -m louke agent maestro advance --stage M-ARCH --spec-id demo
    [ "$status" -ne 0 ]
    [[ "$output" == *"contract bundle hash stale"* ]]
}

@test "stage-results: current_stage drift does not stale M-ARCH artifacts" {
    write_arch_fixture
    python -m louke agent archer validate-arch --spec demo >/dev/null
    python -m louke agent prism review-arch \
        --spec-id demo \
        --reviewed-target .louke/project/specs/demo/architecture.md >/dev/null
    python - <<'PY'
from pathlib import Path
path = Path('.louke/project/project.toml')
text = path.read_text(encoding='utf-8')
path.write_text(text.replace('current_stage = "M-ARCH"', 'current_stage = "M-LOCK"'), encoding='utf-8')
PY

    run python -m louke agent maestro advance --stage M-ARCH --spec-id demo
    [ "$status" -eq 0 ] || {
        echo "$output" >&2
        false
    }
    [[ "$output" == *"advanced to M-LOCK"* ]]
}

@test "stage-results: M-E2E requires review artifact and writes author + gate artifacts" {
    write_dev_fixture
    mkdir -p tests/e2e
    cat > tests/e2e/test_flow.py <<'EOF'
def test_flow():
    """AC-FR0001-01: works."""
    assert 2 == 2
EOF
    git add tests/e2e/test_flow.py
    git commit -q -m "feat: green – #1 – add e2e trace"
    python -m louke agent prism review \
        --stage M-E2E \
        --spec-id demo \
        --commit-range HEAD~1..HEAD \
        --reviewed-target tests/e2e/test_flow.py >/dev/null

    run python -m louke agent maestro advance --stage M-E2E --spec-id demo --commit-range HEAD~1..HEAD
    [ "$status" -eq 0 ] || {
        echo "$output" >&2
        false
    }
    [ -f .louke/project/stage-results/demo/M-E2E/author-result.json ]
    [ -f .louke/project/stage-results/demo/M-E2E/review-result.json ]
    [ -f .louke/project/stage-results/demo/M-E2E/gate-result.json ]
}

@test "stage-results: M-E2E normalizes duplicate tests roots before gate metadata compare" {
    write_dev_fixture
    mkdir -p tests/e2e
    cat > tests/e2e/test_flow.py <<'EOF'
def test_flow():
    """AC-FR0001-01: works."""
    assert 2 == 2
EOF
    git add tests/e2e/test_flow.py
    git commit -q -m "feat: green – #1 – add e2e trace"
    python - <<'PY'
from pathlib import Path
path = Path('.louke/project/project.toml')
text = path.read_text(encoding='utf-8')
text = text.replace('paths = ["tests/e2e"]', 'paths = ["tests/e2e/", " tests/e2e "]')
path.write_text(text, encoding='utf-8')
PY
    python -m louke agent prism review \
        --stage M-E2E \
        --spec-id demo \
        --commit-range HEAD~1..HEAD \
        --reviewed-target tests/e2e/test_flow.py >/dev/null

    run python -m louke agent maestro advance --stage M-E2E --spec-id demo --commit-range HEAD~1..HEAD
    [ "$status" -eq 0 ] || {
        echo "$output" >&2
        false
    }
    python - <<'PY'
import json
from pathlib import Path
data = json.loads(Path('.louke/project/stage-results/demo/M-E2E/gate-result.json').read_text(encoding='utf-8'))
assert (data.get('metadata') or {}).get('tests_roots') == ['tests/e2e'], data
PY
}

@test "stage-results: force advance requires waiver artifact" {
    write_arch_fixture

    run python -m louke agent maestro advance --stage M-ARCH --spec-id demo --force
    [ "$status" -ne 0 ]
    [[ "$output" == *"missing or stale waiver artifact"* ]]

    python -m louke agent maestro waive \
        --stage M-ARCH \
        --spec-id demo \
        --approved-by Aaron \
        --reason "manual override for review" >/dev/null

    run python -m louke agent maestro advance --stage M-ARCH --spec-id demo --force
    [ "$status" -eq 0 ] || {
        echo "$output" >&2
        false
    }
    [[ "$output" == *"forced advance to M-LOCK"* ]]
}
