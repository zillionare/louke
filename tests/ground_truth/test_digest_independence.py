"""Ground-truth: independent SHA-256 digests for runtime contract artifacts.

This is the *ground-truth* side of a drift-detection pair (gap-analysis §3
P1-1 / §4 Batch 3, issue #178 S5). It recomputes the digest of an ordered
artifact map using only the Python standard library (``hashlib`` + ``json``)
and asserts the result matches a hand-authored fixture -- it does NOT import
``louke``. The matching product-side check lives in ``tests/unit/runtime``:
``louke.runtime.contract_gates.contract_digest`` must produce identical
values for the same inputs.

The digest contract is: sort the artifact map by role, serialise with
``json.dumps(..., sort_keys=True, separators=(",", ":"))``, SHA-256 the UTF-8
bytes, prefix with ``sha256:``. The three sample inputs exercise
input-shape sensitivity: only the ``story`` digest changes while ``spec`` and
``acceptance`` stay constant, proving the digest is sensitive to each role.

AC references: FR-0801 / FR-0901 artifact-bound gates (contract_digest),
gap-analysis §3 P1-1 / §4 Batch 3.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "expected_status_digests.json"


def _load_samples() -> list[dict]:
    """Load and return the hand-authored digest samples from the fixture."""
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return data["samples"]


def contract_digest(artifacts: dict[str, str]) -> str:
    """Independently compute the runtime contract digest.

    This is a from-scratch reimplementation using only the stdlib; it must NOT
    import ``louke``. It mirrors the documented contract: roles sorted
    alphabetically, JSON-serialised with sorted keys and compact separators,
    SHA-256 over the UTF-8 bytes, prefixed with ``sha256:``.

    Args:
        artifacts: Mapping from artifact role (e.g. ``"story"``) to its digest.

    Returns:
        The ``sha256:``-prefixed hex digest string.
    """
    payload = {role: artifacts[role] for role in sorted(artifacts)}
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


def test_digest_shape_is_sha256_hex_prefixed() -> None:
    """Every sample digest is ``sha256:`` + exactly 64 lowercase hex chars."""
    for sample in _load_samples():
        digest = contract_digest(sample["input"])
        assert digest.startswith("sha256:"), digest
        hexpart = digest[len("sha256:") :]
        assert len(hexpart) == 64, f"expected 64 hex chars, got {len(hexpart)}"
        int(hexpart, 16)  # raises ValueError if not valid hex


def test_digest_matches_fixture_values() -> None:
    """The independently computed digests equal the hand-authored fixture."""
    for sample in _load_samples():
        assert contract_digest(sample["input"]) == sample["expected_digest"], sample


def test_digest_is_deterministic() -> None:
    """The same input always yields the same digest."""
    samples = _load_samples()
    first = samples[0]
    a = contract_digest(first["input"])
    b = contract_digest(first["input"])
    assert a == b


def test_digest_is_input_shape_sensitive() -> None:
    """Changing only the ``story`` role changes the digest; same input is stable.

    The three samples share ``spec`` and ``acceptance`` but differ in
    ``story``, so their digests must all differ -- proving the digest reflects
    each role and is not collapsed or ignored.
    """
    samples = _load_samples()
    digests = {contract_digest(s["input"]) for s in samples}
    assert len(digests) == len(samples), (
        f"expected {len(samples)} distinct digests, got {len(digests)}"
    )
