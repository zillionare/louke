"""Integration tests for FR-1200: M-TEST test assets generation & review.

AC-FR1200-01: Shield only generates integration/e2e with parseable AC
metadata in contract paths, covering Test Plan required layers through
public observable interfaces; Prism verdict binds the test patch
digest. Patches that modify product code, introduce undeclared
frameworks, lower test layers, snoop private state, or lack trace are
rejected.

Interfaces covered (per interfaces.md):
- IF-TEST-02 (Primary ARC-08)
- IF-TST-01 (inherited, ARC-08)
- IF-REV-02 (Prism review, ARC-07)
"""
# AC-FR1200-01

from __future__ import annotations

import pytest

from louke.v014.fr1200_m_test_assets import (
    ERROR_CODES,
    MTestAssetsError,
    ShieldPatch,
    ShieldPatchReview,
    evaluate_shield_patch,
)


def _valid_patch() -> ShieldPatch:
    return ShieldPatch(
        diff_paths=(
            "tests/integration/v014_003_workflow_reflow/test_fr0100_m_impl_entry.py",
        ),
        product_code_changed=False,
        framework_declared=True,
        test_layer="integration",
        ac_refs=("AC-FR0100-01",),
        uses_public_interface=True,
        metadata_present=True,
        lowering_layer=False,
        private_outlet_used=False,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_evaluate_shield_patch_passes_on_valid_patch():
    """AC-FR1200-01: valid Shield patch -> status=pass with digest."""
    review = evaluate_shield_patch(_valid_patch())
    assert isinstance(review, ShieldPatchReview)
    assert review.status == "pass"
    assert review.patch_digest.startswith("sha256:")


@pytest.mark.real_module
def test_evaluate_shield_patch_rejects_product_code_modification():
    """AC-FR1200-01: Shield must not modify product code -> TEST_PRODUCT_CODE_CHANGED."""
    p = ShieldPatch(
        diff_paths=_valid_patch().diff_paths,
        product_code_changed=True,
        framework_declared=True,
        test_layer="integration",
        ac_refs=("AC-FR0100-01",),
        uses_public_interface=True,
        metadata_present=True,
        lowering_layer=False,
        private_outlet_used=False,
    )
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(p)
    assert exc.value.code == "TEST_PRODUCT_CODE_CHANGED"


@pytest.mark.real_module
def test_evaluate_shield_patch_rejects_unauthorized_path():
    """AC-FR1200-01: Shield must write only in tests/integration or tests/e2e
    -> TEST_PATH_DENIED."""
    p = ShieldPatch(
        diff_paths=("louke/v014/fr0100_m_impl_entry.py",),  # product path
        product_code_changed=False,
        framework_declared=True,
        test_layer="integration",
        ac_refs=("AC-FR0100-01",),
        uses_public_interface=True,
        metadata_present=True,
        lowering_layer=False,
        private_outlet_used=False,
    )
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(p)
    assert exc.value.code == "TEST_PATH_DENIED"


@pytest.mark.real_module
def test_evaluate_shield_patch_rejects_undeclared_framework():
    """AC-FR1200-01: Shield may not introduce new framework ->
    TEST_FRAMEWORK_UNDECLARED."""
    p = ShieldPatch(
        diff_paths=_valid_patch().diff_paths,
        product_code_changed=False,
        framework_declared=False,
        test_layer="integration",
        ac_refs=("AC-FR0100-01",),
        uses_public_interface=True,
        metadata_present=True,
        lowering_layer=False,
        private_outlet_used=False,
    )
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(p)
    assert exc.value.code == "TEST_FRAMEWORK_UNDECLARED"


@pytest.mark.real_module
def test_evaluate_shield_patch_rejects_layer_downgrade():
    """AC-FR1200-01: lowering required layer -> TEST_LAYER_DOWNGRADED."""
    p = ShieldPatch(
        diff_paths=_valid_patch().diff_paths,
        product_code_changed=False,
        framework_declared=True,
        test_layer="integration",
        ac_refs=("AC-FR0100-01",),
        uses_public_interface=True,
        metadata_present=True,
        lowering_layer=True,
        private_outlet_used=False,
    )
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(p)
    assert exc.value.code == "TEST_LAYER_DOWNGRADED"


@pytest.mark.real_module
def test_evaluate_shield_patch_rejects_missing_ac_metadata():
    """AC-FR1200-01: missing AC metadata/comment -> TEST_AC_METADATA_MISSING."""
    p = ShieldPatch(
        diff_paths=_valid_patch().diff_paths,
        product_code_changed=False,
        framework_declared=True,
        test_layer="integration",
        ac_refs=("AC-FR0100-01",),
        uses_public_interface=True,
        metadata_present=False,  # missing metadata
        lowering_layer=False,
        private_outlet_used=False,
    )
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(p)
    assert exc.value.code == "TEST_AC_METADATA_MISSING"


@pytest.mark.real_module
def test_evaluate_shield_patch_rejects_missing_ac_refs():
    """AC-FR1200-01: no AC anchors -> TEST_AC_METADATA_MISSING."""
    p = ShieldPatch(
        diff_paths=_valid_patch().diff_paths,
        product_code_changed=False,
        framework_declared=True,
        test_layer="integration",
        ac_refs=(),  # no AC refs
        uses_public_interface=True,
        metadata_present=True,
        lowering_layer=False,
        private_outlet_used=False,
    )
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(p)
    assert exc.value.code == "TEST_AC_METADATA_MISSING"


@pytest.mark.real_module
def test_evaluate_shield_patch_rejects_private_outlet():
    """AC-FR1200-01: private outlet / no public interface -> TEST_PRIVATE_OUTLET_USED."""
    p = ShieldPatch(
        diff_paths=_valid_patch().diff_paths,
        product_code_changed=False,
        framework_declared=True,
        test_layer="integration",
        ac_refs=("AC-FR0100-01",),
        uses_public_interface=False,  # uses private
        metadata_present=True,
        lowering_layer=False,
        private_outlet_used=False,
    )
    with pytest.raises(MTestAssetsError) as exc:
        evaluate_shield_patch(p)
    assert exc.value.code == "TEST_PRIVATE_OUTLET_USED"

    # Also explicit private_outlet_used
    p2 = ShieldPatch(
        diff_paths=_valid_patch().diff_paths,
        product_code_changed=False,
        framework_declared=True,
        test_layer="integration",
        ac_refs=("AC-FR0100-01",),
        uses_public_interface=True,
        metadata_present=True,
        lowering_layer=False,
        private_outlet_used=True,
    )
    with pytest.raises(MTestAssetsError) as exc2:
        evaluate_shield_patch(p2)
    assert exc2.value.code == "TEST_PRIVATE_OUTLET_USED"


@pytest.mark.real_module
def test_evaluate_shield_patch_accepts_e2e_path():
    """AC-FR1200-01: e2e path is also authorised."""
    p = ShieldPatch(
        diff_paths=(
            "tests/e2e/v014_003_workflow_reflow/test_journey_full_lifecycle.py",
        ),
        product_code_changed=False,
        framework_declared=True,
        test_layer="e2e",
        ac_refs=("AC-FR0100-01",),
        uses_public_interface=True,
        metadata_present=True,
        lowering_layer=False,
        private_outlet_used=False,
    )
    review = evaluate_shield_patch(p)
    assert review.status == "pass"


@pytest.mark.real_module
def test_evaluate_shield_patch_digest_is_deterministic():
    """AC-FR1200-01: same patch -> same digest (Prism binds to digest)."""
    r1 = evaluate_shield_patch(_valid_patch())
    r2 = evaluate_shield_patch(_valid_patch())
    assert r1.patch_digest == r2.patch_digest


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR1200-01: ERROR_CODES includes all codes from interfaces.md §6."""
    expected = {
        "TEST_PATH_DENIED",
        "TEST_PRODUCT_CODE_CHANGED",
        "TEST_FRAMEWORK_UNDECLARED",
        "TEST_LAYER_DOWNGRADED",
        "TEST_AC_METADATA_MISSING",
        "TEST_PRIVATE_OUTLET_USED",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
