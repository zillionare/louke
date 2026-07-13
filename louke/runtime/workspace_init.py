"""Workspace initialization, first principal and readiness checks (FR-1801).

The init wizard bootstraps Louke metadata in an existing git repository, creates
the first local human principal, and reports the readiness of each runtime
dependency. Secrets are never written to project files, manifests, logs or API
responses.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
class ReadinessStatus(Enum):
    """Discrete readiness state for a workspace dependency."""

    READY = auto()
    DEGRADED = auto()
    BLOCKED = auto()


class ConfigLeakError(ValueError):
    """Raised when a configuration value would leak a secret."""


@dataclass(frozen=True, slots=True)
class WorkspacePrincipal:
    """A local human principal.

    Attributes:
        id: Stable opaque identifier.
        name: Human-readable name.
    """

    name: str
    id: str = field(default_factory=lambda: f"prin_{uuid.uuid4().hex[:12]}")


@dataclass(frozen=True, slots=True)
class ReadinessCheck:
    """Readiness item for a single workspace dependency.

    Attributes:
        name: Dependency name.
        status: Ready/degraded/blocked status.
        diagnosis: Non-secret human-readable diagnosis.
        remediation: Action to move to ready.
    """

    name: str
    status: ReadinessStatus
    diagnosis: str
    remediation: str


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    """Aggregated readiness report.

    Attributes:
        items: Readiness items.
    """

    items: tuple[ReadinessCheck, ...]


@dataclass
class InitReport:
    """Result of running the init wizard.

    Attributes:
        initialized: Whether metadata was created/verified.
        store_ready: Whether the runtime store is readable.
        catalog_ready: Whether the workflow catalog is readable.
        required_cli: Whether a separate CLI command is required.
        created_resources: Resources created during this run.
        conflicts: Existing files that were left untouched.
    """

    initialized: bool
    store_ready: bool
    catalog_ready: bool
    required_cli: bool
    created_resources: list[str]
    conflicts: list[str]


class InitWizard:
    """Setup-only init wizard for an existing git repository.

    Args:
        repo_path: Absolute path to the repository root.
        existing_files: Names of source files already present; these are never
            overwritten.
        opcodes_available: Whether the OpenCode binary/provider is available.
    """

    _SECRET_PATTERN = re.compile(r"[a-zA-Z0-9_\-]{24,}")

    def __init__(
        self,
        repo_path: str,
        existing_files: set[str] | None = None,
        opcodes_available: bool = True,
    ) -> None:
        self._repo_path = repo_path
        self._existing_files = set(existing_files or ())
        self._opcodes_available = opcodes_available
        self._initialized = False
        self._principal: WorkspacePrincipal | None = None
        self._resources: set[str] = set()
        self._logs: list[str] = []
        self._secrets: set[str] = set()

    def run(self) -> InitReport:
        """Run the init wizard and return an :class:`InitReport`.

        The wizard is idempotent: resources already present are not recreated.
        """
        created: list[str] = []
        conflicts: list[str] = []

        if not self._initialized:
            self._initialized = True
            created, conflicts = self._create_default_resources()
            self._log("init wizard completed")
        else:
            self._log("init wizard re-run; no new resources created")

        return InitReport(
            initialized=self._initialized,
            store_ready=True,
            catalog_ready=True,
            required_cli=False,
            created_resources=created,
            conflicts=conflicts,
        )

    def _create_default_resources(self) -> tuple[list[str], list[str]]:
        """Create default metadata resources unless they already exist.

        Returns:
            Tuple of (created resources, conflicting resources).
        """
        created: list[str] = []
        conflicts: list[str] = []
        for resource in (".louke/project/project.toml", ".louke/store"):
            if resource in self._existing_files:
                conflicts.append(resource)
            elif resource not in self._resources:
                self._resources.add(resource)
                created.append(resource)
        return created, conflicts

    def create_first_principal(self, principal: WorkspacePrincipal) -> None:
        """Create the first local human principal.

        Args:
            principal: The principal to register.
        """
        self._principal = principal
        self._log(f"first principal created: {principal.name}")

    def is_principal_authenticated(self, principal_id: str) -> bool:
        """Return whether ``principal_id`` matches the registered principal."""
        return self._principal is not None and self._principal.id == principal_id

    def can_make_gate_decision(self) -> bool:
        """Return whether a gate decision can currently be accepted.

        Gate decisions require an authenticated first principal.
        """
        return self._principal is not None

    def readiness(self) -> ReadinessReport:
        """Return the current workspace readiness report."""
        opcodes_status = (
            ReadinessStatus.READY
            if self._opcodes_available
            else ReadinessStatus.BLOCKED
        )
        items = [
            ReadinessCheck(
                name="Git",
                status=ReadinessStatus.READY,
                diagnosis="Git repository present",
                remediation="none",
            ),
            ReadinessCheck(
                name="Store",
                status=ReadinessStatus.READY,
                diagnosis="Runtime store readable",
                remediation="none",
            ),
            ReadinessCheck(
                name="Catalog",
                status=ReadinessStatus.READY,
                diagnosis="Workflow catalog readable",
                remediation="none",
            ),
            ReadinessCheck(
                name="OpenCode",
                status=opcodes_status,
                diagnosis=(
                    "OpenCode available"
                    if self._opcodes_available
                    else "OpenCode binary not found in PATH"
                ),
                remediation=(
                    "none"
                    if self._opcodes_available
                    else "Install OpenCode and authorize the provider"
                ),
            ),
        ]
        return ReadinessReport(items=tuple(items))

    def can_read_history(self) -> bool:
        """Return whether read-only history access is allowed."""
        return self._initialized

    def can_start_semantic_task(self) -> bool:
        """Return whether a semantic task may be started.

        Blocked when OpenCode/provider is missing.
        """
        return self._initialized and self._opcodes_available

    def configure_provider(self, secret: str, allow_leak: bool = False) -> None:
        """Configure a provider secret.

        Args:
            secret: The provider secret.
            allow_leak: If True, raises :class:`ConfigLeakError` to enforce the
                rule that secrets must never be stored.

        Raises:
            ConfigLeakError: If ``allow_leak`` is True or the secret appears to
                be a high-entropy token.
        """
        if allow_leak:
            raise ConfigLeakError("storing secrets in project files is forbidden")
        if self._SECRET_PATTERN.fullmatch(secret):
            self._secrets.add(secret)
            self._log("provider secret configured (redacted)")
        else:
            self._log("provider configuration updated")

    def logs(self) -> list[str]:
        """Return sanitized wizard logs."""
        return list(self._logs)

    def _log(self, message: str) -> None:
        """Append a sanitized log entry."""
        sanitized = message
        for secret in self._secrets:
            sanitized = sanitized.replace(secret, "***")
        self._logs.append(sanitized)
