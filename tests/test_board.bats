#!/usr/bin/env bats

setup() {
    TEST_DIR="$(mktemp -d)"
    REPO_ROOT="$(cd "$BATS_TEST_DIRNAME/.." && pwd)"
    export SPECFORGE_HOME="$REPO_ROOT"
    export SPECFORGE_MODELS_CONFIG="$TEST_DIR/user-models.json"
    export SPECFORGE_PROJECT_MODELS_CONFIG="$TEST_DIR/project-models.json"
    export SPECFORGE_OPENCODE_MODELS=$'opencode/kimi-k2.6\nark/kimi-k2.6\nark/deepseek-v4-pro\nark/glm-5.2\nark/deepseek-v4-flash'
    cd "$TEST_DIR"
}

teardown() {
    rm -rf "$TEST_DIR"
}

@test "BOARD_T01_opencode: generates 18 opencode agent files" {
    mkdir -p p && cd p
    cp -R "$REPO_ROOT/agents" .specforge_agents_src
    mkdir -p .specforge
    cp -R .specforge_agents_src .specforge/agents
    run bash "$REPO_ROOT/bin/specforge" board opencode
    [ "$status" -eq 0 ]
    [ "$(ls .opencode/agents/*.md | wc -l | tr -d ' ')" -eq 18 ]
    grep -q "^model: ark/kimi-k2.6$" .opencode/agents/sage.md
}

@test "BOARD_T02_assignment: opencode board uses agent assignment override" {
    mkdir -p p && cd p
    mkdir -p .specforge
    cp -R "$REPO_ROOT/agents" .specforge/agents
    bash "$REPO_ROOT/bin/specforge" models assign set sage glm-5.2 >/dev/null
    run bash "$REPO_ROOT/bin/specforge" board opencode
    [ "$status" -eq 0 ]
    grep -q "^model: ark/glm-5.2$" .opencode/agents/sage.md
}

@test "BOARD_T03_body: generated opencode body contains source prompt" {
    mkdir -p p && cd p
    mkdir -p .specforge
    cp -R "$REPO_ROOT/agents" .specforge/agents
    bash "$REPO_ROOT/bin/specforge" board opencode >/dev/null
    grep -q "你是 \*\*Sage\*\*" .opencode/agents/sage.md
}

@test "BOARD_T04_idempotent: rerun produces same file hash" {
    mkdir -p p && cd p
    mkdir -p .specforge
    cp -R "$REPO_ROOT/agents" .specforge/agents
    bash "$REPO_ROOT/bin/specforge" board opencode >/dev/null
    BEFORE=$(shasum .opencode/agents/sage.md | awk '{print $1}')
    bash "$REPO_ROOT/bin/specforge" board opencode >/dev/null
    AFTER=$(shasum .opencode/agents/sage.md | awk '{print $1}')
    [ "$BEFORE" = "$AFTER" ]
}

@test "BOARD_T05_vscode: generates symlinks" {
    mkdir -p p && cd p
    mkdir -p .specforge
    cp -R "$REPO_ROOT/agents" .specforge/agents
    run bash "$REPO_ROOT/bin/specforge" board vscode
    [ "$status" -eq 0 ]
    [ -L .github/agents/Sage.agent.md ]
    [ -e .github/agents/Sage.agent.md ]
}

@test "BOARD_T06_status: reports installed boards" {
    mkdir -p p && cd p
    mkdir -p .specforge
    cp -R "$REPO_ROOT/agents" .specforge/agents
    bash "$REPO_ROOT/bin/specforge" board opencode >/dev/null
    run bash "$REPO_ROOT/bin/specforge" board status
    [ "$status" -eq 0 ]
    [[ "$output" =~ "opencode  ✓" ]]
}

@test "BOARD_T07_unknown: unknown board fails" {
    mkdir -p p && cd p
    mkdir -p .specforge
    cp -R "$REPO_ROOT/agents" .specforge/agents
    run bash "$REPO_ROOT/bin/specforge" board unknown
    [ "$status" -ne 0 ]
}

@test "BOARD_T08_init_board_none: skips auto board" {
    run bash "$REPO_ROOT/bin/specforge" init proj --board=none
    [ "$status" -eq 0 ]
    [ ! -d proj/.opencode/agents ]
}

@test "BOARD_T09_init_board_opencode: explicit board installs opencode" {
    run bash "$REPO_ROOT/bin/specforge" init proj --board=opencode
    [ "$status" -eq 0 ]
    [ -f proj/.opencode/agents/sage.md ]
}
