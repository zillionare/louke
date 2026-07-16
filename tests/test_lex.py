"""Bug #152: verify_project passes URL to `gh project item-list` instead of number.

``cmd_verify_project`` builds the ``gh project item-list`` invocation as::

    ["gh", "project", "item-list", str(project_url), "--format", "json"]

but ``gh project item-list`` rejects a full URL; it only accepts a project
number together with ``--owner``. These tests pin the fix so the invocation
uses the parsed number + owner derived from the project URL.

Two URL shapes are covered (both valid GitHub Projects URLs):
  * user project:  https://github.com/users/{owner}/projects/{number}
  * repo  project: https://github.com/{owner}/{repo}/projects/{number}
"""

from __future__ import annotations

import json
import types
from unittest import mock

import louke.lex as lex


def _make_args():
    """Build a minimal argparse.Namespace matching the verify-project parser."""
    return types.SimpleNamespace(
        spec="v0.12-001-test",
        repo="",
        dry_run=False,
    )


def _patch_env(monkeypatch, project_url):
    """Patch lex helpers so cmd_verify_project reaches the gh call deterministically.

    - ``_read_project_info("Project ID")`` -> the supplied project URL
    - ``_extract_frs_from_spec`` -> a non-empty FR set so the fn does not early-return
    - ``_resolve_repo`` -> a fixed owner/repo so the fn does not early-return
    - ``subprocess.check_output`` for the item-list call -> a minimal items JSON
    """
    monkeypatch.setattr(
        lex,
        "_read_project_info",
        lambda label: project_url if label == "Project ID" else "",
    )
    monkeypatch.setattr(
        lex, "_extract_frs_from_spec", lambda spec_id: ("spec-text", ["0001"])
    )
    monkeypatch.setattr(lex, "_resolve_repo", lambda args: "quantclaws/louke")

    def _fake_check_output(cmd, *a, **kw):
        # item-list -> items payload; issue list -> empty issue array.
        if "item-list" in cmd:
            return '{"items": []}'
        return "[]"

    monkeypatch.setattr(
        lex.subprocess,
        "check_output",
        mock.Mock(side_effect=_fake_check_output),
    )


def _item_list_call(mock_check):
    """Return the first argv list passed to subprocess.check_output that targets item-list."""
    for call in mock_check.call_args_list:
        args, _ = call
        if args and "item-list" in args[0]:
            return args[0]
    return None


def test_verify_project_parses_number_and_owner_from_user_url(monkeypatch):
    """User-style project URL must use the ``@me`` item-list owner.

    URL: https://github.com/users/quantclaws/projects/15
    Expected gh argv: ["gh", "project", "item-list", "15", "--owner", "@me", "--format", "json"]
    """
    _patch_env(monkeypatch, "https://github.com/users/quantclaws/projects/15")
    assert lex.cmd_verify_project(_make_args()) == 0

    argv = _item_list_call(lex.subprocess.check_output)
    assert argv is not None, "gh project item-list was never invoked"
    assert "15" in argv, f"project number 15 missing from argv {argv}"
    assert "--owner" in argv, f"--owner flag missing from argv {argv}"
    owner_idx = argv.index("--owner") + 1
    assert owner_idx < len(argv), "--owner has no value"
    assert argv[owner_idx] == "@me", (
        f"user-owned project must use @me, got {argv[owner_idx]!r}"
    )
    assert "https://github.com" not in " ".join(argv), (
        "full URL must NOT be passed to gh project item-list"
    )


def test_verify_project_parses_number_and_owner_from_repo_url(monkeypatch):
    """Repo-style project URL must yield `item-list <number> --owner <owner>`.

    URL: https://github.com/quantclaws/louke/projects/9
    Expected gh argv includes number 9 and owner quantclaws.
    """
    _patch_env(monkeypatch, "https://github.com/quantclaws/louke/projects/9")
    assert lex.cmd_verify_project(_make_args()) == 0

    argv = _item_list_call(lex.subprocess.check_output)
    assert argv is not None, "gh project item-list was never invoked"
    assert "9" in argv, f"project number 9 missing from argv {argv}"
    assert "--owner" in argv, f"--owner flag missing from argv {argv}"
    owner_idx = argv.index("--owner") + 1
    assert argv[owner_idx] == "quantclaws", (
        f"owner must be quantclaws, got {argv[owner_idx]!r}"
    )


def test_verify_project_rejects_unrecognized_url(monkeypatch):
    """An URL without a /projects/<number> segment must exit 1, not call gh."""
    _patch_env(monkeypatch, "https://github.com/quantclaws/louke")
    assert lex.cmd_verify_project(_make_args()) == 1
    argv = _item_list_call(lex.subprocess.check_output)
    assert argv is None, "gh project item-list must not be called for bad URL"


# --- Bug #153: cross-spec [FR-] title search misreports v0.11 issues as unlinked ---


_V012_SPEC = "v0.12-001-programmatic-workflow-runtime"


def _issue(number, title, body):
    """Build a minimal gh issue dict with number/title/body/url."""
    url = f"https://github.com/zillionare/louke/issues/{number}"
    return {"number": number, "title": title, "body": body, "url": url}


_V011_ERA_BODY = (
    "### Requirement ID\nFR-0101\n\n"
    "### Spec Link\n"
    "https://github.com/zillionare/louke/blob/releases/v0.8/"
    ".louke/project/specs/v0.11-001-web-ide/spec.md#fr-0101\n\n"
    "### Acceptance Criteria\nNone\n"
)

_V012_MIRROR_BODY = (
    "### Requirement ID\nFR-0101\n\n"
    "### Spec Link\n"
    "https://github.com/zillionare/louke/blob/main/"
    f".louke/project/specs/{_V012_SPEC}/spec.md#fr-0101\n\n"
    "### Acceptance Criteria\n"
    f"https://github.com/zillionare/louke/blob/main/"
    f".louke/project/specs/{_V012_SPEC}/acceptance.md#ac-fr-0101\n"
)


def _patch_env_cross_spec(monkeypatch, project_url, issues):
    """Like _patch_env but lets the issue-list call return custom issues.

    The mirror issue is linked to the project; the v0.11-era issue is not.
    """
    monkeypatch.setattr(
        lex,
        "_read_project_info",
        lambda label: project_url if label == "Project ID" else "",
    )
    monkeypatch.setattr(
        lex, "_extract_frs_from_spec", lambda spec_id: ("spec-text", ["0101"])
    )
    monkeypatch.setattr(lex, "_resolve_repo", lambda args: "zillionare/louke")

    linked_url = issues[0]["url"]  # mirror issue is linked
    items_payload = json.dumps([{"content": {"url": linked_url}, "url": linked_url}])

    def _fake_check_output(cmd, *a, **kw):
        if "item-list" in cmd:
            return items_payload
        if "issue" in cmd and "list" in cmd:
            return json.dumps(issues)
        return "[]"

    monkeypatch.setattr(
        lex.subprocess,
        "check_output",
        mock.Mock(side_effect=_fake_check_output),
    )


def _make_args_v012():
    return types.SimpleNamespace(spec=_V012_SPEC, repo="", dry_run=False)


def test_verify_project_filters_cross_spec_v011_issue(monkeypatch):
    """Bug #153: a v0.11-era issue with [FR-0101] title must not be flagged unlinked
    when verifying v0.12-001, because its body Spec Link points at v0.11-001-web-ide.

    Setup:
      - mirror issue #141: title [FR-0101], body -> v0.12-001 spec, linked to project
      - v0.11-era issue #99:  title [FR-0101], body -> v0.11-001-web-ide, NOT linked
    Expected: exit 0 (no unlinked), because #99 is cross-spec and must be filtered out.
    """
    issues = [
        _issue(141, "[FR-0101] Runtime 是状态与转移的唯一写入者", _V012_MIRROR_BODY),
        _issue(99, "[FR-0101] Louke Server 工作流推进与 Agent 工具化", _V011_ERA_BODY),
    ]
    _patch_env_cross_spec(
        monkeypatch, "https://github.com/users/quantclaws/projects/15", issues
    )
    assert lex.cmd_verify_project(_make_args_v012()) == 0


def test_verify_project_still_flags_unlinked_same_spec_issue(monkeypatch):
    """A genuine v0.12-001 issue that is NOT linked must still be flagged unlinked.

    This guards against the fix over-filtering: the cross-spec filter must only drop
    issues whose body points at a different spec, not issues of the same spec.
    """
    issues = [
        _issue(141, "[FR-0101] Runtime 是状态与转移的唯一写入者", _V012_MIRROR_BODY),
        _issue(200, "[FR-0101] unlinked v0.12 issue", _V012_MIRROR_BODY),
    ]
    _patch_env_cross_spec(
        monkeypatch, "https://github.com/users/quantclaws/projects/15", issues
    )
    rc = lex.cmd_verify_project(_make_args_v012())
    assert rc == 1, "an unlinked same-spec issue must still be flagged"
