#!/usr/bin/env bats
# 测试 tools/check_identity.py

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
SCRIPT="$REPO_ROOT/tools/check_identity.py"

# ---------- 脚本存在性和语法 ----------

@test "ID-001: check_identity.py 存在" {
    [ -f "$SCRIPT" ]
}

@test "ID-002: check_identity.py 是合法 Python 3" {
    run python3 -c "import ast; ast.parse(open('$SCRIPT').read())"
    [ "$status" -eq 0 ]
}

@test "ID-003: check_identity.py 支持 --offline 模式" {
    run python3 "$SCRIPT" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--offline"* ]]
}

@test "ID-004: check_identity.py 支持 --repo 参数" {
    run python3 "$SCRIPT" --help
    [[ "$output" == *"--repo"* ]]
}

# ---------- L1-L5 检查项都覆盖 ----------

@test "ID-100: 脚本源码提及 L1 (gh 认证)" {
    run grep -q "L1" "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "ID-101: 脚本源码提及 L2 (viewerPermission)" {
    run grep -q "L2" "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "ID-102: 脚本源码提及 L3 (git user.name/email)" {
    run grep -q "L3" "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "ID-103: 脚本源码提及 L4 (commit author email vs gh 邮箱)" {
    run grep -q "L4" "$SCRIPT"
    [ "$status" -eq 0 ]
}

@test "ID-104: 脚本源码提及 L5 (remote owner vs gh user,advisory)" {
    run grep -q "L5" "$SCRIPT"
    [ "$status" -eq 0 ]
}

# ---------- 离线模式:好 case ----------

@test "ID-200: 离线 - 单一身份 + WRITE 角色 → [通过], exit 0" {
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user zillionare \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 0 ]
    [[ "$output" == *"\[通过\]"* ]]
    [[ "$output" != *"L4"* ]]
}

# ---------- 离线模式:坏 case ----------

@test "ID-301: 离线 - 两个身份 (L4 失败) → [拒绝], exit 1" {
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user quantclaws \
        --gh-emails "quantclaws@elsewhere.com" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 1 ]
    [[ "$output" == *"\[拒绝\]"* ]]
    [[ "$output" == *"L4"* ]]
}

@test "ID-302: 离线 - READ 角色 (L2 失败) → [拒绝], exit 1" {
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user quantclaws \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role READ
    [ "$status" -eq 1 ]
    [[ "$output" == *"\[拒绝\]"* ]]
    [[ "$output" == *"L2"* ]]
}

@test "ID-303: 离线 - gh 未认证 (L1 失败) → [拒绝], exit 1" {
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user "" \
        --gh-emails "" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 1 ]
    [[ "$output" == *"L1"* ]]
}

@test "ID-304: 离线 - git user.email 未设置 (L3 失败) → [拒绝], exit 1" {
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user zillionare \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name "" \
        --git-email "" \
        --last-commit-author "" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 1 ]
    [[ "$output" == *"L3"* ]]
}

# ---------- 离线模式:advisory (L5 不阻塞) ----------

@test "ID-400: 离线 - remote owner 与 gh user 不同 → [通过+警告], exit 0" {
    # 模拟"个人 token 操作 org repo"的合法场景
    run python3 "$SCRIPT" --offline \
        --repo zillionare/specforge \
        --gh-user quantclaws \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 0 ]
    [[ "$output" == *"\[通过+警告\]"* ]]
    [[ "$output" == *"L5"* ]]
    # L4 不应触发(commit email 在 gh 已知邮箱里)
    [[ "$output" != *"L4"* ]]
}
