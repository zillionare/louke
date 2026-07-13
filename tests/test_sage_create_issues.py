"""Bug #137: cmd_create_issues must emit prefix-aware spec anchors.

When the spec defines an NFR-xxxx requirement, the GitHub issue body's
"Spec Link" field must reference ``spec.md#nfr-xxxx`` (lowercase prefix
preserved), not the historically hardcoded ``#fr-xxxx``. The same applies
to the Acceptance Criteria anchor decided by ``_decide_ac_value``.

These are unit tests over the pure helpers that build the issue body so they
can run without ``gh`` or network access.
"""

from __future__ import annotations


from louke import sage


# ---------- Bug #137: Spec Link fragment must be prefix-aware ----------


def test_spec_anchor_fragment_for_fr():
    """``_spec_anchor_fragment("FR-0001")`` returns ``"fr-0001"`` (regression guard)."""
    assert sage._spec_anchor_fragment("FR-0001") == "fr-0001"


def test_spec_anchor_fragment_for_nfr():
    """``_spec_anchor_fragment("NFR-0002")`` returns ``"nfr-0002"`` (bug #137 core).

    The historically hardcoded ``fr-{fr_id.split('-')[1]}`` lost the ``n``
    prefix for NFR rows; the helper must preserve the original prefix.
    """
    frag = sage._spec_anchor_fragment("NFR-0002")
    assert frag == "nfr-0002", (
        f"Spec anchor fragment must preserve the nfr- prefix for NFR-xxxx; got {frag!r}"
    )


# ---------- Bug #137: _decide_ac_value AC anchor must be prefix-aware ----------


def test_decide_ac_value_nfr_with_acceptance_anchor_uses_nfr_fragment():
    """When acceptance.md has an ``ac-nfr-xxxx`` anchor, AC URL must use ``#ac-nfr-xxxx``.

    Previously ``_decide_ac_value`` hardcoded ``ac-fr-{num}`` regardless of the
    requirement prefix, so NFR rows emitted ``#ac-fr-xxxx`` pointing at the
    wrong anchor.
    """
    acc_text = '<a id="ac-nfr-0002"></a>\n### AC-1: sample\n'
    ac = sage._decide_ac_value(
        "NFR-0002",
        "v0.12-001-test",
        "",
        acc_text,
        "main",
        "https://github.com/foo/bar",
    )
    assert "#ac-nfr-0002" in ac, f"AC URL must preserve the nfr- prefix; got: {ac!r}"
    assert "#ac-fr-0002" not in ac


def test_decide_ac_value_nfr_with_spec_anchor_uses_nfr_fragment():
    """When only spec.md has the anchor, AC URL falls back to ``#nfr-xxxx``.

    Previously ``_decide_ac_value`` searched for ``fr-{num}`` anchor and
    emitted ``#fr-{num}``, missing NFR rows entirely.
    """
    spec_text = '<a id="nfr-0002"></a>\n### NFR-0002 sample\n'
    ac = sage._decide_ac_value(
        "NFR-0002",
        "v0.12-001-test",
        spec_text,
        "",
        "main",
        "https://github.com/foo/bar",
    )
    assert "#nfr-0002" in ac, (
        f"AC fallback URL must preserve the nfr- prefix; got: {ac!r}"
    )
    assert "#fr-0002" not in ac


def test_decide_ac_value_fr_still_uses_fr_fragment():
    """Regression guard: FR rows must keep using ``#fr-xxxx`` / ``#ac-fr-xxxx``."""
    acc_text = '<a id="ac-fr-0001"></a>\n### AC-1: sample\n'
    ac = sage._decide_ac_value(
        "FR-0001",
        "v0.12-001-test",
        "",
        acc_text,
        "main",
        "https://github.com/foo/bar",
    )
    assert "#ac-fr-0001" in ac
    assert "#ac-nfr-0001" not in ac
