"""FR-1200: M-TEST test assets generation & review.

After all implementation tasks complete, Runtime creates Shield tasks per
Test Plan + project-local contracts.  Shield may only write required
integration/e2e in authorised paths, using the host framework's
metadata/neighbour-comment to trace AC, asserting via public interfaces,
not choosing new frameworks, not lowering test layers, and not modifying
product code to fit tests.  Runtime saves patch/digest; Prism reviews
test faithfulness and layering before the execution gate (AC-FR1200-01).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

ERROR_CODES = (
    "TEST_PATH_DENIED",
    "TEST_PRODUCT_CODE_CHANGED",
    "TEST_FRAMEWORK_UNDECLARED",
    "TEST_LAYER_DOWNGRADED",
    "TEST_AC_METADATA_MISSING",
    "TEST_PRIVATE_OUTLET_USED",
)

_AUTHORIZED_PREFIXES = (
    "tests/integration/",
    "tests/e2e/",
)

_FORBIDDEN_PREFIXES = (
    "louke/",
    "src/",
)


class MTestAssetsError(Exception):
    """A fail-closed Shield patch rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ShieldPatch:
    """A Shield test-asset patch (AC-FR1200-01).

    Attributes:
        diff_paths: Tuple of paths the patch touches.
        product_code_changed: ``True`` if any non-test path was modified.
        framework_declared: ``True`` if the host framework is already declared
            in the Test Plan/contracts.
        test_layer: ``integration|e2e|unit`` declared layer.
        ac_refs: Tuple of AC anchors present in the diff/metadata.
        uses_public_interface: ``True`` if assertions use public interfaces.
        metadata_present: ``True`` if AC metadata/neighbour-comment is present.
        lowering_layer: ``True`` if the patch lowers a required layer.
        private_outlet_used: ``True`` if the patch uses private outlets.
    """

    diff_paths: tuple[str, ...]
    product_code_changed: bool
    framework_declared: bool
    test_layer: str
    ac_refs: tuple[str, ...]
    uses_public_interface: bool
    metadata_present: bool
    lowering_layer: bool
    private_outlet_used: bool


@dataclass(frozen=True)
class ShieldPatchReview:
    """Result of :func:`evaluate_shield_patch` (AC-FR1200-01).

    Attributes:
        status: ``pass`` for an accepted patch.
        patch_digest: ``sha256:<hex>`` canonical digest of the patch.
    """

    status: str
    patch_digest: str


def _check_paths(patch: ShieldPatch) -> None:
    for path in patch.diff_paths:
        if any(path.startswith(p) for p in _FORBIDDEN_PREFIXES):
            raise MTestAssetsError(
                "TEST_PATH_DENIED",
                f"path {path!r} is not an authorised test-asset path",
            )
        if not any(path.startswith(p) for p in _AUTHORIZED_PREFIXES):
            raise MTestAssetsError(
                "TEST_PATH_DENIED",
                f"path {path!r} is not under authorised test-asset prefixes",
            )


def _check_patch(patch: ShieldPatch) -> None:
    if patch.product_code_changed:
        raise MTestAssetsError(
            "TEST_PRODUCT_CODE_CHANGED",
            "Shield must not modify product code to fit tests",
        )
    if not patch.framework_declared:
        raise MTestAssetsError(
            "TEST_FRAMEWORK_UNDECLARED",
            "Shield may not introduce a new test framework",
        )
    if patch.lowering_layer:
        raise MTestAssetsError(
            "TEST_LAYER_DOWNGRADED",
            "Shield may not lower a required test layer",
        )
    if not patch.ac_refs or not patch.metadata_present:
        raise MTestAssetsError(
            "TEST_AC_METADATA_MISSING",
            "Shield patch must carry AC metadata/neighbour-comment",
        )
    if patch.private_outlet_used or not patch.uses_public_interface:
        raise MTestAssetsError(
            "TEST_PRIVATE_OUTLET_USED",
            "Shield must assert through public observable interfaces",
        )


def evaluate_shield_patch(patch: ShieldPatch) -> ShieldPatchReview:
    """Evaluate a Shield test-asset patch (AC-FR1200-01).

    Args:
        patch: The :class:`ShieldPatch` to evaluate.

    Returns:
        A :class:`ShieldPatchReview` with ``status=pass`` and the canonical
        patch digest for Prism binding.

    Raises:
        MTestAssetsError: With a stable code from :data:`ERROR_CODES` for any
            unauthorised path, product code change, undeclared framework,
            lowered layer, missing AC metadata or private outlet use.
    """
    _check_paths(patch)
    _check_patch(patch)
    payload = json.dumps(
        {
            "diff_paths": list(patch.diff_paths),
            "test_layer": patch.test_layer,
            "ac_refs": list(patch.ac_refs),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return ShieldPatchReview(status="pass", patch_digest=digest)
