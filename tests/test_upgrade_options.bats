#!/usr/bin/env bats
# 测试 v0.6-009+ 增补: lk upgrade 支持 --index / --pre / --dry-run

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

# 使用 PYTHONPATH 让 lk 用本地源码 (避免 venv 装旧版)
LK_BIN="/Users/aaronyang/.local/bin/lk"

setup() {
    export PYTHONPATH="$REPO_ROOT"
}

teardown() {
    rm -f /tmp/louke_upgrade_test_*
}

@test "lk upgrade --help 显示新选项" {
    run "$LK_BIN" upgrade --help
    [ "$status" -eq 0 ]
    [[ "$output" == *"--index"* ]]
    [[ "$output" == *"--pre"* ]]
    [[ "$output" == *"--dry-run"* ]]
}

@test "lk upgrade --dry-run 不实际执行 pip" {
    run "$LK_BIN" upgrade --dry-run
    [ "$status" -eq 0 ]
    [[ "$output" == *"Running:"* ]]
    [[ "$output" == *"pip install --upgrade louke"* ]]
    # 不应该有 'Successfully installed' 输出
    [[ ! "$output" == *"Successfully installed"* ]]
}

@test "lk upgrade --dry-run --index URL 翻译为 pip --index-url" {
    run "$LK_BIN" upgrade --dry-run --index https://test.pypi.org/simple/
    [ "$status" -eq 0 ]
    [[ "$output" == *"--index-url https://test.pypi.org/simple/"* ]]
}

@test "lk upgrade --dry-run --pre 加 --pre 标志" {
    run "$LK_BIN" upgrade --dry-run --pre
    [ "$status" -eq 0 ]
    [[ "$output" == *"--pre"* ]]
}

@test "lk upgrade --dry-run --index URL --pre 同时加两个标志" {
    run "$LK_BIN" upgrade --dry-run --index https://example.com/pypi/ --pre
    [ "$status" -eq 0 ]
    [[ "$output" == *"--index-url https://example.com/pypi/"* ]]
    [[ "$output" == *"--pre"* ]]
}

@test "lk upgrade 未知选项原样转发给 pip" {
    # pip 自身的 --force-reinstall 选项应原样透传
    run "$LK_BIN" upgrade --dry-run --force-reinstall
    [ "$status" -eq 0 ]
    [[ "$output" == *"--force-reinstall"* ]]
    # 我们的 louke-level 选项不应被加
    [[ ! "$output" == *"--index-url"* ]]
}
