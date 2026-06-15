#!/usr/bin/env bash
# install_vscode_agents.sh
# 把 specforge agents 安装为 VS Code custom agent (.github/agents/*.agent.md)
# 用法: bash tools/install_vscode_agents.sh
# 每个开发者只需跑一次, .github/agents/ 已在 .gitignore 中

set -euo pipefail

AGENT_SOURCE="agents"
AGENT_TARGET=".github/agents"

if [ ! -d "$AGENT_SOURCE" ]; then
    echo "❌ 未找到 $AGENT_SOURCE/ 目录,请在 specforge 项目根目录运行此脚本"
    exit 1
fi

if [ ! -d ".git" ]; then
    echo "❌ 未找到 .git 目录,请在 specforge 项目根目录运行此脚本"
    exit 1
fi

mkdir -p "$AGENT_TARGET"

count=0
for f in "$AGENT_SOURCE"/*.md; do
    [ -f "$f" ] || continue
    base=$(basename "$f" .md)
    target="$AGENT_TARGET/${base}.agent.md"
    # 相对路径: .github/agents/X.agent.md → ../../agents/X.md
    ln -snf "../../$f" "$target"
    echo "  ✅ $target → ../../$f"
    count=$((count + 1))
done

echo ""
echo "完成: $count 个 agent 已安装到 $AGENT_TARGET/"
echo "重启 VS Code (Reload Window) 后即可在 Chat 面板看到 @lex @sage @scout 等 agent"
