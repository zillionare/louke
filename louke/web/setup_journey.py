"""State projection for the continuous, recoverable Setup journey."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SetupStep(str, Enum):
    """Ordered steps in the Workspace Setup Wizard."""

    IDENTITY = "identity"
    REPOSITORY = "repository"
    DEPENDENCIES = "dependencies"
    REVIEW = "review"
    APPLYING = "applying"


_ORDERED_STEPS = tuple(SetupStep)


@dataclass(frozen=True)
class SetupJourney:
    """Immutable projection of Setup progress and its recoverable blockers."""

    current_step: SetupStep
    completed_steps: tuple[SetupStep, ...]
    blocking_items: tuple[str, ...] = ()

    @classmethod
    def new(cls) -> "SetupJourney":
        """Create a new Setup journey beginning at local identity."""
        return cls(current_step=SetupStep.IDENTITY, completed_steps=())

    @property
    def remaining_steps(self) -> tuple[SetupStep, ...]:
        """Return steps not yet verified, beginning with the current step."""
        return _ORDERED_STEPS[_ORDERED_STEPS.index(self.current_step) :]

    def complete_current(self) -> "SetupJourney":
        """Mark the current verified step complete and move to its successor.

        Raises:
            ValueError: If Apply is already current; completion must be read
                back by the owning apply service rather than inferred here.
        """
        index = _ORDERED_STEPS.index(self.current_step)
        if index == len(_ORDERED_STEPS) - 1:
            raise ValueError("apply completion requires owning-service readback")
        return SetupJourney(
            current_step=_ORDERED_STEPS[index + 1],
            completed_steps=(*self.completed_steps, self.current_step),
        )

    def return_to(self, step: SetupStep) -> "SetupJourney":
        """Return to a prior step and invalidate dependent downstream results.

        Args:
            step: Step whose input the Human intends to revise.

        Returns:
            A journey retaining only verified predecessors of ``step``.
        """
        index = _ORDERED_STEPS.index(step)
        return SetupJourney(current_step=step, completed_steps=_ORDERED_STEPS[:index])

    def block(self, message: str) -> "SetupJourney":
        """Return this journey with one non-secret actionable blocking item."""
        if not message:
            raise ValueError("blocking message is required")
        return SetupJourney(
            current_step=self.current_step,
            completed_steps=self.completed_steps,
            blocking_items=(*self.blocking_items, message),
        )
