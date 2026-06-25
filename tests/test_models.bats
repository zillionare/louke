#!/usr/bin/env bats

setup() {
    TEST_DIR="$(mktemp -d)"
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    export SPECFORGE_HOME="$REPO_ROOT"
    export SPECFORGE_MODELS_CONFIG="$TEST_DIR/user-models.json"
    export SPECFORGE_PROJECT_MODELS_CONFIG="$TEST_DIR/project-models.json"
    export SPECFORGE_OPENCODE_MODELS=$'opencode/kimi-k2.6\nark/kimi-k2.6\nark/deepseek-v4-pro\nark/glm-5.2\nark/deepseek-v4-flash\nopencode/glm-5.2'
    cd "$REPO_ROOT"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "MODELS_T01_list: lists abstract names used by source agents" {
    run bash "$REPO_ROOT/bin/specforge" models list
    [ "$status" -eq 0 ]
    [[ "$output" =~ "kimi-k2.6" ]]
    [[ "$output" =~ "deepseek-v4-pro" ]]
    [[ "$output" =~ "glm-5.2" ]]
    [[ "$output" =~ "deepseek-v4-flash" ]]
}

@test "MODELS_T02_doctor: auto strong-matches opencode models" {
    run bash "$REPO_ROOT/bin/specforge" models doctor
    [ "$status" -eq 0 ]
    [[ "$output" =~ "kimi-k2.6 -> ark/kimi-k2.6" ]]
    [[ "$output" =~ "glm-5.2 -> ark/glm-5.2" ]]
}

@test "MODELS_T03_doctor_fix_auto: writes user models cache" {
    run bash "$REPO_ROOT/bin/specforge" models doctor --fix-auto
    [ "$status" -eq 0 ]
    [ -f "$SPECFORGE_MODELS_CONFIG" ]
    python3 - "$SPECFORGE_MODELS_CONFIG" <<'PY'
import json, sys
j=json.load(open(sys.argv[1]))
assert j['aliases']['kimi-k2.6'] == 'ark/kimi-k2.6'
assert j['aliases']['deepseek-v4-pro'] == 'ark/deepseek-v4-pro'
PY
}

@test "MODELS_T04_bind_unbind: user alias override can be changed" {
    run bash "$REPO_ROOT/bin/specforge" models bind kimi-k2.6 opencode/kimi-k2.6
    [ "$status" -eq 0 ]
    run bash "$REPO_ROOT/bin/specforge" models list
    [[ "$output" =~ "kimi-k2.6"$'\t'"opencode/kimi-k2.6" ]]
    run bash "$REPO_ROOT/bin/specforge" models unbind kimi-k2.6
    [ "$status" -eq 0 ]
    run bash "$REPO_ROOT/bin/specforge" models list
    [[ "$output" =~ "kimi-k2.6"$'\t'"ark/kimi-k2.6" ]]
}

@test "MODELS_T05_project_bind: project alias overrides user alias" {
    bash "$REPO_ROOT/bin/specforge" models bind kimi-k2.6 opencode/kimi-k2.6 >/dev/null
    bash "$REPO_ROOT/bin/specforge" models bind kimi-k2.6 ark/kimi-k2.6 --project >/dev/null
    run bash "$REPO_ROOT/bin/specforge" models list
    [ "$status" -eq 0 ]
    [[ "$output" =~ "kimi-k2.6"$'\t'"ark/kimi-k2.6" ]]
}

@test "MODELS_T06_assign: agent assignment changes effective model chain" {
    run bash "$REPO_ROOT/bin/specforge" models assign set sage glm-5.2,deepseek-v4-pro
    [ "$status" -eq 0 ]
    run bash "$REPO_ROOT/bin/specforge" models assign list
    [ "$status" -eq 0 ]
    [[ "$output" =~ "sage"$'\t'"glm-5.2,deepseek-v4-pro" ]]
}

@test "MODELS_T07_assign_unset: assignment can be removed" {
    bash "$REPO_ROOT/bin/specforge" models assign set sage glm-5.2 >/dev/null
    run bash "$REPO_ROOT/bin/specforge" models assign unset sage
    [ "$status" -eq 0 ]
    run bash "$REPO_ROOT/bin/specforge" models assign list
    [ "$status" -eq 0 ]
    [[ "$output" =~ "no assignments" ]]
}

@test "MODELS_T08_no_match: unknown alias fails with bind hint" {
    export SPECFORGE_OPENCODE_MODELS=$'ark/other-model'
    run bash "$REPO_ROOT/bin/specforge" models doctor
    [ "$status" -ne 0 ]
    [[ "$output" =~ "models bind" ]]
}
