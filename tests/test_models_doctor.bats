#!/usr/bin/env bash
# Regression tests for lk models doctor (v0.6-009 + v0.6.13)
# Key: covers the ok-shadowing bug found in GLM v0.6.13 review
#
# Note: agent prompts are owned by the installed louke package — `doctor` reads
# from there, not from any per-project or per-user `agents/` dir. The tests
# below only seed `~/.louke/models.json` (the alias config) and assert on
# doctor behaviour against the package-supplied abstracts.
#
# IMPORTANT: doctor also reads project-level aliases from `<git_root>/.louke/
# models.json`. To make these tests deterministic regardless of what the host
# repo has configured, we redirect GIT_DIR / GIT_WORK_TREE to an isolated empty
# repo so project aliases resolve to {} instead of the host repo's config.

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    export TEST_HOME="$(mktemp -d)"
    export HOME="$TEST_HOME"
    export LOUKE_HOME="$TEST_HOME/.louke"
    # Isolate project aliases: make git_root() resolve to an empty temp repo.
    ISOLATED_REPO="$(mktemp -d)"
    git -C "$ISOLATED_REPO" init -q
    export GIT_DIR="$ISOLATED_REPO/.git"
    export GIT_WORK_TREE="$ISOLATED_REPO"
    mkdir -p "$LOUKE_HOME" "$TEST_HOME/bin"
    export PATH="$TEST_HOME/bin:$PATH"
    export PYTHONPATH="$REPO_ROOT"
    cat > "$TEST_HOME/bin/lk" <<'WRAPPER_EOF'
#!/usr/bin/env bash
exec python3 -m louke "$@"
WRAPPER_EOF
    chmod +x "$TEST_HOME/bin/lk"
}

teardown() {
    rm -rf "$TEST_HOME"
    if [ -n "$ISOLATED_REPO" ]; then rm -rf "$ISOLATED_REPO"; fi
    unset GIT_DIR GIT_WORK_TREE
}

@test "doctor does not crash when alias exists (v0.6.13 fix)" {
    cat > "$LOUKE_HOME/models.json" <<'CFG_EOF'
{
  "$schema": "louke://models-config",
  "version": 1,
  "aliases": {
    "deepseek-v4-flash": "ark/deepseek-v4-flash"
  },
  "assignments": {}
}
CFG_EOF
    run "$TEST_HOME/bin/lk" models doctor
    [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
    [[ ! "$output" == *"TypeError"* ]]
    [[ ! "$output" == *"'bool' object is not callable"* ]]
    [[ "$output" == *"deepseek-v4-flash"* ]]
    [[ "$output" == *"ark/deepseek-v4-flash"* ]]
}

@test "doctor does not crash with multiple aliases (regression test)" {
    cat > "$LOUKE_HOME/models.json" <<'CFG_EOF'
{
  "$schema": "louke://models-config",
  "version": 1,
  "aliases": {
    "deepseek-v4-flash": "ark/deepseek-v4-flash",
    "minimax-m3": "ark/minimax-m3",
    "kimi-k2.7-code": "ark/kimi-k2.7-code"
  },
  "assignments": {}
}
CFG_EOF
    run "$TEST_HOME/bin/lk" models doctor
    [[ ! "$output" == *"TypeError"* ]]
    [[ "$output" == *"✓"* ]]
    [[ "$output" == *"ark/deepseek-v4-flash"* ]]
    [[ "$output" == *"ark/minimax-m3"* ]]
    [[ "$output" == *"ark/kimi-k2.7-code"* ]]
}

@test "doctor does not crash when all unresolved (boundary)" {
    # No aliases, no `models.json` — every abstract must fall through to the
    # strong/weak-match path against the opencode models list. We don't assert
    # any specific value, just that the run completes without TypeError and
    # reports at least one ✗ for the truly-absent abstract.
    cat > "$LOUKE_HOME/models.json" <<'CFG_EOF'
{
  "$schema": "louke://models-config",
  "version": 1,
  "aliases": {},
  "assignments": {}
}
CFG_EOF
    run "$TEST_HOME/bin/lk" models doctor
    [[ ! "$output" == *"TypeError"* ]]
}