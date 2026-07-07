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
__version__ = "0.6.14"

# v0.6-009 NFR-0040: minimum OpenCode version (Qwen A-8.4 calibration)
# The permission object format (replacing the deprecated tools field) was
# introduced in OpenCode v1.1.1
MIN_OPENCODE_VERSION = "1.1.1"
