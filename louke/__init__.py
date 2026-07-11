"""lk - louke CLI.

Unified entry point. Each agent has its own entry file (louke/{agent}.py); agent
prompts are invoked via `lk <agent> {command} [--args]`, avoiding raw bash
multi-step commands in agents/*.md.

Design principles:
1. One entry file per agent (louke/{agent}.py)
2. Agents do not call low-level scripts directly; they go through `lk <agent>`
3. Multi-step commands are wrapped into a single `lk` command to reduce errors
4. Subcommands may use subprocess to call low-level tools (louke/_tools/*.py),
   or implement new logic inline
5. Exit codes follow Unix convention: 0 = success, non-zero = failure
"""

__version__: str
try:
    # Read the installed package version from wheel METADATA so the
    # hardcoded constant can't drift from the released version.
    # Falls back to the literal below only if importlib.metadata
    # is unavailable (very old Python) or the package is being
    # imported from a source tree without an installed distribution.
    from importlib.metadata import version as _pkg_version, PackageNotFoundError

    try:
        __version__ = _pkg_version("louke")
    except PackageNotFoundError:
        __version__ = "0.0.0+unknown"
except ImportError:  # pragma: no cover
    __version__ = "0.0.0+unknown"

# v0.6-009 NFR-0040: minimum OpenCode version (Qwen A-8.4 calibration)
# The permission object format (replacing the deprecated tools field) was
# introduced in OpenCode v1.1.1
MIN_OPENCODE_VERSION = "1.1.1"

# NFR-0201: workspace security sandbox module registration
from . import security  # noqa: E402,F401

# FR-0401: canonical .louke directory layout module registration
from . import paths  # noqa: E402,F401

from . import opencode, opencode_api  # noqa: E402,F401
