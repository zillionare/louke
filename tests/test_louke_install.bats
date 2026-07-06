#!/usr/bin/env bats
# Smoke tests to ensure the venv always runs workspace louke, not stale site-packages.

setup() {
  LOUKE_ROOT="${BATS_TEST_DIRNAME}/.."
  VENV_BIN="/Users/aaronyang/.louke/venv/bin"
  export PATH="${VENV_BIN}:${PATH}"
}

@test "pip show louke reports workspace location" {
  run pip show louke
  [ "$status" -eq 0 ]
  # After pip install -e . the package Location must be the workspace, not a separate site-packages copy.
  [[ "$output" == *"Location: /Users/aaronyang/workspace/louke"* ]] || {
    echo "FAIL: louke is not installed from workspace: $output"
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

@test "lk agent devon commit-rgr --help shows FR-0400 CLI (no --task-id, --phase {green,refactor})" {
  run lk agent devon commit-rgr --help
  [ "$status" -eq 0 ]
  [[ "$output" != *"task-id"* ]] || { echo "FAIL: site-packages louke stale (--task-id still present)"; return 1; }
  [[ "$output" == *"--phase {green,refactor}"* ]] || { echo "FAIL: --phase choices not green,refactor"; return 1; }
}
