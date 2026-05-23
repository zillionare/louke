#!/usr/bin/env bash
set -euo pipefail

SPECFORGE_HOME="${HOME}/.specforge"
REPO_URL="https://github.com/zillionare/specforge.git"
VERSION="${1:-main}"

if [ -d "$SPECFORGE_HOME" ]; then
    echo "specforge is already installed at $SPECFORGE_HOME"
    echo "To reinstall, run: rm -rf $SPECFORGE_HOME && curl -sSL https://raw.githubusercontent.com/zillionare/specforge/main/install.sh | bash"
    exit 1
fi

echo "Installing specforge into $SPECFORGE_HOME ..."
git clone --depth 1 --branch "$VERSION" "$REPO_URL" "$SPECFORGE_HOME"

BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"

cat > "${BIN_DIR}/specforge" << 'SCRIPT'
#!/usr/bin/env bash
SPECFORGE_HOME="${HOME}/.specforge"
case "${1:-}" in
    init)
        PROJECT_NAME="${2:-}"
        if [ -z "$PROJECT_NAME" ]; then
            echo "Usage: specforge init <project-name>"
            exit 1
        fi
        if [ -d "$PROJECT_NAME" ]; then
            echo "Directory '$PROJECT_NAME' already exists."
            exit 1
        fi
        mkdir -p "$PROJECT_NAME"/{agents,templates,specs,wiki/entries,wiki/decisions}
        cp "$SPECFORGE_HOME"/agents/*.md "$PROJECT_NAME/agents/"
        cp "$SPECFORGE_HOME"/templates/*.md "$PROJECT_NAME/templates/"
        cp "$SPECFORGE_HOME"/agents/ROSTER.md "$PROJECT_NAME/agents/"
        cat << 'ONBOARD'
specforge project '$PROJECT_NAME' initialized!

  项目目录: $(pwd)/$PROJECT_NAME
  Agent 目录: $PROJECT_NAME/agents/  (21 个 Agent)
  模板目录:   $PROJECT_NAME/templates/ (8 个模板)
  Wiki 目录:  $PROJECT_NAME/wiki/

  下一步:
  1. cd $PROJECT_NAME
  2. 调用 Guide Agent 了解如何使用:
     用你的 AI 工具加载 agents/Guide.md 的 prompt，然后问 "我该如何开始？"
  3. 如果你已有所需功能的想法，调用 Scout Agent:
     加载 agents/Scout.md → 告诉它你要做什么

  推荐模型（国内版）:
    S 档 (深度推理): deepseek-v4-pro  → Sage, Forge, Hunter
    A 档 (综合规划): kimi-k2.6        → Maestro, Archer, Probe
    A-档 (稳定编码): qwen3.6-plus     → Lex, Judge
    C 档 (快速检查): deepseek-v4-flash → Warden, Keeper, Shield

  详细模型映射见: agents/README.md
ONBOARD
        ;;
    *)
        echo "specforge v1.0.0"
        echo "Usage: specforge init <project-name>"
        exit 0
        ;;
esac
SCRIPT

chmod +x "${BIN_DIR}/specforge"

SHELL_RC=""
if [ -f "${HOME}/.zshrc" ]; then SHELL_RC="${HOME}/.zshrc"; fi
if [ -f "${HOME}/.bashrc" ]; then SHELL_RC="${HOME}/.bashrc"; fi

if [ -n "$SHELL_RC" ] && ! grep -q "${BIN_DIR}" "$SHELL_RC" 2>/dev/null; then
    echo "export PATH=\"${BIN_DIR}:\$PATH\"" >> "$SHELL_RC"
    echo "Added ${BIN_DIR} to PATH in $SHELL_RC"
fi

echo ""
echo "specforge installed successfully!"
echo "Restart your shell or run: export PATH=\"${BIN_DIR}:\$PATH\""
echo "Then try: specforge init my-first-project"
