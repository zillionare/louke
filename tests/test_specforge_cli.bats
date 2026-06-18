#!/usr/bin/env bats
# 测试 bin/specforge — framework 的统一 CLI 入口
# 重点:子命令分发、参数透传、upgrade 安全护栏、help 自描述

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
CLI="$REPO_ROOT/bin/specforge"

setup() {
    TEST_DIR="$(mktemp -d)"
    export SPECFORGE_HOME="$TEST_DIR/fake-home"
    mkdir -p "$SPECFORGE_HOME"
    # 默认放一份 VERSION 让大多数测试能读出 "0.1.0"
    echo "0.1.0" > "$SPECFORGE_HOME/VERSION"
    # 准备好供 cmd_checkup / cmd_verify_issue 调用的 Python 脚本
    mkdir -p "$SPECFORGE_HOME/tools"
    cp "$REPO_ROOT/tools/check_identity.py" "$SPECFORGE_HOME/tools/"
    cp "$REPO_ROOT/tools/verify_issue_schema.py" "$SPECFORGE_HOME/tools/"
}

teardown() {
    rm -rf "$TEST_DIR"
}

# ---------- 脚本存在性和语法 ----------

@test "CLI-001: bin/specforge 存在" {
    [ -f "$CLI" ]
}

@test "CLI-002: bin/specforge 是合法 bash 脚本" {
    run bash -n "$CLI"
    [ "$status" -eq 0 ]
}

@test "CLI-003: bin/specforge 有可执行权限 (或可被 bash 调用)" {
    # 用 bash 调用即可,不强求 +x;install.sh 会 chmod
    run bash "$CLI" version
    [ "$status" -eq 0 ]
}

# ---------- help / version ----------

@test "CLI-100: 不带参数 → help" {
    run bash "$CLI"
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "CLI-101: help 子命令 → usage" {
    run bash "$CLI" help
    [ "$status" -eq 0 ]
    [[ "$output" == *"specforge"* ]]
    [[ "$output" == *"init"* ]]
    [[ "$output" == *"checkup"* ]]
    [[ "$output" == *"verify-issue"* ]]
    [[ "$output" == *"upgrade"* ]]
}

@test "CLI-102: -h / --help 等同 help" {
    run bash "$CLI" -h
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
    run bash "$CLI" --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"Usage:"* ]]
}

@test "CLI-103: version 打印版本号" {
    run bash "$CLI" version
    [ "$status" -eq 0 ]
    [[ "$output" == *"specforge 0.1.0"* ]]
}

@test "CLI-104: -v / --version 等同 version" {
    run bash "$CLI" -v
    [ "$status" -eq 0 ]
    [[ "$output" == *"0.1.0"* ]]
    run bash "$CLI" --version
    [ "$status" -eq 0 ]
    [[ "$output" == *"0.1.0"* ]]
}

@test "CLI-105: version 打印 install path" {
    run bash "$CLI" version
    [ "$status" -eq 0 ]
    [[ "$output" == *"$SPECFORGE_HOME"* ]]
}

@test "CLI-106: SPECFORGE_HOME 缺 VERSION → version 报 dev" {
    rm -f "$SPECFORGE_HOME/VERSION"
    run bash "$CLI" version
    [ "$status" -eq 0 ]
    [[ "$output" == *"dev"* ]]
}

@test "CLI-108: help 明确区分 User-driven vs Agent-driven 命令" {
    run bash "$CLI" help
    [ "$status" -eq 0 ]
    # 必须在 help 顶部提示"agent 自动调用"原则
    [[ "$output" == *"agent"* ]]
    [[ "$output" == *"debug"* ]]
    # 必须有显式分类标题
    [[ "$output" == *"User-driven"* ]]
    [[ "$output" == *"Agent-driven"* ]]
}

@test "CLI-109: help 把 checkup/verify-issue 标为 Agent-driven" {
    # 防止以后有人改回「所有命令都是人跑」
    run bash "$CLI" help
    [ "$status" -eq 0 ]
    # checkup 应出现在 Agent-driven 块,而非 User-driven 块
    awk '/User-driven/{u=1; next} /Agent-driven/{u=0; a=1} u && /checkup/{print "FAIL: checkup in user block"; exit 1} a && /checkup/{found_checkup=1} END{exit !found_checkup}' <<<"$output"
    # verify-issue 同样
    awk '/User-driven/{u=1; next} /Agent-driven/{u=0; a=1} u && /verify-issue/{print "FAIL: verify-issue in user block"; exit 1} a && /verify-issue/{found_vi=1} END{exit !found_vi}' <<<"$output"
}

@test "CLI-110: help 把 init/upgrade 标为 User-driven" {
    run bash "$CLI" help
    [ "$status" -eq 0 ]
    # init 必须在 User-driven 块
    awk '/User-driven/{u=1; next} /Agent-driven/{u=0} u && /init/{found_init=1} END{exit !found_init}' <<<"$output"
    # upgrade 必须在 User-driven 块
    awk '/User-driven/{u=1; next} /Agent-driven/{u=0} u && /upgrade/{found_up=1} END{exit !found_up}' <<<"$output"
}

@test "CLI-107: help 自描述所有 6 个子命令" {
    run bash "$CLI" help
    [ "$status" -eq 0 ]
    for sub in "init" "checkup" "verify-issue" "doctor" "upgrade" "version"; do
        [[ "$output" == *"$sub"* ]] || { echo "help missing: $sub" >&2; false; }
    done
}

# ---------- 错误处理 ----------

@test "CLI-200: 未知子命令 → die, exit 1" {
    run bash "$CLI" bogus-cmd
    [ "$status" -eq 1 ]
    [[ "$output" == *"unknown command"* ]]
    [[ "$output" == *"bogus-cmd"* ]]
}

@test "CLI-201: init 不带名字 → die" {
    run bash "$CLI" init
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage: specforge init"* ]]
}

@test "CLI-202: init 目录已存在 → die" {
    mkdir -p "$TEST_DIR/existing-project"
    cd "$TEST_DIR"
    run bash "$CLI" init existing-project
    [ "$status" -eq 1 ]
    [[ "$output" == *"already exists"* ]]
}

@test "CLI-203: checkup 不带 repo → die" {
    run bash "$CLI" checkup
    [ "$status" -eq 1 ]
    [[ "$output" == *"Usage: specforge checkup"* ]]
}

# ---------- checkup 参数透传 ----------

@test "CLI-300: checkup 转发 --offline + 全部参数给 check_identity.py" {
    # 用 --offline 模式避免打真实 GitHub;检查 exit 0 + [通过]
    # 注: bash 3.2 (macOS) 在 [[ glob ]] 里不解析 \[ 转义,用 [通过] 而非 \[通过\]
    run bash "$CLI" checkup zillionare/specforge --offline \
        --gh-user zillionare \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
    [[ "$output" != *"L4"* ]]
}

@test "CLI-301: doctor 是 checkup 的别名" {
    run bash "$CLI" doctor zillionare/specforge --offline \
        --gh-user zillionare \
        --gh-emails "aaron_yang@jieyu.ai" \
        --git-name zillionare \
        --git-email aaron_yang@jieyu.ai \
        --last-commit-author "zillionare <aaron_yang@jieyu.ai>" \
        --remote-url "git@github.com:zillionare/specforge.git" \
        --repo-role WRITE
    [ "$status" -eq 0 ]
    [[ "$output" == *"[通过]"* ]]
}

# ---------- verify-issue 参数透传 ----------

@test "CLI-400: verify-issue 透传 --offline + spec-file + issues-json" {
    # 写一份最小 spec.md(只有一个锚点 FR-001)+ 一份合法 form-rendered issue
    cat > "$TEST_DIR/spec.md" <<'EOF'
# test spec
<a id="fr-001"></a>
## FR-001
done.
EOF
    # GitHub 把 form 字段渲染为 ### Label / value 格式
    cat > "$TEST_DIR/issues.json" <<'EOF'
[
  {"number": 1, "title": "[FR-001] test feature", "labels": [{"name": "Feature"}],
   "body": "### 需求 ID\nFR-001\n\n### Spec 链接\nhttps://github.com/x/y/blob/main/.specforge/project/specs/001/spec.md#fr-001\n\n### 验收标准\nAC-1: it works\n"}
]
EOF
    run bash "$CLI" verify-issue --offline \
        --spec-file "$TEST_DIR/spec.md" \
        --issues-json "$TEST_DIR/issues.json"
    [ "$status" -eq 0 ]
    [[ "$output" != *"L2"* ]]
    [[ "$output" != *"L3"* ]]
    [[ "$output" != *"L7"* ]]
}

@test "CLI-401: verify-issue 缺 --offline 缺 --spec → exit 2" {
    run bash "$CLI" verify-issue
    [ "$status" -eq 2 ]
}

# ---------- upgrade 安全护栏 ----------

@test "CLI-500: upgrade 在非 git 目录 → die" {
    # SPECFORGE_HOME 已经 setup 但没 git init
    run bash "$CLI" upgrade
    [ "$status" -eq 1 ]
    [[ "$output" == *"is not a git clone"* ]]
}

@test "CLI-501: upgrade 在非 main 分支 → die (保护 dev 仓)" {
    cd "$SPECFORGE_HOME"
    git init -q .
    git -c init.defaultBranch=main checkout -q -b main 2>/dev/null || git checkout -q -b main
    git -c user.email=t@t.com -c user.name=t commit -q --allow-empty -m init
    git checkout -q -b feature/my-dev
    run bash "$CLI" upgrade
    [ "$status" -eq 1 ]
    [[ "$output" == *"refusing to upgrade on branch 'feature/my-dev'"* ]]
    # main 是唯一允许的分支
    [[ "$output" == *"only main is supported"* ]]
}

@test "CLI-502: upgrade 在 main 分支且 origin 缺失 → fetch 失败" {
    cd "$SPECFORGE_HOME"
    git init -q .
    git -c init.defaultBranch=main checkout -q -b main 2>/dev/null || git checkout -q -b main
    # 没有 origin,fetch 会失败 → die
    run bash "$CLI" upgrade
    [ "$status" -ne 0 ]
}

# ---------- SPECFORGE_HOME 行为 ----------

@test "CLI-600: SPECFORGE_HOME 优先于默认值" {
    export SPECFORGE_HOME="$TEST_DIR/custom-home"
    mkdir -p "$SPECFORGE_HOME/agents" "$SPECFORGE_HOME/templates"
    echo "9.9.9" > "$SPECFORGE_HOME/VERSION"
    run bash "$CLI" version
    [ "$status" -eq 0 ]
    [[ "$output" == *"9.9.9"* ]]
    [[ "$output" == *"$TEST_DIR/custom-home"* ]]
}

@test "CLI-601: dev 模式 (SPECFORGE_HOME=.) 可直接 init" {
    # 模拟"开发者在 specforge repo 内直接跑 bin/specforge"
    cd "$REPO_ROOT"
    SPECFORGE_HOME=. run bash "$CLI" init "$TEST_DIR/from-dev"
    [ "$status" -eq 0 ]
    [ -d "$TEST_DIR/from-dev/agents" ]
}

# ---------- install.sh 单源一致性 ----------

@test "CLI-700: install.sh 语法合法" {
    run bash -n "$REPO_ROOT/install.sh"
    [ "$status" -eq 0 ]
}

@test "CLI-701: install.sh 不内联 specforge 函数体 (单源: 复制 bin/specforge)" {
    # 真正实现 install 时是从 $SPECFORGE_HOME/bin/specforge 复制到 $BIN_DIR
    # 旧版会把 specforge 脚本 inline 在 install.sh 里 — 不允许
    # grep -F 'cmd_checkup()' 应该 0 个匹配
    run grep -F 'cmd_checkup()' "$REPO_ROOT/install.sh"
    [ "$status" -ne 0 ]
    # 也不应内联 cmd_init
    run grep -F 'cmd_init()' "$REPO_ROOT/install.sh"
    [ "$status" -ne 0 ]
    # 不应内联 cmd_help
    run grep -F 'cmd_help()' "$REPO_ROOT/install.sh"
    [ "$status" -ne 0 ]
    # 应有 cp 命令把 repo 里的 bin/specforge 复制到 $BIN_DIR
    run grep -F 'cp "$SPECFORGE_HOME/bin/specforge"' "$REPO_ROOT/install.sh"
    [ "$status" -eq 0 ]
}
