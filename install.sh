#!/usr/bin/env bash
# louke installer — pip-based
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/zillionare/louke/main/install.sh | bash
#   curl -sSL ... | bash -s -- v0.1.0         # specify a version
#   curl -sSL ... | bash -s -- --editable     # dev mode (clone from GitHub then pip install -e)
#   ./install.sh [version]                    # run locally

set -euo pipefail

# ---------- Platform support ----------
# This installer has only been tested on macOS / Linux.
# Windows users should use WSL2 or Docker, or report at https://github.com/zillionare/louke/issues.
case "$(uname -s 2>/dev/null || echo unknown)" in
    Darwin|Linux) ;;
    MINGW*|MSYS*|CYGWIN*) {
        echo "louke installer does not support native Windows." >&2
        echo "Use WSL2 (https://docs.microsoft.com/en-us/windows/wsl/) or Docker." >&2
        exit 1
    } ;;
    *) echo "louke: unrecognized platform $(uname -s); continuing best-effort" >&2 ;;
esac

# ---------- Parse args: the first non-flag is VERSION, --editable / -e is a flag ----------
EDITABLE=0
VERSION="latest"
for arg in "$@"; do
    case "$arg" in
        --editable|-e) EDITABLE=1 ;;
        -h|--help)
            echo "usage: $0 [--editable|-e] [version]" >&2
            exit 0
            ;;
        --) shift; break ;;
        -*) echo "louke: unknown flag: $arg" >&2; exit 1 ;;
        *)  VERSION="$arg" ;;
    esac
done

REPO_URL="https://github.com/zillionare/louke.git"
VENV_DIR="${HOME}/.louke/venv"
BIN_DIR="${HOME}/.local/bin"

note() { echo "louke: $*" >&2; }
die()  { note "error: $*"; exit 1; }

# ---------- Pre-check ----------
command -v python3 >/dev/null 2>&1 || die "python3 not found. install Python 3.9+ first."
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
[ "$PY_MINOR" -ge 9 ] 2>/dev/null || die "Python 3.9+ required (found $(python3 -V 2>&1))"

# ---------- Decide install source ----------
if [ "$EDITABLE" -eq 1 ]; then
    # git clone mode
    LOUKE_HOME="${HOME}/.louke/src"
    if [ -d "$LOUKE_HOME" ]; then
        note "updating existing checkout at $LOUKE_HOME"
        git -C "$LOUKE_HOME" pull --ff-only
    else
        # latest → default branch (main), do not pass --branch
        if [ "$VERSION" = "latest" ]; then
            note "cloning louke (default branch) into $LOUKE_HOME"
            git clone --depth 1 "$REPO_URL" "$LOUKE_HOME"
        else
            note "cloning louke ($VERSION) into $LOUKE_HOME"
            git clone --depth 1 --branch "$VERSION" "$REPO_URL" "$LOUKE_HOME"
        fi
    fi
    PKG_SPEC="$LOUKE_HOME"
elif [ "$VERSION" = "latest" ]; then
    PKG_SPEC="louke"
else
    PKG_SPEC="louke==$VERSION"
fi

# ---------- Create venv ----------
if [ ! -d "$VENV_DIR" ]; then
    note "creating venv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# ---------- Upgrade pip + install louke ----------
note "installing $PKG_SPEC into $VENV_DIR"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet --upgrade "$PKG_SPEC"

# ---------- Link lk into ~/.local/bin ----------
mkdir -p "$BIN_DIR"
ln -sf "$VENV_DIR/bin/lk" "$BIN_DIR/lk"
note "linked $BIN_DIR/lk -> $VENV_DIR/bin/lk"

# ---------- Persist PATH ----------
# Detect the user's primary shell rc file by $SHELL, not by blind file-existence checks
SHELL_NAME="$(basename "${SHELL:-bash}")"
case "$SHELL_NAME" in
    zsh)  SHELL_RC="${HOME}/.zshrc" ;;
    bash)
        # Linux bash usually reads .bashrc; macOS bash reads .bash_profile (login) or .bashrc (interactive non-login)
        if [ -f "${HOME}/.bashrc" ]; then SHELL_RC="${HOME}/.bashrc"
        elif [ -f "${HOME}/.bash_profile" ]; then SHELL_RC="${HOME}/.bash_profile"
        else SHELL_RC="${HOME}/.bashrc"; fi
        ;;
    fish) SHELL_RC="${HOME}/.config/fish/config.fish" ;;
    *)    SHELL_RC="${HOME}/.profile" ;;
esac
if [ -n "$SHELL_RC" ] && [ -w "$(dirname "$SHELL_RC")" ] && ! grep -q "${BIN_DIR}" "$SHELL_RC" 2>/dev/null; then
    {
        echo ""
        echo "# louke CLI"
        if [ "$SHELL_NAME" = "fish" ]; then
            echo "set -gx PATH ${BIN_DIR} \$PATH"
        else
            echo "export PATH=\"${BIN_DIR}:\$PATH\""
        fi
    } >> "$SHELL_RC"
    note "added ${BIN_DIR} to PATH in $SHELL_RC"
fi

# ---------- Verify ----------
INSTALLED_VERSION="$("$VENV_DIR/bin/lk" --version 2>/dev/null || echo '?')"
note "louke ${INSTALLED_VERSION} installed at $VENV_DIR"
note ""
note "next steps:"
note "  1. restart your shell, or:    export PATH=\"${BIN_DIR}:\$PATH\""
note "  2. verify install:             lk --help"
note "  3. check identity:             lk agent scout identity-check --repo OWNER/REPO"
note "  4. read the manual:            lk --help <agent>"
note ""
note "uninstall:  rm -rf $VENV_DIR $BIN_DIR/lk"
