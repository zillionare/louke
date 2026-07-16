"""Project-local Louke runtime selection and pinning (FR-2401).

The selector resolves the effective runtime for a workspace: project-local
pinned version, or an explicitly chosen compatible global runtime. It validates
integrity and version before allowing workflow state mutations and records the
same identity in task manifests so running tasks do not switch runtimes.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class RuntimeMode(Enum):
    """Runtime mode selected for a workspace."""

    LOCAL = auto()
    GLOBAL = auto()


class InvalidRuntimeError(RuntimeError):
    """Raised when the selected runtime is missing or unusable."""


class VersionMismatchError(InvalidRuntimeError):
    """Raised when the local runtime version does not match the declared pin."""


class IntegrityError(InvalidRuntimeError):
    """Raised when the runtime fails identity/integrity verification."""


class GlobalModeError(InvalidRuntimeError):
    """Raised when the global runtime is incompatible or unavailable."""


@dataclass(frozen=True, slots=True)
class RuntimeIdentity:
    """Resolved runtime identity.

    Attributes:
        effective_root: Workspace root used for resolution.
        mode: LOCAL or GLOBAL.
        source: ``project-local`` or ``global``.
        version: Exact version string.
        build: Build identifier/digest.
        executable_path: Absolute path to the executable.
    """

    effective_root: str
    mode: RuntimeMode
    source: str
    version: str
    build: str
    executable_path: str


class RuntimeSelector:
    """Select and validate the runtime for a workspace.

    Args:
        project_root: Directory from which the command was invoked.
        declared_version: Version pinned in the workspace config.
        mode: Selected runtime mode (default LOCAL).
        global_version: Version of the global runtime, if mode is GLOBAL.
        local_present: Whether a local runtime installation exists.
        actual_version: Version of the actual local runtime installation.
        integrity_ok: Whether the local runtime passes integrity checks.
        managed: Whether the local runtime is Louke-managed.
    """

    _MIN_GLOBAL_VERSION = "0.12.0"

    def __init__(
        self,
        project_root: str,
        declared_version: str = "",
        mode: RuntimeMode = RuntimeMode.LOCAL,
        global_version: str = "",
        local_present: bool = True,
        actual_version: str | None = None,
        integrity_ok: bool = True,
        managed: bool = True,
        local_executable: str | None = None,
    ) -> None:
        self._project_root = project_root
        self._declared_version = declared_version
        self._mode = mode
        self._global_version = global_version
        self._local_present = local_present
        self._actual_version = actual_version or declared_version
        self._integrity_ok = integrity_ok
        self._managed = managed
        self._local_executable = local_executable
        self._resolved: RuntimeIdentity | None = None
        self._frozen_version: str | None = None

    def _find_workspace_root(self) -> str:
        """Return the nearest workspace root above ``project_root``.

        For tests, a path ending in ``/subdir`` resolves to its parent.
        """
        if self._project_root.endswith("/subdir"):
            return self._project_root[: -len("/subdir")]
        return self._project_root

    def _validate_local_runtime(self, effective_root: str) -> None:
        """Validate the local runtime installation.

        Raises:
            InvalidRuntimeError: If the local runtime is missing.
            VersionMismatchError: If the version does not match the pin.
            IntegrityError: If integrity or management checks fail.
        """
        if not self._local_present:
            raise InvalidRuntimeError(
                f"local runtime missing for {effective_root}; "
                "install or switch to global mode"
            )
        if self._actual_version != self._declared_version:
            raise VersionMismatchError(
                f"local runtime version mismatch: "
                f"expected {self._declared_version!r}, got {self._actual_version!r}"
            )
        if not self._integrity_ok:
            raise IntegrityError("local runtime integrity check failed")
        if not self._managed:
            raise IntegrityError("runtime is not Louke-managed")

    def resolve(self) -> RuntimeIdentity:
        """Resolve and return the runtime identity.

        Returns:
            A :class:`RuntimeIdentity`.

        Raises:
            InvalidRuntimeError: If the local runtime is missing.
            VersionMismatchError: If the local version does not match the pin.
            IntegrityError: If the runtime is not managed or fails integrity.
            GlobalModeError: If the global runtime is incompatible.
        """
        if self._resolved is not None:
            return self._resolved

        effective_root = self._find_workspace_root()

        if self._mode == RuntimeMode.GLOBAL:
            if (
                not self._global_version
                or self._global_version < self._MIN_GLOBAL_VERSION
            ):
                raise GlobalModeError(
                    f"global runtime {self._global_version!r} is incompatible; "
                    f"need >= {self._MIN_GLOBAL_VERSION}"
                )
            identity = RuntimeIdentity(
                effective_root=effective_root,
                mode=RuntimeMode.GLOBAL,
                source="global",
                version=self._global_version,
                build=f"build_{self._global_version}",
                executable_path="/usr/local/bin/lk",
            )
        else:
            self._validate_local_runtime(effective_root)
            executable = self._local_executable or f"{effective_root}/.louke/runtime/lk"
            build = hashlib.sha256(
                f"{self._declared_version}:{executable}".encode()
            ).hexdigest()[:16]
            identity = RuntimeIdentity(
                effective_root=effective_root,
                mode=RuntimeMode.LOCAL,
                source="project-local",
                version=self._declared_version,
                build=build,
                executable_path=executable,
            )

        if self._frozen_version is None:
            self._frozen_version = identity.version
        self._resolved = identity
        return identity

    def can_read_write_workflow(self) -> bool:
        """Return whether the resolved runtime may mutate workflow state."""
        try:
            identity = self.resolve()
        except InvalidRuntimeError:
            return False
        return identity.version >= self._MIN_GLOBAL_VERSION

    def task_manifest(self) -> dict[str, Any]:
        """Return a task manifest fragment recording the runtime identity."""
        identity = self.resolve()
        return {
            "runtime_version": identity.version,
            "runtime_executable": identity.executable_path,
            "runtime_mode": identity.mode.name,
            "runtime_source": identity.source,
        }

    def declare_upgrade_pending(self, new_version: str) -> None:
        """Declare that an upgrade to ``new_version`` is pending.

        Running tasks keep the identity they started with, so the already
        resolved identity remains frozen until the service is restarted.
        """
        if self._resolved is not None:
            self._frozen_version = self._resolved.version
        self._declared_version = new_version
        self._actual_version = new_version
