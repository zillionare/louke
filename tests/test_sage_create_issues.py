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


# ---------- Bug: dedup must filter by spec_id, not just FR title ----------


def test_gh_list_issues_with_fr_no_spec_id_returns_all_title_matches():
    """Without ``spec_id`` the helper preserves legacy behaviour: any title match wins.

    This documents the backward-compatible default; callers that need strict
    per-spec isolation must pass ``spec_id``.
    """
    issues = [
        {
            "number": 1,
            "title": "[FR-1301] v0.12 something",
            "body": "...specs/v0.12-001-x/spec.md...",
            "url": "https://github.com/o/r/issues/1",
        },
        {
            "number": 2,
            "title": "[FR-1301] v0.13 something",
            "body": "...specs/v0.13-001-y/spec.md...",
            "url": "https://github.com/o/r/issues/2",
        },
    ]

    def fake_check_output(cmd, text=True, stderr=None):
        import json as _json

        return _json.dumps(issues)

    import subprocess

    orig = subprocess.check_output
    subprocess.check_output = fake_check_output
    try:
        result = sage._gh_list_issues_with_fr("o/r", "FR-1301")
    finally:
        subprocess.check_output = orig
    assert {i["number"] for i in result} == {1, 2}


def test_gh_list_issues_with_fr_filters_by_spec_id():
    """Bug: v0.12 FR-1301 should NOT count as v0.13 FR-1301's existing issue.

    When ``spec_id="v0.13-001-y"`` is passed, only the issue whose Spec Link
    references v0.13-001-y/spec.md must be returned. The v0.12 issue is
    filtered out even though both share the ``[FR-1301]`` title fragment.
    """
    issues = [
        {
            "number": 1,
            "title": "[FR-1301] v0.12 something",
            "body": (
                "### Requirement ID\nFR-1301\n\n"
                "### Spec Link\n"
                "https://github.com/o/r/blob/main/.louke/project/specs/"
                "v0.12-001-programmatic-workflow-runtime/spec.md#fr-1301\n"
            ),
            "url": "https://github.com/o/r/issues/1",
        },
        {
            "number": 2,
            "title": "[FR-1301] v0.13 something",
            "body": (
                "### Requirement ID\nFR-1301\n\n"
                "### Spec Link\n"
                "https://github.com/o/r/blob/main/.louke/project/specs/"
                "v0.13-001-web-ui-foundation/spec.md#fr-1301\n"
            ),
            "url": "https://github.com/o/r/issues/2",
        },
    ]

    def fake_check_output(cmd, text=True, stderr=None):
        import json as _json

        return _json.dumps(issues)

    import subprocess

    orig = subprocess.check_output
    subprocess.check_output = fake_check_output
    try:
        result = sage._gh_list_issues_with_fr(
            "o/r", "FR-1301", spec_id="v0.13-001-web-ui-foundation"
        )
    finally:
        subprocess.check_output = orig
    assert [i["number"] for i in result] == [2], (
        "Only the v0.13 issue should remain after spec_id filter; "
        f"got {[i['number'] for i in result]}"
    )


# ---------- Bug: project URL parser used by create-issues + record-lock ----------


def test_parse_project_url_local_user_scoped():
    """User-scoped Projects URLs (https://github.com/users/<owner>/projects/<N>)."""
    num, owner = sage._parse_project_url_local(
        "https://github.com/users/quantclaws/projects/18"
    )
    assert num == "18"
    assert owner == "quantclaws"


def test_parse_project_url_local_repo_scoped():
    """Repo-scoped Projects URLs (https://github.com/<owner>/<repo>/projects/<N>)."""
    num, owner = sage._parse_project_url_local(
        "https://github.com/quantclaws/louke/projects/42"
    )
    assert num == "42"
    assert owner == "quantclaws"


def test_parse_project_url_local_invalid_returns_none_pair():
    """Garbage URLs must return ``(None, None)`` so callers can fall back."""
    assert sage._parse_project_url_local("") == (None, None)
    assert sage._parse_project_url_local("not-a-url") == (None, None)
    assert sage._parse_project_url_local("https://github.com/o/r") == (None, None)


# ---------- Bug: cmd_record_lock must rewrite frontmatter cleanly ----------


def test_apply_lock_to_frontmatter_replaces_placeholder_keys():
    """Frontmatter with ``locked: false`` + empty placeholder keys must be
    rewritten to a single canonical block (no duplication).

    Previously the code appended new ``locked*`` keys after the old ones,
    producing malformed YAML like::

        ---
        locked: false
        locked-at:
        locked-by:
        locked: true
        locked-at: 2026-...
        locked-by: lk agent sage record-lock
        ---
    """
    placeholder = (
        "---\n"
        "locked: false\n"
        "locked-at:\n"
        "locked-by:\n"
        "---\n"
        "# Web UI Foundation — Spec\n"
        "\n"
        "Some content.\n"
    )
    new_text, locked_already = sage._apply_lock_to_frontmatter(placeholder)
    assert locked_already is False
    # Must open with exactly one frontmatter block.
    assert new_text.startswith("---\n")
    assert new_text[4:].find("\n---\n") != -1
    body_after_first_fm = new_text.split("\n---\n", 1)[1]
    assert "locked: false" not in new_text
    assert (
        "locked-at:" not in new_text.split("\n---\n")[0]
        or new_text.count("locked-at:") == 1
    )
    # The body must be preserved verbatim.
    assert "# Web UI Foundation — Spec" in body_after_first_fm
    assert "Some content." in body_after_first_fm


def test_apply_lock_to_frontmatter_idempotent_when_already_true():
    """Re-running record-lock on a locked spec is a no-op."""
    locked = (
        "---\n"
        "locked: true\n"
        "locked-at: 2026-07-15T00:00:00Z\n"
        "locked-by: lk agent sage record-lock\n"
        "---\n"
        "# body\n"
    )
    new_text, locked_already = sage._apply_lock_to_frontmatter(locked)
    assert locked_already is True
    assert new_text == locked


def test_apply_lock_to_frontmatter_adds_canonical_when_no_frontmatter():
    """A spec file with no YAML frontmatter gets one prepended."""
    bare = "# body without frontmatter\n"
    new_text, locked_already = sage._apply_lock_to_frontmatter(bare)
    assert locked_already is False
    assert new_text.startswith("---\nlocked: true\nlocked-at:"), new_text[:80]


def test_apply_lock_to_frontmatter_preserves_other_keys():
    """Non-``locked*`` keys (e.g. ``status``, ``version``) must be preserved."""
    mixed = "---\nstatus: Draft\nversion: 0.13\nlocked: false\n---\n# body\n"
    new_text, locked_already = sage._apply_lock_to_frontmatter(mixed)
    assert locked_already is False
    assert "status: Draft" in new_text
    assert "version: 0.13" in new_text
    assert "locked: true" in new_text
    assert "locked: false" not in new_text
