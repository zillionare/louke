#!/usr/bin/env bash
# louke installer — project-local + user-global runtimes
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/zillionare/louke/main/install.sh | bash
#   curl -sSL ... | bash -s -- v0.1.0         # specify a version
#   curl -sSL ... | bash -s -- --editable     # dev mode (clone from GitHub then pip install -e)
#   ./install.sh [version]                    # run locally

set -euo pipefail

note() { echo "louke: $*" >&2; }
die()  { note "error: $*"; exit 1; }

# ---------- Platform support ----------
# This installer has only been tested on macOS / Linux.
# Windows users should use WSL2 or Docker, or report at https://github.com/zillionare/louke/issues.
case "$(uname -s 2>/dev/null || echo unknown)" in
    Darwin|Linux) ;;
    MINGW*|MSYS*|CYGWIN*) {
        echo "louke installer does not support native Windows." >&2
        echo "Use the native install.bat or install.ps1 entry point instead." >&2
        exit 1
    } ;;
    *) echo "louke: unrecognized platform $(uname -s); continuing best-effort" >&2 ;;
esac

# ---------- Parse args: VERSION may be positional or passed as --version ----------
EDITABLE=0
VERSION="latest"
while [ "$#" -gt 0 ]; do
    arg="$1"
    case "$arg" in
        --editable|-e)
            EDITABLE=1
            shift
            ;;
        --version|-v)
            [ "$#" -ge 2 ] || die "${arg} requires a version"
            VERSION="$2"
            shift 2
            ;;
        -h|--help)
            echo "usage: $0 [--editable|-e] [--version VERSION|version]" >&2
            exit 0
            ;;
        --)
            shift
            [ "$#" -gt 0 ] && VERSION="$1"
            shift || true
            ;;
        -*) die "unknown flag: $arg" ;;
        *)
            VERSION="$arg"
            shift
            ;;
    esac
done

REPO_URL="https://github.com/zillionare/louke.git"
PROJECT_VENV="${PWD}/.venv"
GLOBAL_VENV="${HOME}/.louke/venv"
BIN_DIR="${HOME}/.local/bin"

# ---------- Pre-check ----------
command -v python3 >/dev/null 2>&1 || die "python3 not found. install Python 3.11+ first."

# Prefer the highest compatible interpreter exposed by the host. The plain
# python3 check above is intentional: the public contract promises an
# actionable error when that command is unavailable.
PYTHON_BIN=""
PYTHON_MINOR=0
for candidate in python3.14 python3.13 python3.12 python3.11 python3; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    version="$($candidate -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)"
    minor="${version#*.}"
    case "$version" in
        3.*) ;;
        *) continue ;;
    esac
    if [ "${minor:-0}" -ge 11 ] 2>/dev/null && [ "${minor:-0}" -gt "$PYTHON_MINOR" ]; then
        PYTHON_BIN="$(command -v "$candidate")"
        PYTHON_MINOR="$minor"
    fi
done
[ -n "$PYTHON_BIN" ] || die "Python 3.11+ required (found $(python3 -V 2>&1))"

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

# ---------- Create both runtimes + install louke ----------
install_runtime() {
    local venv_dir="$1"
    if [ ! -d "$venv_dir" ]; then
        note "creating venv at $venv_dir"
        "$PYTHON_BIN" -m venv "$venv_dir"
    fi
    [ -x "$venv_dir/bin/python" ] || die "venv Python not found at $venv_dir/bin/python"
    note "installing $PKG_SPEC into $venv_dir"
    "$venv_dir/bin/python" -m pip install --quiet --upgrade pip
    "$venv_dir/bin/python" -m pip install --quiet --upgrade "$PKG_SPEC"
    "$venv_dir/bin/python" -c 'import louke' || die "louke import failed in $venv_dir"
}

install_runtime "$PROJECT_VENV"
install_runtime "$GLOBAL_VENV"

runtime_package_version() {
    "$1" -c 'import importlib.metadata; print(importlib.metadata.version("louke"))'
}

PROJECT_PACKAGE_VERSION="$(runtime_package_version "$PROJECT_VENV/bin/python")"
GLOBAL_PACKAGE_VERSION="$(runtime_package_version "$GLOBAL_VENV/bin/python")"
[ -n "$PROJECT_PACKAGE_VERSION" ] || die "could not verify project-local louke version"
[ "$PROJECT_PACKAGE_VERSION" = "$GLOBAL_PACKAGE_VERSION" ] || die "runtime version mismatch: local=$PROJECT_PACKAGE_VERSION global=$GLOBAL_PACKAGE_VERSION"
if [ "$VERSION" != "latest" ] && [ "$EDITABLE" -eq 0 ] && [ "$PROJECT_PACKAGE_VERSION" != "$VERSION" ]; then
    die "requested louke $VERSION but installed $PROJECT_PACKAGE_VERSION"
fi

# ---------- Install a strict-CWD local-first shim ----------
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/lk" <<'SHIM'
#!/usr/bin/env bash
set -e
if [ -x "$PWD/.venv/bin/python" ]; then
    export LOUKE_RUNTIME_MODE=local
    exec "$PWD/.venv/bin/python" -m louke "$@"
fi
if [ -x "$HOME/.louke/venv/bin/python" ]; then
    export LOUKE_RUNTIME_MODE=global
    exec "$HOME/.louke/venv/bin/python" -m louke "$@"
fi
echo "no louke runtime found; run install.sh / install.bat / lk install first" >&2
exit 1
SHIM
chmod +x "$BIN_DIR/lk"
note "installed local-first shim at $BIN_DIR/lk"

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
note "louke ${PROJECT_PACKAGE_VERSION} installed at $PROJECT_VENV"
note "global runtime installed at $GLOBAL_VENV"
note ""
note "next steps:"
note "  1. restart your shell, or:    export PATH=\"${BIN_DIR}:\$PATH\""
note "  2. verify install:             lk --help"
note "  3. check identity:             lk agent scout identity-check --repo OWNER/REPO"
note "  4. read the manual:            lk --help <agent>"
note ""
note "uninstall:  rm -rf $PROJECT_VENV $GLOBAL_VENV $BIN_DIR/lk"
