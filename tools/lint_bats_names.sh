#!/usr/bin/env bash
# lint_bats_names.sh — 拒绝任何含非 ASCII 字符的 bats test 名
# 防止 silent skip bug 复发 (bats 在 zh_CN / C.UTF-8 locale 下解析多字节 test 名会 skip)
#
# 用法:
#   bash tools/lint_bats_names.sh tests/*.bats
#   bash tools/lint_bats_names.sh tests/test_xxx.bats
#
# 退出码:
#   0 — 所有 test 名 ASCII
#   1 — 至少一个 test 名含非 ASCII 字符
#
# 实现: 扫所有 @test "<NAME>" 行, 提取 <NAME>, 检查每个字节是否在 0x00-0x7F.
# ADR 008: https://...decisions/008-bats-test-name-convention.md

set -u

if [ $# -eq 0 ]; then
    echo "usage: $0 <bats_file> [bats_file...]" >&2
    exit 2
fi

violations=0
files_scanned=0

for f in "$@"; do
    [ -f "$f" ] || { echo "WARN: $f not found, skipping" >&2; continue; }
    files_scanned=$((files_scanned + 1))

    # 提取 @test "<NAME>" 行. NAME 假设不含未转义双引号 (bats 本身限制).
    # 用 grep -n 拿行号方便定位.
    while IFS= read -r line; do
        [ -z "$line" ] && continue
        # 拆 file:lineno:"@test_name" 格式
        file=$(echo "$line" | cut -d: -f1)
        lineno=$(echo "$line" | cut -d: -f2)
        # 拿 @test "..." 之间的内容 (第 3 列起, 去掉前缀 @test ")
        name=$(echo "$line" | sed -nE 's/^[0-9]+:[[:space:]]*@test[[:space:]]+"(.*)"[[:space:]]*\{?[[:space:]]*$/\1/p')
        [ -z "$name" ] && continue

        # 检查每个字节是否 ASCII (0x00-0x7F)
        # LC_ALL=C 保证 byte-level 比较
        if echo "$name" | LC_ALL=C grep -q '[^[:print:][:space:]]'; then
            echo "FAIL: $file:$lineno — test name contains non-ASCII bytes:"
            echo "      raw: $name"
            violations=$((violations + 1))
        fi
    done < <(LC_ALL=C grep -nE '^[[:space:]]*@test[[:space:]]+' "$f" 2>/dev/null)
done

if [ "$violations" -gt 0 ]; then
    echo ""
    echo "✗ $violations non-ASCII bats test name(s) found in $files_scanned file(s)"
    echo "  See ADR 008: bats test names must be ASCII ([a-zA-Z0-9_-:] only)"
    echo "  Chinese descriptions are OK as ## comments after @test, not in the name itself"
    exit 1
fi

echo "✓ all bats test names in $files_scanned file(s) are ASCII"
exit 0