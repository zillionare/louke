"""FR-0100: `lk serve` 启动诊断与产品入口.

Implements the deterministic contract slice of FR-0100:

* :func:`evaluate_hard_preflight` distinguishes Web-service-establishment
  failures (Python interpreter, package load, workspace path, port
  availability, app factory, non-loopback host) from Web-readiness failures.
  A hard-preflight failure raises :class:`HardPreflightError` with a
  non-zero exit code, the failure item, a non-empty remediation and
  ``web_listener_reachable is False``. The same failure is never also
  reported in the Web readiness diagnostic (AC-FR0100-03, IF-CLI-01).

* :func:`evaluate_web_readiness` lists per-item readiness
  (Louke/dependencies/configuration/model/provider/OpenCode/workspace
  identity). Missing items are ``BLOCKED`` with non-empty remediation; the
  overall readiness is ``BLOCKED`` and the release submit is disabled
  (AC-FR0100-01).

* :func:`decide_release_submit_enabled` decides whether the release entry
  is submittable: only when all checks are ``READY`` AND the setup manifest
  is valid (AC-FR0100-01, AC-FR0100-02).

* :func:`classify_serve_failure` attributes each failure to exactly one
  category (``hard_preflight`` or ``web_readiness``) so the same failure
  never appears in both (AC-FR0100-03).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


NON_LOOPBACK_AUTH_UNAVAILABLE = "NON_LOOPBACK_AUTH_UNAVAILABLE"


class ReadinessStatus(str, Enum):
    """Status of a readiness check or the overall readiness.

    Members:
        READY: The check passed.
        BLOCKED: The check failed with a known, actionable cause.
        UNKNOWN: The check could not be determined.
    """

    READY = "READY"
    BLOCKED = "BLOCKED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ReadinessCheck:
    """A single readiness check.

    Attributes:
        id: Stable check identifier (``louke``, ``dependencies``,
            ``configuration``, ``model``, ``opencode``,
            ``workspace_identity``).
        status: :class:`ReadinessStatus`.
        remediation: Non-empty when ``status == BLOCKED``; empty otherwise.
    """

    id: str
    status: ReadinessStatus
    remediation: str


@dataclass(frozen=True)
class HardPreflightResult:
    """Result of a successful :func:`evaluate_hard_preflight`.

    Attributes:
        exit_code: Always ``0`` on success.
        web_listener_reachable: Always ``True`` on success.
    """

    exit_code: int
    web_listener_reachable: bool


class HardPreflightError(Exception):
    """Raised when a hard preflight check fails.

    Attributes:
        code: ``NON_LOOPBACK_AUTH_UNAVAILABLE`` for non-loopback host;
            ``HARD_PREFLIGHT_FAILED`` otherwise.
        failure_item: Non-secret failure item name (e.g. ``python``,
            ``package``, ``port``, ``app_factory``, ``host``).
        remediation: Non-empty remediation instructing the Human how to
            recover.
        exit_code: Non-zero process exit code.
        web_listener_reachable: Always ``False``.
    """

    def __init__(
        self,
        *,
        code: str,
        failure_item: str,
        remediation: str,
        exit_code: int = 1,
    ) -> None:
        super().__init__(f"{code}: {failure_item}: {remediation}")
        self.code = code
        self.failure_item = failure_item
        self.remediation = remediation
        self.exit_code = exit_code
        self.web_listener_reachable = False


def evaluate_hard_preflight(
    *,
    python_interpreter_ok: bool,
    package_loadable: bool,
    workspace_path_ok: bool,
    port_available: bool,
    app_factory_ok: bool,
    host_is_loopback: bool,
) -> HardPreflightResult:
    """Evaluate the hard preflight checks before the Web service starts.

    Args:
        python_interpreter_ok: Whether the Python interpreter is usable.
        package_loadable: Whether the Louke package can be imported.
        workspace_path_ok: Whether the workspace path is valid.
        port_available: Whether the configured port is available.
        app_factory_ok: Whether the Starlette app factory loads.
        host_is_loopback: Whether the configured host is loopback.

    Returns:
        A :class:`HardPreflightResult` with ``exit_code == 0`` and
        ``web_listener_reachable is True`` when all checks pass.

    Raises:
        HardPreflightError: When any check fails. ``code`` is
            :data:`NON_LOOPBACK_AUTH_UNAVAILABLE` for non-loopback host;
            ``HARD_PREFLIGHT_FAILED`` otherwise. ``web_listener_reachable``
            is always ``False`` and the failure item is exactly one of the
            input preconditions (AC-FR0100-03, IF-CLI-01).
    """
    if not host_is_loopback:
        raise HardPreflightError(
            code=NON_LOOPBACK_AUTH_UNAVAILABLE,
            failure_item="host",
            remediation=(
                "non-loopback host is not supported in this spec; use "
                "127.0.0.1 (default) or wait for a future TLS/identity-provider "
                "contract to open remote access"
            ),
        )
    if not python_interpreter_ok:
        raise HardPreflightError(
            code="HARD_PREFLIGHT_FAILED",
            failure_item="python",
            remediation="install or repair the Python 3.11+ interpreter",
        )
    if not package_loadable:
        raise HardPreflightError(
            code="HARD_PREFLIGHT_FAILED",
            failure_item="package",
            remediation="reinstall the louke wheel or fix the broken import",
        )
    if not workspace_path_ok:
        raise HardPreflightError(
            code="HARD_PREFLIGHT_FAILED",
            failure_item="workspace",
            remediation="choose an existing workspace directory and re-run lk serve",
        )
    if not port_available:
        raise HardPreflightError(
            code="HARD_PREFLIGHT_FAILED",
            failure_item="port",
            remediation="free the configured port or pass --port with a free one",
        )
    if not app_factory_ok:
        raise HardPreflightError(
            code="HARD_PREFLIGHT_FAILED",
            failure_item="app_factory",
            remediation="verify starlette/uvicorn are installed and importable",
        )
    return HardPreflightResult(exit_code=0, web_listener_reachable=True)


@dataclass(frozen=True)
class WebReadiness:
    """Overall Web readiness.

    Attributes:
        overall: :class:`ReadinessStatus` aggregated from all checks.
        checks: Tuple of :class:`ReadinessCheck`.
        setup_manifest_identity: Stable identity of the setup manifest when
            one is loaded; ``None`` otherwise.
        workspace_config_modification_count: Always ``0``; reading
            readiness never modifies workspace configuration.
        release_resource_creation_count: Always ``0``; reading readiness
            never creates release-level resources.
    """

    overall: ReadinessStatus
    checks: tuple[ReadinessCheck, ...]
    setup_manifest_identity: Optional[str] = None
    workspace_config_modification_count: int = 0
    release_resource_creation_count: int = 0


def evaluate_web_readiness(
    *,
    louke_ok: bool,
    dependencies_ok: bool,
    configuration_ok: bool,
    model_provider_ok: bool,
    opencode_ok: bool,
    workspace_identity_ok: bool,
    setup_manifest_identity: Optional[str] = None,
) -> WebReadiness:
    """Evaluate the Web readiness checks.

    Args:
        louke_ok: Whether the Louke runtime is ready.
        dependencies_ok: Whether all dependencies are installed.
        configuration_ok: Whether the configuration is valid.
        model_provider_ok: Whether a model provider is configured.
        opencode_ok: Whether OpenCode is reachable.
        workspace_identity_ok: Whether the workspace identity is established.
        setup_manifest_identity: Stable identity of the setup manifest when
            one is loaded; ``None`` otherwise.

    Returns:
        A :class:`WebReadiness` with per-item checks and the aggregated
        overall status. ``BLOCKED`` items carry non-empty remediation
        (AC-FR0100-01). The function is pure: it never modifies workspace
        configuration or creates release-level resources (AC-FR0100-02).
    """
    checks: list[ReadinessCheck] = []
    if louke_ok:
        checks.append(
            ReadinessCheck(id="louke", status=ReadinessStatus.READY, remediation="")
        )
    else:
        checks.append(
            ReadinessCheck(
                id="louke",
                status=ReadinessStatus.BLOCKED,
                remediation="reinstall louke",
            )
        )
    if dependencies_ok:
        checks.append(
            ReadinessCheck(
                id="dependencies", status=ReadinessStatus.READY, remediation=""
            )
        )
    else:
        checks.append(
            ReadinessCheck(
                id="dependencies",
                status=ReadinessStatus.BLOCKED,
                remediation="install missing dependencies",
            )
        )
    if configuration_ok:
        checks.append(
            ReadinessCheck(
                id="configuration", status=ReadinessStatus.READY, remediation=""
            )
        )
    else:
        checks.append(
            ReadinessCheck(
                id="configuration",
                status=ReadinessStatus.BLOCKED,
                remediation="fix the configuration file",
            )
        )
    if model_provider_ok:
        checks.append(
            ReadinessCheck(id="model", status=ReadinessStatus.READY, remediation="")
        )
    else:
        checks.append(
            ReadinessCheck(
                id="model",
                status=ReadinessStatus.BLOCKED,
                remediation="configure a model provider in setup",
            )
        )
    if opencode_ok:
        checks.append(
            ReadinessCheck(id="opencode", status=ReadinessStatus.READY, remediation="")
        )
    else:
        checks.append(
            ReadinessCheck(
                id="opencode",
                status=ReadinessStatus.BLOCKED,
                remediation="start OpenCode or configure its URL in setup",
            )
        )
    if workspace_identity_ok:
        checks.append(
            ReadinessCheck(
                id="workspace_identity", status=ReadinessStatus.READY, remediation=""
            )
        )
    else:
        checks.append(
            ReadinessCheck(
                id="workspace_identity",
                status=ReadinessStatus.BLOCKED,
                remediation="confirm workspace identity in setup",
            )
        )
    overall = (
        ReadinessStatus.READY
        if all(c.status == ReadinessStatus.READY for c in checks)
        else ReadinessStatus.BLOCKED
    )
    return WebReadiness(
        overall=overall,
        checks=tuple(checks),
        setup_manifest_identity=setup_manifest_identity,
        workspace_config_modification_count=0,
        release_resource_creation_count=0,
    )


@dataclass(frozen=True)
class ReleaseSubmitDecision:
    """Decision returned by :func:`decide_release_submit_enabled`.

    Attributes:
        release_submit_enabled: ``True`` when the release entry may be
            submitted; ``False`` otherwise.
        blocking_check_ids: Tuple of check ids that block submission; empty
            when ``release_submit_enabled is True``.
    """

    release_submit_enabled: bool
    blocking_check_ids: tuple[str, ...]


def decide_release_submit_enabled(
    *,
    checks: tuple[ReadinessCheck, ...],
    setup_manifest_valid: bool,
) -> ReleaseSubmitDecision:
    """Decide whether the release entry may be submitted.

    Args:
        checks: Tuple of :class:`ReadinessCheck`.
        setup_manifest_valid: Whether the setup manifest is valid.

    Returns:
        A :class:`ReleaseSubmitDecision`. ``release_submit_enabled is True``
        only when all checks are ``READY`` AND ``setup_manifest_valid is
        True`` (AC-FR0100-01, AC-FR0100-02).
    """
    blocking = tuple(c.id for c in checks if c.status != ReadinessStatus.READY)
    if blocking or not setup_manifest_valid:
        return ReleaseSubmitDecision(
            release_submit_enabled=False,
            blocking_check_ids=blocking,
        )
    return ReleaseSubmitDecision(
        release_submit_enabled=True,
        blocking_check_ids=(),
    )


@dataclass(frozen=True)
class ServeFailureClassification:
    """Classification returned by :func:`classify_serve_failure`.

    Attributes:
        category: ``hard_preflight`` or ``web_readiness``.
        also_in_hard_preflight: ``True`` when the same failure also appears
            in the hard preflight; always ``False`` (each failure is
            attributed to exactly one category).
        also_in_web_readiness: ``True`` when the same failure also appears
            in the Web readiness; always ``False``.
    """

    category: str
    also_in_hard_preflight: bool = False
    also_in_web_readiness: bool = False


def classify_serve_failure(
    *,
    python_interpreter_ok: bool,
    package_loadable: bool,
    port_available: bool,
    app_factory_ok: bool,
    web_readiness_blocked: bool,
) -> ServeFailureClassification:
    """Attribute a serve failure to exactly one category.

    Args:
        python_interpreter_ok: Whether the Python interpreter is usable.
        package_loadable: Whether the Louke package can be imported.
        port_available: Whether the configured port is available.
        app_factory_ok: Whether the Starlette app factory loads.
        web_readiness_blocked: Whether any Web readiness check is BLOCKED.

    Returns:
        A :class:`ServeFailureClassification`. ``category`` is
        ``hard_preflight`` when any of the hard preflight preconditions
        failed; otherwise ``web_readiness`` when ``web_readiness_blocked``
        is True. Each failure is attributed to exactly one category
        (AC-FR0100-03).
    """
    if (
        not python_interpreter_ok
        or not package_loadable
        or not port_available
        or not app_factory_ok
    ):
        return ServeFailureClassification(
            category="hard_preflight",
            also_in_web_readiness=False,
        )
    if web_readiness_blocked:
        return ServeFailureClassification(
            category="web_readiness",
            also_in_hard_preflight=False,
        )
    return ServeFailureClassification(category="none")
