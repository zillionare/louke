#!/usr/bin/env bats

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
KEEPER_PY="$REPO_ROOT/louke/keeper.py"
SHIELD_PY="$REPO_ROOT/louke/shield.py"
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
    git config user.email "keeper@example.com"
    git config user.name "Keeper"
}

commit() {
    local msg="$1"
    echo "$msg" > "$(date +%s%N).txt"
    git add .
    git commit -q -m "$msg"
}

@test "FR-0600 AC-1: keeper.py no longer defines _load_quality_gates" {
    run grep -Eq "^def _load_quality_gates\(" "$KEEPER_PY"
    [ "$status" -ne 0 ] || {
        echo "FAIL: _load_quality_gates still defined in keeper.py" >&2
        false
    }
}

@test "FR-0600 AC-2: keeper.py no longer defines run_external_tool" {
    run grep -Eq "^def run_external_tool\(" "$KEEPER_PY"
    [ "$status" -ne 0 ] || {
        echo "FAIL: run_external_tool still defined in keeper.py" >&2
        false
    }
}

@test "FR-0600 AC-3: keeper.py no longer defines run_project_tests" {
    run grep -Eq "^def run_project_tests\(" "$KEEPER_PY"
    [ "$status" -ne 0 ] || {
        echo "FAIL: run_project_tests still defined in keeper.py" >&2
        false
    }
}

@test "FR-0600 AC-4: keeper.py contains no e2e-related code" {
    run grep -iqE "e2e|end.to.end" "$KEEPER_PY"
    [ "$status" -ne 0 ] || {
        echo "FAIL: keeper.py still contains e2e references" >&2
        false
    }
}

@test "FR-0600 AC-4: shield.py retains _load_quality_gates, _load_e2e_config, cmd_run_e2e" {
    run grep -Eq "^def _load_quality_gates\(" "$SHIELD_PY"
    [ "$status" -eq 0 ] || { echo "FAIL: _load_quality_gates missing in shield.py" >&2; false; }
    run grep -Eq "^def _load_e2e_config\(" "$SHIELD_PY"
    [ "$status" -eq 0 ] || { echo "FAIL: _load_e2e_config missing in shield.py" >&2; false; }
    run grep -Eq "^def cmd_run_e2e\(" "$SHIELD_PY"
    [ "$status" -eq 0 ] || { echo "FAIL: cmd_run_e2e missing in shield.py" >&2; false; }
}

@test "FR-0600 AC-9: --tests flag exits non-zero with deprecation message" {
    init_tmp_repo
    run python -m louke agent keeper gate --tests
    [ "$status" -ne 0 ]
    [[ "$output" == *"v0.7-001"* ]] || {
        echo "stderr/output: $output" >&2
        false
    }
}

@test "FR-0600 AC-9: --lint flag exits non-zero with deprecation message" {
    init_tmp_repo
    run python -m louke agent keeper gate --lint
    [ "$status" -ne 0 ]
    [[ "$output" == *"v0.7-001"* ]] || {
        echo "stderr/output: $output" >&2
        false
    }
}

@test "FR-0600 AC-9: --typecheck flag exits non-zero with deprecation message" {
    init_tmp_repo
    run python -m louke agent keeper gate --typecheck
    [ "$status" -ne 0 ]
    [[ "$output" == *"v0.7-001"* ]] || {
        echo "stderr/output: $output" >&2
        false
    }
}

@test "FR-0600 AC-5/AC-7/AC-8: lk keeper gate checks format/RGR/AC trace/anti-pattern" {
    init_tmp_repo
    commit "chore: init"
    commit "test: red – #1 – add failing test"
    commit "feat: green – #1 – implement feature"
    commit "refactor: – #1 – clean up"
    run python -m louke agent keeper gate --commit-range HEAD~3..HEAD \
        --skip-ac-trace --skip-anti-pattern
    [ "$status" -eq 0 ] || {
        echo "keeper gate failed: $output" >&2
        false
    }
}
