#!/usr/bin/env bash
# specforge installer
# 用法: curl -sSL https://raw.githubusercontent.com/zillionare/specforge/main/install.sh | bash
# 或:   ./install.sh [version]   (version 默认 main)

set -euo pipefail

SPECFORGE_HOME="${HOME}/.specforge"
REPO_URL="https://github.com/zillionare/specforge.git"
VERSION="${1:-main}"
BIN_DIR="${HOME}/.local/bin"

note() { echo "specforge: $*" >&2; }

if [ -d "$SPECFORGE_HOME" ]; then
    note "specforge is already installed at $SPECFORGE_HOME"
    note "to reinstall, run:"
    note "  rm -rf $SPECFORGE_HOME && curl -sSL https://raw.githubusercontent.com/zillionare/specforge/main/install.sh | bash"
    note "to upgrade in place, run:"
    note "  $BIN_DIR/specforge upgrade"
    exit 1
fi

note "installing specforge ($VERSION) into $SPECFORGE_HOME ..."
git clone --depth 1 --branch "$VERSION" "$REPO_URL" "$SPECFORGE_HOME"

# 把 repo 自带的 bin/specforge 软链接/复制到用户 PATH
# 注意:不能用 --depth 1 的 repo 做开发,只是 install 用途。
mkdir -p "$BIN_DIR"
cp "$SPECFORGE_HOME/bin/specforge" "$BIN_DIR/specforge"
chmod +x "$BIN_DIR/specforge"

# PATH 持久化
SHELL_RC=""
if [ -f "${HOME}/.zshrc" ]; then SHELL_RC="${HOME}/.zshrc"; fi
if [ -f "${HOME}/.bashrc" ]; then SHELL_RC="${HOME}/.bashrc"; fi
if [ -n "$SHELL_RC" ] && ! grep -q "${BIN_DIR}" "$SHELL_RC" 2>/dev/null; then
    echo "export PATH=\"${BIN_DIR}:\$PATH\"" >> "$SHELL_RC"
    note "added ${BIN_DIR} to PATH in $SHELL_RC"
fi

INSTALLED_VERSION="$(cat "$SPECFORGE_HOME/VERSION" 2>/dev/null || echo "?")"
note "specforge $INSTALLED_VERSION installed at $SPECFORGE_HOME"
note ""
note "next steps:"
note "  1. restart your shell, or:  export PATH=\"${BIN_DIR}:\$PATH\""
note "  2. verify install:           specforge version"
note "  3. check identity:           specforge checkup OWNER/REPO"
note "  4. create your first project: specforge init my-project"
note "  5. read the manual:          cat $SPECFORGE_HOME/agents/README.md"
