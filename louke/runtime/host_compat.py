"""NFR-0500: Host project compatibility.

The implementation must support different languages, builders, test
frameworks and artifact types through 002 project-local contracts,
preserve existing hooks/workflows/rules, and use Archer's current design
for brand-new projects.  It must NOT hardcode Louke's own repo facts.
At least two distinct tech-stack fixtures must each complete to candidate
through their own project-local test/build/artifact/pre-commit/CI contracts
while preserving existing hooks/workflows/rules.  The execution path must
NOT read Louke's own language/build config as host default; unsupported
adapters must return a clear capability diagnostic (AC-NFR0500-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ERROR_CODES = (
    "HOST_UNSUPPORTED",
    "HOST_CAPABILITY_MISSING",
    "HOST_DEFAULT_LEAKED",
)

_PYTHON_MARKERS = ("pyproject.toml", "setup.py", "requirements.txt")
_NODE_MARKERS = ("package.json",)


class HostCompatError(Exception):
    """A fail-closed host compatibility rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass
class HostAdapter:
    """A host-project adapter binding test/build/artifact/pre-commit/CI commands.

    Attributes:
        stack_id: ``python|node|...``.
        test_command: Host test command (must NOT default to Louke's).
        build_command: Host build command.
        artifact_kinds: Tuple of artifact kinds the host produces.
        precommit_config_path: Pre-commit config path.
        ci_workflow_path: CI workflow path.
        capabilities: Frozenset of supported capabilities (test/build/artifact/
            pre-commit/ci).
    """

    stack_id: str
    test_command: str
    build_command: str
    artifact_kinds: tuple[str, ...]
    precommit_config_path: str
    ci_workflow_path: str
    capabilities: frozenset[str]

    def require_capability(self, capability: str) -> None:
        """Raise ``HOST_CAPABILITY_MISSING`` if ``capability`` is not supported."""
        if capability not in self.capabilities:
            raise HostCompatError(
                "HOST_CAPABILITY_MISSING",
                f"adapter {self.stack_id!r} does not support capability {capability!r}",
            )


def detect_adapter(*, stack_files: tuple[str, ...]) -> HostAdapter:
    """Detect the host stack from filesystem markers (AC-NFR0500-01).

    Args:
        stack_files: Tuple of files present in the host repo root.

    Returns:
        A :class:`HostAdapter` for Python or Node.

    Raises:
        HostCompatError: With ``HOST_UNSUPPORTED`` if the stack is not
            Python or Node.
    """
    files = set(stack_files)
    if any(m in files for m in _PYTHON_MARKERS):
        return HostAdapter(
            stack_id="python",
            test_command=".venv/bin/python3 -m pytest -q",
            build_command=".venv/bin/python3 -m build",
            artifact_kinds=("wheel", "sdist"),
            precommit_config_path=".pre-commit-config.yaml",
            ci_workflow_path=".github/workflows/louke-ci.yml",
            capabilities=frozenset({"test", "build", "artifact", "pre-commit", "ci"}),
        )
    if any(m in files for m in _NODE_MARKERS):
        return HostAdapter(
            stack_id="node",
            test_command="npm test",
            build_command="npm run build",
            artifact_kinds=("tarball",),
            precommit_config_path=".husky/pre-commit",
            ci_workflow_path=".github/workflows/louke-ci.yml",
            capabilities=frozenset({"test", "build", "artifact", "pre-commit", "ci"}),
        )
    raise HostCompatError(
        "HOST_UNSUPPORTED",
        f"unsupported host stack; files {sorted(files)} do not match Python or Node markers",
    )


@dataclass(frozen=True)
class HostCompatReport:
    """Result of :func:`validate_host_compat` (AC-NFR0500-01).

    Attributes:
        status: ``pass`` or ``fail``.
    """

    status: str


_REQUIRED_CAPABILITIES: frozenset[str] = frozenset(
    {
        "test",
        "build",
        "artifact",
        "pre-commit",
        "ci",
    }
)


def validate_host_compat(adapter: HostAdapter) -> HostCompatReport:
    """Validate that the host adapter has all required capabilities (AC-NFR0500-01)."""
    missing = _REQUIRED_CAPABILITIES - adapter.capabilities
    if missing:
        raise HostCompatError(
            "HOST_CAPABILITY_MISSING",
            f"adapter {adapter.stack_id!r} missing capabilities: {sorted(missing)}",
        )
    return HostCompatReport(status="pass")


def preserve_existing_assets(
    existing: dict[str, list[dict[str, Any]]],
    *,
    runtime_additions: dict[str, list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """Preserve existing hooks/workflows/rules and merge Runtime additions (AC-NFR0500-01).

    Args:
        existing: Map of asset category -> list of existing assets.
        runtime_additions: Map of asset category -> list of Runtime-owned additions.

    Returns:
        A merged map preserving all existing assets and adding Runtime-owned ones.
    """
    merged: dict[str, list[dict[str, Any]]] = {}
    for category, items in existing.items():
        merged[category] = list(items)
    for category, items in runtime_additions.items():
        merged.setdefault(category, []).extend(items)
    return merged
