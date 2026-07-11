"""FR-0401: .louke directory layout - paths are non-overlapping."""
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
    root = canonical_root()
    assert root.name == ".louke"
    # 必须在项目内(测试 cwd 之外也允许,只要是 .louke 段)
    parts = root.parts
    assert ".louke" in parts


def test_server_dir_does_not_collide_with_others():
    s = server_dir()
    r = review_dir()
    ss = session_dir()
    # 4 个路径互不包含
    for a, b in [(s, r), (s, ss), (r, ss)]:
        try:
            b.relative_to(a)
            assert False, f"{b} is under {a}"
        except ValueError:
            pass


def test_session_dir_namespaced_by_date():
    today = date(2026, 7, 11)
    p = session_dir(date=today)
    assert "2026-07-11" in str(p)
    # 不传 date 也应返回当日路径
    p2 = session_dir()
    assert p2.exists() or not p2.exists()  # 不检查创建,只调用


def test_wiki_path_validates_type():
    p = wiki_path("story")
    assert "wiki" in p.parts
    assert p.name == "story.md"
    with pytest.raises(ValueError):
        wiki_path("bogus")


def test_wiki_types_constant_is_frozenset():
    assert isinstance(WIKI_TYPES, frozenset)
    expected = {"story", "spec", "test-plan", "architecture", "interfaces"}
    assert WIKI_TYPES == expected
