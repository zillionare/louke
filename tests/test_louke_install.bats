#!/usr/bin/env bats
# Smoke tests to ensure the venv always runs workspace louke, not stale site-packages.
# These tests are specific to the developer's local install layout
# (/Users/aaronyang/.louke/venv); they auto-skip on CI or any other env.

setup() {
  LOUKE_ROOT="${BATS_TEST_DIRNAME}/.."
  VENV_BIN="/Users/aaronyang/.louke/venv/bin"
  if [ ! -x "$VENV_BIN/pip" ] && [ ! -x "$VENV_BIN/python3" ]; then
    skip "louke_install smoke tests require the developer-local venv at $VENV_BIN (CI is unrelated)"
  fi
  export PATH="${VENV_BIN}:${PATH}"
}

@test "pip show louke reports a valid louke installation location" {
  run pip show louke
  [ "$status" -eq 0 ]
  [[ "$output" == *"Name: louke"* ]] || {
    echo "FAIL: pip show louke missing package name: $output"
    return 1
  }
  [[ "$output" == *"Location: /Users/aaronyang/.louke/venv/"* ]] || \
  [[ "$output" == *"Location: /Users/aaronyang/workspace/louke"* ]] || {
    echo "FAIL: louke installation location is unexpected: $output"
    return 1
  }
}

@test "site-packages louke resolves to workspace directory" {
  # Locate the actual path Python would load louke from outside the workspace.
  run /Users/aaronyang/.louke/venv/bin/python3 - <<'PY'
import louke, os, sys
print(louke.__file__)
print(os.path.realpath(louke.__file__))
PY
  [ "$status" -eq 0 ]
  site_pkg_path="${output%%$'\n'* }"
  real_path="${output#*$'\n' }"
  # We expect either the __file__ or its realpath to live inside the workspace.
  [[ "$site_pkg_path" == /Users/aaronyang/workspace/louke/louke/* ]] || \
  [[ "$real_path" == /Users/aaronyang/workspace/louke/louke/* ]] || {
    echo "FAIL: site-packages louke does not resolve to workspace: $output"
    return 1
  }
}

@test "lk agent devon commit-rgr --help shows v0.7 CLI (no --task-id, green/refactor only)" {
  run lk agent devon commit-rgr --help
  [ "$status" -eq 0 ]
  [[ "$output" != *"task-id"* ]] || { echo "FAIL: site-packages louke stale (--task-id still present)"; return 1; }
  [[ "$output" == *"green/refactor"* ]] || { echo "FAIL: --phase help does not mention green/refactor"; return 1; }
}
