"""Protocol regressions for human-authored inline-discussion syntax."""

from __future__ import annotations

from pathlib import Path

import pytest

from louke._tools.discuss import DiscussParser


@pytest.mark.parametrize(
    ("line", "expected_status"),
    [
        ("> **Aaron:** comment", "open"),
        ("> **Aaron**: comment", "open"),
        ("> **Aaron [RESOLVED]:** comment", "resolved"),
        ("> **Aaron** [RESOLVED]: comment", "resolved"),
        ("> **Aaron [REOPEN]:** comment", "reopen"),
        ("> **Aaron** [REOPEN]: comment", "reopen"),
        ("> Aaron: comment", "open"),
        ("> Aaron [RESOLVED]: comment", "resolved"),
    ],
)
def test_separator_and_status_layouts_parse_equivalently(
    tmp_path: Path, line: str, expected_status: str
) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text(f"Anchor paragraph.\n\n{line}\n", encoding="utf-8")

    result = DiscussParser().parse_file(spec)

    assert len(result.threads) == 1
    thread = result.threads[0]
    assert thread.initiator == "aaron"
    assert thread.status == expected_status
    assert thread.snippet == "comment"
    assert thread.anchor_text == "Anchor paragraph."


def test_prose_around_human_discussion_does_not_suppress_it(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text(
        "检查下这个项目的 inline-discussion 工具，它解析这样的语法块：\n"
        "\n"
        "> **Aaron:** 我们不对安装完成时间做要求。\n"
        "\n"
        "也要把它当成一个 inline-discussion。\n",
        encoding="utf-8",
    )

    result = DiscussParser().parse_file(spec)

    assert len(result.threads) == 1
    thread = result.threads[0]
    assert thread.initiator == "aaron"
    assert thread.snippet == "我们不对安装完成时间做要求。"
    assert thread.anchor_line == 1
    assert thread.anchor_text.startswith("检查下这个项目的 inline-discussion 工具")


@pytest.mark.parametrize(
    "line",
    [
        "> **Aaron** comment without a colon",
        "> **定义:** explanatory label",
        "> Note: explanatory label",
        "> Warning: explanatory label",
    ],
)
def test_tolerance_does_not_turn_ordinary_blockquotes_into_discussions(
    tmp_path: Path, line: str
) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text(f"Anchor paragraph.\n\n{line}\n", encoding="utf-8")

    assert DiscussParser().parse_file(spec).threads == []


def test_writers_emit_only_canonical_bold_separator_form(tmp_path: Path) -> None:
    spec = tmp_path / "spec.md"
    spec.write_text("Anchor paragraph.\n", encoding="utf-8")

    DiscussParser().add_thread(spec, 1, "Sage", "Question?")
    thread = DiscussParser().parse_file(spec).threads[0]
    assert "> **Sage:** Question?" in spec.read_text(encoding="utf-8")

    DiscussParser().add_reply(
        spec,
        thread.thread_id,
        "Answer.",
        "Aaron",
        total_lines=thread.total_lines,
        anchor_line=thread.anchor_line,
        anchor_text=thread.anchor_text,
        root_line=thread.root_line,
        root_text=thread.root_text,
    )
    assert ">> **Aaron:** Answer." in spec.read_text(encoding="utf-8")

    thread = DiscussParser().parse_file(spec).threads[0]
    DiscussParser().set_status(
        spec,
        thread.thread_id,
        "resolved",
        "Sage",
        total_lines=thread.total_lines,
        anchor_line=thread.anchor_line,
        anchor_text=thread.anchor_text,
        root_line=thread.root_line,
        root_text=thread.root_text,
    )
    text = spec.read_text(encoding="utf-8")
    assert "> **Sage [RESOLVED]:** Question?" in text
    assert "> **Sage**" not in text
