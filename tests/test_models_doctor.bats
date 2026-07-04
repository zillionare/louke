#!/usr/bin/env bash
# Regression tests for lk models doctor (v0.6-009 + v0.6.13)
# 关键: 覆盖 GLM v0.6.13 review 找到的 ok 遮蔽 bug

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    export TEST_HOME="$(mktemp -d)"
    export HOME="$TEST_HOME"  # 关键: 让 resolve_model 读 TEST_HOME/.louke/models.json
    export LOUKE_HOME="$TEST_HOME/.louke"
    mkdir -p "$LOUKE_HOME/agents" "$TEST_HOME/bin"
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
}

@test "doctor 在 alias 存在时不 crash (v0.6.13 修复)" {
    cat > "$LOUKE_HOME/agents/Archer.md" <<'AGENT_EOF'
---
name: archer
mode: subagent
models:
  - glm-5.2
  - deepseek-v4-pro
permission:
  bash: allow
  question: allow
---
test archer
AGENT_EOF
    cat > "$LOUKE_HOME/models.json" <<'CFG_EOF'
{
  "$schema": "louke://models-config",
  "version": 1,
  "aliases": {
    "glm-5.2": "ark/glm-5.2",
    "deepseek-v4-pro": "ark/deepseek-v4-pro"
  },
  "assignments": {}
}
CFG_EOF
    run "$TEST_HOME/bin/lk" models doctor
    [ "$status" -eq 0 ] || [ "$status" -eq 1 ]
    [[ ! "$output" == *"TypeError"* ]]
    [[ ! "$output" == *"'bool' object is not callable"* ]]
    [[ "$output" == *"glm-5.2"* ]]
    [[ "$output" == *"ark/glm-5.2"* ]]
}

@test "doctor 多 alias 时不 crash (回归测试)" {
    cat > "$LOUKE_HOME/agents/Archer.md" <<'AGENT_EOF'
---
name: archer
mode: subagent
models:
  - glm-5.2
  - minimax-m3
  - kimi-2.7-code
permission:
  bash: allow
---
test
AGENT_EOF
    cat > "$LOUKE_HOME/models.json" <<'CFG_EOF'
{
  "$schema": "louke://models-config",
  "version": 1,
  "aliases": {
    "glm-5.2": "ark/glm-5.2",
    "minimax-m3": "ark/minimax-m3",
    "kimi-2.7-code": "ark/kimi-k2.7-code"
  },
  "assignments": {}
}
CFG_EOF
    run "$TEST_HOME/bin/lk" models doctor
    [[ ! "$output" == *"TypeError"* ]]
    [[ "$output" == *"✓"* ]]
    [[ "$output" == *"ark/glm-5.2"* ]]
    [[ "$output" == *"ark/minimax-m3"* ]]
    [[ "$output" == *"ark/kimi-k2.7-code"* ]]
}

@test "doctor 全部 unresolved 时不 crash (边界)" {
    cat > "$LOUKE_HOME/agents/Archer.md" <<'AGENT_EOF'
---
name: archer
mode: subagent
models:
  - nonexistent-abstract-1
  - nonexistent-abstract-2
permission:
  bash: allow
---
test
AGENT_EOF
    cat > "$LOUKE_HOME/models.json" <<'CFG_EOF'
{
  "$schema": "louke://models-config",
  "version": 1,
  "aliases": {},
  "assignments": {}
}
CFG_EOF
    run "$TEST_HOME/bin/lk" models doctor
    [ "$status" -eq 1 ]
    [[ ! "$output" == *"TypeError"* ]]
    [[ "$output" == *"✗"* ]]
}
