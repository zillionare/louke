"""State projection for the continuous, recoverable Setup journey."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SetupStep(str, Enum):
    """Ordered steps in the Workspace Setup Wizard."""

    IDENTITY = "identity"
    REPOSITORY = "repository"
    DEPENDENCIES = "dependencies"
    REVIEW = "review"
    APPLYING = "applying"
    COMPLETE = "complete"


_ORDERED_STEPS: tuple[SetupStep, ...] = (
    SetupStep.IDENTITY,
    SetupStep.REPOSITORY,
    SetupStep.DEPENDENCIES,
    SetupStep.REVIEW,
    SetupStep.APPLYING,
    SetupStep.COMPLETE,
)


_STEP_LABELS: dict[SetupStep, str] = {
    SetupStep.IDENTITY: "Local identity",
    SetupStep.REPOSITORY: "Repository",
    SetupStep.DEPENDENCIES: "Runtime dependencies",
    SetupStep.REVIEW: "Review",
    SetupStep.APPLYING: "Apply",
    SetupStep.COMPLETE: "Complete",
}


def step_label(step: SetupStep) -> str:
    """Return the user-facing label for ``step``."""
    return _STEP_LABELS[step]


def step_index(step: SetupStep) -> int:
    """Return the zero-based position of ``step`` in the wizard order."""
    return _ORDERED_STEPS.index(step)


@dataclass(frozen=True)
class SetupJourney:
    """Immutable projection of Setup progress and its recoverable blockers."""

    current_step: SetupStep
    completed_steps: tuple[SetupStep, ...]
    blocking_items: tuple[str, ...] = ()
    selections: tuple[tuple[str, str], ...] = ()

    @classmethod
    def new(cls) -> "SetupJourney":
        """Create a new Setup journey beginning at local identity."""
        return cls(current_step=SetupStep.IDENTITY, completed_steps=())

    @property
    def remaining_steps(self) -> tuple[SetupStep, ...]:
        """Return steps not yet verified, beginning with the current step."""
        return _ORDERED_STEPS[_ORDERED_STEPS.index(self.current_step) :]

    @property
    def is_complete(self) -> bool:
        """Return True if every step is completed."""
        return self.current_step == SetupStep.COMPLETE and not self.blocking_items

    def complete_current(self) -> "SetupJourney":
        """Mark the current verified step complete and move to its successor.

        Raises:
            ValueError: If already at the COMPLETE step.
        """
        index = _ORDERED_STEPS.index(self.current_step)
        if index == len(_ORDERED_STEPS) - 1:
            raise ValueError("setup is already complete")
        next_step = _ORDERED_STEPS[index + 1]
        return SetupJourney(
            current_step=next_step,
            completed_steps=(*self.completed_steps, self.current_step),
            blocking_items=(),
            selections=self.selections,
        )

    def return_to(self, step: SetupStep) -> "SetupJourney":
        """Return to a prior step and invalidate dependent downstream results.

        Args:
            step: Step whose input the Human intends to revise.

        Returns:
            A journey retaining only verified predecessors of ``step``.
        """
        index = _ORDERED_STEPS.index(step)
        # Drop any selections recorded at or after the target step.
        cut = step_index(step)
        kept = tuple(
            (k, v) for k, v in self.selections if self._selection_step(k) < cut
        )
        return SetupJourney(
            current_step=step,
            completed_steps=_ORDERED_STEPS[:index],
            blocking_items=(),
            selections=kept,
        )

    def record_selection(self, key: str, value: str) -> "SetupJourney":
        """Record a non-secret selection tied to the current step."""
        return SetupJourney(
            current_step=self.current_step,
            completed_steps=self.completed_steps,
            blocking_items=self.blocking_items,
            selections=(*self.selections, (f"{self.current_step.value}:{key}", value)),
        )

    def get_selection(self, key: str) -> str | None:
        """Return the recorded selection for ``key`` in the current step, if any."""
        prefix = f"{self.current_step.value}:"
        for k, v in self.selections:
            if k == f"{prefix}{key}":
                return v
        return None

    def block(self, message: str) -> "SetupJourney":
        """Return this journey with one non-secret actionable blocking item."""
        if not message:
            raise ValueError("blocking message is required")
        return SetupJourney(
            current_step=self.current_step,
            completed_steps=self.completed_steps,
            blocking_items=(*self.blocking_items, message),
            selections=self.selections,
        )

    def _selection_step(self, key: str) -> int:
        """Return the index of the step that owns ``key`` (used in ``return_to``)."""
        step_name = key.split(":", 1)[0]
        try:
            return step_index(SetupStep(step_name))
        except ValueError:
            return 0


@dataclass(frozen=True)
class SetupStepView:
    """Renderable state for one step in the wizard UI."""

    step: SetupStep
    label: str
    state: str  # "completed" | "current" | "pending" | "blocked"
    blocking: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_current(self) -> bool:
        return self.state == "current"

    @property
    def is_completed(self) -> bool:
        return self.state == "completed"

    @property
    def is_blocked(self) -> bool:
        return self.state == "blocked"


def render_step_views(
    journey: SetupJourney,
) -> tuple[SetupStepView, ...]:
    """Return ordered SetupStepViews for the wizard UI.

    Args:
        journey: The current SetupJourney projection.

    Returns:
        A tuple of SetupStepView with per-step render state.
    """
    current_idx = step_index(journey.current_step)
    completed_idxs = {step_index(s) for s in journey.completed_steps}
    blocking = set(journey.blocking_items)
    views: list[SetupStepView] = []
    for idx, step in enumerate(_ORDERED_STEPS):
        if idx in completed_idxs:
            state = "completed"
            per_step_blocking: tuple[str, ...] = ()
        elif idx == current_idx:
            state = "blocked" if blocking else "current"
            per_step_blocking = tuple(blocking)
        else:
            state = "pending"
            per_step_blocking = ()
        views.append(
            SetupStepView(
                step=step,
                label=step_label(step),
                state=state,
                blocking=per_step_blocking,
            )
        )
    return tuple(views)
