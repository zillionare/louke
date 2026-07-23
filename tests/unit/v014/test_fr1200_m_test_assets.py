"""AC-FR1200-01: M-TEST test assets generation & review.

After all implementation tasks complete, Runtime creates Shield tasks per
Test Plan + project-local contracts.  Shield may only write required
integration/e2e in authorised paths, using the host framework's
metadata/neighbour-comment to trace AC, asserting via public interfaces,
not choosing new frameworks, not lowering test layers, and not modifying
product code to fit tests.  Runtime saves patch/digest; Prism reviews
test faithfulness and layering before the execution gate.
"""

from __future__ import annotations


import pytest

from louke.runtime.m_test_assets import (
    MTestAssetsError,
    ShieldPatch,
    ShieldPatchReview,
    evaluate_shield_patch,
)

_AC = "AC-FR1200-01"


def _patch(
    *,
    diff_paths: tuple[str, ...] = ("tests/integration/v014/test_x.py",),
    product_code_changed: bool = False,
    framework_declared: bool = True,
    test_layer: str = "integration",
    ac_refs: tuple[str, ...] = (_AC,),
    uses_public_interface: bool = True,
    metadata_present: bool = True,
    lowering_layer: bool = False,
    private_outlet_used: bool = False,
) -> ShieldPatch:
    return ShieldPatch(
        diff_paths=diff_paths,
        product_code_changed=product_code_changed,
        framework_declared=framework_declared,
        test_layer=test_layer,
        ac_refs=ac_refs,
        uses_public_interface=uses_public_interface,
        metadata_present=metadata_present,
        lowering_layer=lowering_layer,
        private_outlet_used=private_outlet_used,
    )


def test_evaluate_shield_patch_passes_for_valid_integration() -> None:
    """AC-FR1200-01: a valid integration patch with AC metadata passes."""
    review = evaluate_shield_patch(_patch())
    assert isinstance(review, ShieldPatchReview)
    assert review.status == "pass"
    assert review.patch_digest.startswith("sha256:")


def test_evaluate_rejects_product_code_change() -> None:
    """AC-FR1200-01: Shield must not modify product code."""
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(_patch(product_code_changed=True))
    assert exc.value.code == "TEST_PRODUCT_CODE_CHANGED"


def test_evaluate_rejects_undeclared_framework() -> None:
    """AC-FR1200-01: Shield may not introduce a new framework."""
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(_patch(framework_declared=False))
    assert exc.value.code == "TEST_FRAMEWORK_UNDECLARED"


def test_evaluate_rejects_lowered_layer() -> None:
    """AC-FR1200-01: lowering a required integration to unit-only is rejected."""
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(_patch(test_layer="unit", lowering_layer=True))
    assert exc.value.code == "TEST_LAYER_DOWNGRADED"


def test_evaluate_rejects_missing_ac_metadata() -> None:
    """AC-FR1200-01: missing AC metadata in patch is rejected."""
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(_patch(ac_refs=(), metadata_present=False))
    assert exc.value.code == "TEST_AC_METADATA_MISSING"


def test_evaluate_rejects_private_outlet_use() -> None:
    """AC-FR1200-01: Shield must assert through public interfaces."""
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(_patch(private_outlet_used=True))
    assert exc.value.code == "TEST_PRIVATE_OUTLET_USED"


def test_evaluate_rejects_unauthorized_path() -> None:
    """AC-FR1200-01: Shield may only write in authorized paths."""
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(_patch(diff_paths=("louke/v014/x.py",)))
    assert exc.value.code == "TEST_PATH_DENIED"


def test_patch_digest_deterministic() -> None:
    """AC-FR1200-01: same patch content produces same digest for Prism binding."""
    a = evaluate_shield_patch(_patch())
    b = evaluate_shield_patch(_patch())
    assert a.patch_digest == b.patch_digest
