"""AC-NFR1505-01@v0.13.1 and AC-NFR1505-02@v0.13.1."""

from pathlib import Path

from louke._tools.check_acs import scan_refs


def test_parse_refs_classifies_current_legacy_wrong_version_and_malformed():
    """AC-NFR1505-01@v0.13.1: classify versioned AC references."""
    path = Path("test_sample.py")
    path.write_text(
        "\n".join(
            [
                '"""'
                + "AC-"
                + "FR0001-01@v0.13.1 "
                + "AC-"
                + "FR0001-02 "
                + "AC-"
                + "FR0001-03@v0.12.1"
                + '"""',
                '"""' + "AC-" + "FR0001-04@bad" + '"""',
            ]
        ),
        encoding="utf-8",
    )

    result = scan_refs(
        [path], current_version="v0.13.1", known_acs={"AC-" + "FR0001-01"}
    )

    assert [item["status"] for item in result["refs"]] == [
        "current",
        "legacy",
        "wrong-version",
        "malformed",
    ]
    assert result["current"] == ["AC-" + "FR0001-01"]
    assert result["legacy"] == ["AC-" + "FR0001-02"]
    assert result["wrong_version"] == ["AC-" + "FR0001-03"]
    assert result["malformed"] == ["AC-" + "FR0001-04@bad"]


def test_unknown_versioned_reference_is_reported_and_blocks():
    """AC-NFR1505-02@v0.13.1: unknown AC references block trace."""
    path = Path("test_sample.py")
    path.write_text('"""' + "AC-" + "FR9999-01@v0.13.1" + '"""\n', encoding="utf-8")

    result = scan_refs(
        [path], current_version="v0.13.1", known_acs={"AC-" + "FR0001-01"}
    )

    assert result["unknown"] == ["AC-" + "FR9999-01"]
    assert result["ok"] is False
