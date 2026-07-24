"""OpenCode real model probe for Setup verification.

AC-FR0201-01, AC-FR0201-02, AC-FR0301-01

Executes a minimal real ``opencode run --model <id> "please echo hi"``
to verify that at least one configured model is reachable. The probe
does not carry Story, artifact, credential, or workspace file context.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any

PROBE_PROMPT = "please echo hi"
SINGLE_TIMEOUT_SECONDS = 15
TOTAL_DEADLINE_SECONDS = 60


@dataclass(frozen=True)
class ProbeResult:
    """Outcome of a single model probe attempt.

    Args:
        model_id: The model id that was probed.
        state: ``passed``, ``failed``, or ``uncertain``.
        diagnosis: Non-secret diagnostic dict, or ``None``.
    """

    model_id: str
    state: str
    diagnosis: dict[str, Any] | None = None


@dataclass
class ModelCheckResult:
    """Aggregate result of checking all candidate models.

    Args:
        check_id: Stable identifier for this check attempt.
        revision: Check-scoped revision.
        state: ``queued``, ``running``, ``passed``, ``failed``, or ``uncertain``.
        current_model_id: The model currently being probed, or ``None``.
        attempted: List of individual probe results.
        diagnosis: Non-secret diagnostic, or ``None``.
        observed_at: ISO-8601 timestamp.
    """

    check_id: str
    revision: int
    state: str = "queued"
    current_model_id: str | None = None
    attempted: list[ProbeResult] = field(default_factory=list)
    diagnosis: dict[str, Any] | None = None
    observed_at: str = ""


def is_available() -> bool:
    """Return ``True`` if the ``opencode`` executable is on PATH."""
    return shutil.which("opencode") is not None


def run_minimal(
    *,
    model_id: str,
    prompt: str = PROBE_PROMPT,
    deadline_seconds: int = SINGLE_TIMEOUT_SECONDS,
    executable: str = "opencode",
) -> ProbeResult:
    """Run a single minimal model probe.

    Args:
        model_id: The model id to probe.
        prompt: The minimal prompt (default: ``PROBE_PROMPT``).
        deadline_seconds: Per-model timeout.
        executable: The executable name or path.

    Returns:
        A :class:`ProbeResult` with ``state=passed`` on exit 0,
        ``state=failed`` on non-zero exit, or ``state=uncertain``
        on timeout.
    """
    try:
        proc = subprocess.run(
            [executable, "run", "--model", model_id, prompt],
            capture_output=True,
            text=True,
            timeout=deadline_seconds,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return ProbeResult(
            model_id=model_id,
            state="uncertain",
            diagnosis={"reason": "timeout", "deadline_seconds": deadline_seconds},
        )
    except FileNotFoundError:
        return ProbeResult(
            model_id=model_id,
            state="failed",
            diagnosis={"reason": "executable_not_found", "executable": executable},
        )
    if proc.returncode == 0:
        return ProbeResult(model_id=model_id, state="passed")
    return ProbeResult(
        model_id=model_id,
        state="failed",
        diagnosis={
            "reason": "nonzero_exit",
            "exit_code": proc.returncode,
            "stderr_snippet": (proc.stderr or "")[:200],
        },
    )
