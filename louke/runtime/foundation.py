"""Foundation programmatic precondition handler.

This module implements the ``foundation.ensure`` program step required by
FR-0401. It checks workspace-level foundation resources, performs idempotent
auto-repairs, surfaces structured questions for human-decidable gaps, and
classifies errors into terminal ``failed`` or policy-retryable states. It never
dispatches a legacy semantic Agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from louke.runtime.program_steps import HandlerResult, StepContext


@dataclass(frozen=True)
class FoundationGap:
    """A missing foundation resource or decision.

    Attributes:
        key: Stable identifier for the gap, used for idempotency and reporting.
        auto_repairable: ``True`` when the gap can be resolved programmatically
            without human input.
        question: Structured question presented when the gap requires a human
            decision. Must be ``None`` for auto-repairable gaps.
    """

    key: str
    auto_repairable: bool
    question: dict[str, Any] | None = None


class FoundationError(Exception):
    """Raised by foundation adapters to report check or repair failures.

    Attributes:
        message: Human-readable failure description.
        retryable: ``True`` when the caller should retry according to policy.
    """

    def __init__(self, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True)
class FoundationProgramResult:
    """Result returned by the canonical M-FOUND Runtime program.

    Attributes:
        status: ``pass`` when the workspace foundation is ready, otherwise
            ``blocked`` or ``failed``.
        details: Structured diagnostics for the Runtime evidence layer.
    """

    status: str
    details: dict[str, Any]


@dataclass(frozen=True)
class FoundationEnsureRequest:
    """Normalized inputs accepted by the Runtime foundation ensure handler.

    Attributes:
        workspace: Workspace root where foundation resources are materialized.
        repo: GitHub repository in ``owner/name`` form.
        version: Release version used for the release branch and projects.
        spec_id: Spec identity to initialize or verify.
        keyword: Legacy keyword retained for compatibility inference.
        upstream: Upstream branch used by release-branch preparation.
        story: Inline story text, when supplied.
        story_file: Optional path to a story source file.
        dod: Definition-of-done text for project metadata.
        security_audit: Explicit security policy, or empty for inference.
        no_commit: Whether compatibility commit/push is disabled.
        no_repo: Whether remote repository resources are disabled.
        dry_run: Whether to report operations without changing resources.
        public: Whether repository creation may request public visibility.
    """

    workspace: Path
    repo: str
    version: str
    spec_id: str
    keyword: str
    upstream: str
    story: str
    story_file: str
    dod: str
    security_audit: str
    no_commit: bool
    no_repo: bool
    dry_run: bool
    public: bool


def foundation_program_check(workspace: Path) -> FoundationProgramResult:
    """Check the minimum foundation contract without dispatching an Agent.

    Args:
        workspace: Workspace root to inspect.

    Returns:
        A :class:`FoundationProgramResult` describing whether the project
        metadata required by later stages exists.

    Raises:
        TypeError: If ``workspace`` is not path-like.
    """
    root = Path(workspace)
    project_file = root / ".louke" / "project" / "project.toml"
    if not project_file.is_file():
        return FoundationProgramResult(
            status="blocked",
            details={"missing": [project_file.as_posix()]},
        )
    return FoundationProgramResult(
        status="pass",
        details={"verified": [project_file.as_posix()]},
    )


def run_foundation_ensure(
    request: FoundationEnsureRequest, adapter: FoundationAdapter
) -> FoundationProgramResult:
    """Execute one Runtime-owned foundation ensure attempt.

    Args:
        request: Normalized compatibility or canonical program inputs.
        adapter: Resource adapter used by the Runtime handler.

    Returns:
        ``pass`` for a satisfied or repaired foundation, otherwise ``blocked``
        or ``failed`` with structured diagnostics. No workflow stage authority
        is written by this function.

    Raises:
        TypeError: If ``request.workspace`` is not path-like.
    """
    workspace = Path(request.workspace)
    context = StepContext(
        run_id=f"foundation:{request.spec_id}",
        step_id="foundation.ensure",
        attempt_id=f"foundation:{request.spec_id}",
        workspace=str(workspace),
        idempotency_key=f"foundation:{request.spec_id}",
    )
    try:
        outcome = foundation_ensure_handler(adapter)(context)
    except FoundationError as exc:
        return FoundationProgramResult(
            status=RETRYABLE if exc.retryable else FAILED,
            details={"error": exc.message},
        )
    except Exception as exc:  # noqa: BLE001
        return FoundationProgramResult(status=FAILED, details={"error": str(exc)})

    if outcome.result in {SATISFIED, REPAIRED}:
        status = "pass"
    elif outcome.result == BLOCKED:
        status = BLOCKED
    elif outcome.result == RETRYABLE:
        status = RETRYABLE
    else:
        status = FAILED
    return FoundationProgramResult(
        status=status,
        details={"handler_result": outcome.result, **outcome.output},
    )


class FoundationAdapter(Protocol):
    """Boundary for foundation checks and idempotent repairs."""

    def check(self, workspace: str) -> list[FoundationGap]:
        """Return the list of foundation gaps for ``workspace``."""
        ...

    def create(self, workspace: str, gap: FoundationGap) -> None:
        """Create the resource identified by ``gap`` idempotently.

        Implementations must not raise for duplicate keys; repeated calls with
        the same ``gap.key`` must produce the same observable result and create
        the underlying resource at most once.
        """
        ...


SATISFIED = "satisfied"
REPAIRED = "repaired"
BLOCKED = "blocked"
FAILED = "failed"
RETRYABLE = "retryable"


def foundation_ensure_handler(
    adapter: FoundationAdapter,
) -> Callable[[StepContext], HandlerResult]:
    """Return a ``foundation.ensure`` handler bound to ``adapter``.

    The handler distinguishes ``satisfied``, ``repaired``, ``blocked``,
    ``failed`` and ``retryable``. Auto-repairs are verified after creation, and
    human-decidable gaps block without guessing resources.

    Args:
        adapter: The foundation adapter that performs checks and idempotent
            repairs.

    Returns:
        A callable matching the program step handler signature.
    """

    def handler(_ctx: StepContext) -> HandlerResult:
        gaps_or_error = _safe_check(adapter, _ctx.workspace)
        if isinstance(gaps_or_error, HandlerResult):
            return gaps_or_error
        gaps = gaps_or_error

        human_gaps = [gap for gap in gaps if not gap.auto_repairable]
        if human_gaps:
            return HandlerResult(
                result=BLOCKED,
                output={"questions": [gap.question for gap in human_gaps]},
            )

        auto_gaps = [gap for gap in gaps if gap.auto_repairable]
        if not auto_gaps:
            return HandlerResult(result=SATISFIED)

        created_keys = _repair_auto_gaps(adapter, _ctx.workspace, auto_gaps)
        remaining_or_error = _safe_check(adapter, _ctx.workspace)
        if isinstance(remaining_or_error, HandlerResult):
            return remaining_or_error
        remaining = remaining_or_error

        if remaining:
            return HandlerResult(
                result=FAILED,
                output={"reason": "repair did not resolve all gaps"},
            )
        return HandlerResult(result=REPAIRED, output={"created": created_keys})

    return handler


def _safe_check(
    adapter: FoundationAdapter, workspace: str
) -> list[FoundationGap] | HandlerResult:
    """Run ``adapter.check`` and classify failures into handler results.

    Returns the gap list on success, otherwise a ``HandlerResult`` carrying
    ``failed`` or ``retryable`` according to the adapter's policy.
    """
    try:
        return adapter.check(workspace)
    except FoundationError as exc:
        return _error_result(exc)
    except Exception as exc:  # noqa: BLE001
        return HandlerResult(result=FAILED, output={"error": str(exc)})


def _repair_auto_gaps(
    adapter: FoundationAdapter, workspace: str, gaps: list[FoundationGap]
) -> list[str]:
    """Create each auto-repairable gap once and return the created keys."""
    created: list[str] = []
    seen: set[str] = set()
    for gap in gaps:
        if gap.key in seen:
            continue
        seen.add(gap.key)
        try:
            adapter.create(workspace, gap)
        except FoundationError as exc:
            raise FoundationError(
                message=f"failed to create {gap.key}: {exc.message}",
                retryable=exc.retryable,
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise FoundationError(
                message=f"failed to create {gap.key}: {exc}",
                retryable=False,
            ) from exc
        created.append(gap.key)
    return created


def _error_result(exc: FoundationError) -> HandlerResult:
    """Map a ``FoundationError`` to the appropriate handler result."""
    result = RETRYABLE if exc.retryable else FAILED
    return HandlerResult(result=result, output={"error": exc.message})
