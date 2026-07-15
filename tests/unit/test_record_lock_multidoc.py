"""Regression: cmd_record_lock must aggregate inline-discussion across all 4 spec docs."""

import textwrap
from pathlib import Path
from types import SimpleNamespace

from louke import lex
from louke import sage


def _write_spec_dir(tmp_path: Path) -> Path:
    """Build a spec dir with spec.md (clean), architecture.md (with reopen chapter thread)."""
    pd = tmp_path / "spec_dir"
    pd.mkdir()
    (pd / "spec.md").write_text(
        textwrap.dedent("""\
        ---
        locked: false
        ---
        # Web UI Foundation
        ### 4.1 modules
        > **Prism** [RESOLVED]: ok
    """)
    )
    (pd / "acceptance.md").write_text("# ac\n")
    (pd / "architecture.md").write_text(
        textwrap.dedent("""\
        # Architecture
        ### 5.2 Chat
        > **Prism** [REOPEN]: chat streaming upstream not implemented.
    """)
    )
    (pd / "interfaces.md").write_text("# interfaces\n")
    (pd / "test-plan.md").write_text("# tp\n")
    return pd


def test_record_lock_blocks_on_chapter_reopen(tmp_path, monkeypatch):
    pd = _write_spec_dir(tmp_path)
    spec_path = pd / "spec.md"
    monkeypatch.setattr(sage, "resolve_existing_path", lambda _: spec_path)
    monkeypatch.setattr(sage, "_run_lk", lambda *args: 0)

    result = sage.cmd_record_lock(SimpleNamespace(confirm=True, spec="spec-id"))

    assert result == 1


def test_quote_check_blocks_on_design_doc_reopen(tmp_path):
    pd = _write_spec_dir(tmp_path)

    result = lex.cmd_quote_check(
        SimpleNamespace(
            spec=str(pd / "spec.md"),
            check_ready=True,
            check_violations=False,
            format="text",
        )
    )

    assert result == 1
