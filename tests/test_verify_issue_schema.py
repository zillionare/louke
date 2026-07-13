"""Bug #138: verify_issue_schema spec FR-set must preserve NFR prefix.

The offline loader (``main`` with ``--offline``) and the online loader
(``load_spec_frs_from_gh``) both built the spec-side FR set using a
comprehension of the form::

    {f"FR-{a.split('-')[1].zfill(3)}" for a in RE_ANCHOR.findall(text)}

which silently dropped the ``n`` prefix for NFR anchors (``nfr-0002`` ->
``FR-0002``), causing L8 bidirectional coverage to report false mismatches
between spec NFR rows and issue NFR rows.

These tests pin the loaders' return value so the prefix is preserved.
"""

from __future__ import annotations

import json

from louke._tools import verify_issue_schema as vis


# ---------- Bug #138: spec FR-set must contain both FR-xxxx and NFR-xxxx ----------


def _spec_text_with_fr_and_nfr() -> str:
    """Build a minimal spec.md fixture containing one FR and one NFR anchor."""
    return (
        '<a id="fr-0001"></a>\n'
        "### FR-0001 Sample FR requirement\n\n"
        "body\n\n"
        '<a id="nfr-0002"></a>\n'
        "### NFR-0002 Sample NFR requirement\n\n"
        "body\n"
    )


def test_load_spec_frs_from_gh_preserves_nfr_prefix(monkeypatch):
    """Online loader ``load_spec_frs_from_gh`` must return {FR-0001, NFR-0002}.

    The loader calls ``fetch_spec_markdown`` to obtain the spec text; we patch
    that function to return our fixture so no network is needed. This test
    pins the actual public loader (not a re-derived expression), so a future
    change to the loader signature is caught.
    """
    spec_text = _spec_text_with_fr_and_nfr()

    def _fake_fetch(owner, repo, branch, spec_id, spec_filename="spec.md"):
        assert owner == "foo"
        assert repo == "bar"
        assert branch == "main"
        assert spec_id == "v0.12-001-test"
        return spec_text

    monkeypatch.setattr(vis, "fetch_spec_markdown", _fake_fetch)
    spec_frs = vis.load_spec_frs_from_gh("foo", "bar", "main", "v0.12-001-test")
    assert spec_frs == {"FR-0001", "NFR-0002"}, (
        f"load_spec_frs_from_gh must preserve NFR prefix; got {spec_frs!r}"
    )


def _issue_body(fr_id: str, spec_fragment: str) -> str:
    """Build a minimal GitHub issue form body for one FR/NFR row.

    Args:
        fr_id: e.g. ``"FR-0001"`` or ``"NFR-0002"``.
        spec_fragment: the spec.md anchor fragment, e.g. ``"fr-0001"``.

    Returns:
        The rendered markdown body with the three required form fields
        (Requirement ID / Spec Link / Acceptance Criteria).
    """
    return (
        f"### Requirement ID\n{fr_id}\n\n"
        f"### Spec Link\n"
        f"https://github.com/foo/bar/blob/main/.louke/project/specs/"
        f"v0.12-001-test/spec.md#{spec_fragment}\n\n"
        f"### Acceptance Criteria\nNone\n"
    )


def _acceptance_text_no_ac() -> str:
    """Build a minimal acceptance.md with a ## No Acceptance list for the fixture FRs."""
    return (
        "# Acceptance\n\n"
        "## No Acceptance\n\n"
        "- FR-0001 (no dedicated AC)\n"
        "- NFR-0002 (no dedicated AC)\n"
    )


def test_offline_main_path_l8_matches_nfr_issue_to_spec(tmp_path, capsys, monkeypatch):
    """L8 bidirectional coverage: an NFR-0002 issue matches the spec NFR-0002 row.

    This is the bug #138 end-to-end regression: previously the spec-side set
    dropped the ``n`` prefix so the issue's ``NFR-0002`` was reported as
    orphan-in-issues and the spec's ``FR-0002`` (phantom) as orphan-in-spec,
    causing a false L8 reject. After the fix the prefix is preserved on
    both sides and L8 passes.
    """
    spec_file = tmp_path / "spec.md"
    spec_file.write_text(_spec_text_with_fr_and_nfr(), encoding="utf-8")
    acc_file = tmp_path / "acceptance.md"
    acc_file.write_text(_acceptance_text_no_ac(), encoding="utf-8")
    issues_file = tmp_path / "issues.json"
    # Two issues, one FR and one NFR, each pointing at the correct spec anchor.
    issues = [
        {
            "number": 1,
            "title": "[FR-0001] Sample FR requirement",
            "body": _issue_body("FR-0001", "fr-0001"),
            "state": "open",
        },
        {
            "number": 2,
            "title": "[NFR-0002] Sample NFR requirement",
            "body": _issue_body("NFR-0002", "nfr-0002"),
            "state": "open",
        },
    ]
    issues_file.write_text(json.dumps(issues), encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "verify_issue_schema.py",
            "--offline",
            "--spec-file",
            str(spec_file),
            "--acceptance-file",
            str(acc_file),
            "--issues-json",
            str(issues_file),
            "--spec",
            "v0.12-001-test",
        ],
    )
    rc = vis.main()
    out = capsys.readouterr().out
    assert rc == 0, (
        f"L8 must PASS when spec and issues both contain FR-0001 + NFR-0002 "
        f"(prefix preserved); rc={rc}, out:\n{out}"
    )
    # L8 must not reject: no orphan report line should appear.
    assert "L8 bidirectional coverage failed" not in out, (
        f"L8 must not reject when spec and issues match (prefix preserved); got:\n{out}"
    )
