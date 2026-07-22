"""Regression test for end-user-docs test ID convention (AC-FR1317-02).

Ensures the End User Docs sidebar renders ``data-testid`` attributes using
the file **stem** (without extension), consistent with Dev Docs.  The v0.13
Chromium e2e test selects ``enduserdocs-file-guide`` for a file named
``guide.md``; the production code previously used ``path.name`` (which
includes ``.md``), causing the element to never be found.
"""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from louke.web.pages.workbench import _end_user_docs


def test_end_user_docs_test_id_uses_stem_not_name() -> None:
    """AC-FR1317-02: end-user-docs file buttons use stem (no extension)."""
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        docs = root / ".louke" / "end-user-docs"
        docs.mkdir(parents=True)
        (docs / "guide.md").write_text("# Guide\n", encoding="utf-8")
        (docs / "faq.md").write_text("# FAQ\n", encoding="utf-8")

        html = _end_user_docs(root)

        assert 'data-testid="enduserdocs-file-guide"' in html
        assert 'data-testid="enduserdocs-file-faq"' in html
        assert "enduserdocs-file-guide.md" not in html
        assert "enduserdocs-file-faq.md" not in html
        # The visible label still shows the full filename.
        assert ">guide.md<" in html
        assert ">faq.md<" in html


def test_end_user_docs_empty_directory_renders_tree() -> None:
    """The tree container is always present even with no docs."""
    with TemporaryDirectory() as tmp:
        html = _end_user_docs(Path(tmp))
        assert 'data-testid="enduserdocs-tree"' in html
