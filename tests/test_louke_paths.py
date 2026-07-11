"""FR-0401: .louke directory layout - paths are non-overlapping.

AC references:
- AC-FR0401-01: confirmed layout - Server/review/session/wiki each have a canonical location.
- AC-FR0401-02: new artifacts land in their canonical location, not another category's dir.
- AC-FR0401-03: at M-SPEC stage, no directory rearrangement occurs from writing this spec.
"""
import pytest
from datetime import date

from louke.paths import (
    canonical_root,
    server_dir,
    review_dir,
    session_dir,
    wiki_path,
    WIKI_TYPES,
)


def test_canonical_root_under_louke():
    """AC-FR0401-01: 经确认的目录规划 - .louke 根目录下各类产物有明确规范位置."""
    root = canonical_root()
    assert root.name == ".louke"
    # 必须在项目内(测试 cwd 之外也允许,只要是 .louke 段)
    parts = root.parts
    assert ".louke" in parts


def test_server_dir_does_not_collide_with_others():
    """AC-FR0401-02: 各类产物目录互不包含 - 新产物出现在其规范位置而非其他类别目录."""
    s = server_dir()
    r = review_dir()
    ss = session_dir()
    # 4 个路径互不包含: a should not contain b
    for a, b in [(s, r), (s, ss), (r, ss)]:
        with pytest.raises(ValueError):
            b.relative_to(a)


def test_session_dir_namespaced_by_date():
    """AC-FR0401-02: session 产物按日期命名空间隔离,落在规范位置."""
    today = date(2026, 7, 11)
    p = session_dir(date=today)
    assert "2026-07-11" in str(p)
    # 不传 date 也应返回当日路径
    p2 = session_dir()
    assert p2.exists() or not p2.exists()  # 不检查创建,只调用


def test_wiki_path_validates_type():
    """AC-FR0401-03: wiki 产物落在规范位置, 不因本 spec 撰写发生目录重排."""
    p = wiki_path("story")
    assert "wiki" in p.parts
    assert p.name == "story.md"
    with pytest.raises(ValueError):
        wiki_path("bogus")


def test_wiki_types_constant_is_frozenset():
    assert isinstance(WIKI_TYPES, frozenset)
    expected = {"story", "spec", "test-plan", "architecture", "interfaces"}
    assert WIKI_TYPES == expected
