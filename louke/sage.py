"""Legacy Sage program adapters used during the v0.14 transition.

The v0.14 Runtime owns these deterministic operations. Sage's semantic prompt
does not call them; they remain temporarily available to the v0.13 CLI path.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from ._common import RUNTIME_FOUNDATION_PROGRAM, resolve_existing_path


def register(subparsers):
    parser = subparsers.add_parser("sage", help="requirement clarification (Sage)")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    # quote-check: check quote status in spec.md (v0.7-003: invokes discuss.py internally)
    p = sub.add_parser(
        "quote-check", help="check whether all quotes in spec.md are resolved"
    )
    p.add_argument("--spec", required=True, help="spec-id, e.g. v0.1-001-init")
    p.add_argument(
        "--check-ready",
        action="store_true",
        help="exit 0 if ready (Maestro gate; no JSON output)",
    )
    p.add_argument(
        "--check-violations",
        action="store_true",
        help="detect ownership violations (who closed someone else's quote)",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format (default text)",
    )

    # commit-spec: multi-step git ops wrapper
    p = sub.add_parser(
        "commit-spec", help="commit spec + acceptance (git add + commit + push)"
    )
    p.add_argument("--spec", required=True)
    p.add_argument("--message", required=True)
    p.add_argument("--no-push", action="store_true")

    # create-issues: create GitHub issues from spec (FR-0410)
    p = sub.add_parser(
        "create-issues", help="create GitHub issues from spec (with schema validation)"
    )
    p.add_argument("--spec", required=True)
    p.add_argument("--spec-file", default="", help="directly specify spec.md path")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--skip-project",
        action="store_true",
        help="do not block when Project URL is missing",
    )

    # record-lock: 3-signal lock record (FR-0420)
    p = sub.add_parser(
        "record-lock", help="record spec locked: true (after 3 signals pass)"
    )
    p.add_argument("--spec", required=True)
    p.add_argument("--confirm", action="store_true")


def run(args):
    handlers = {
        "quote-check": cmd_quote_check,
        "commit-spec": cmd_commit_spec,
        "create-issues": cmd_create_issues,
        "lock-spec": cmd_lock_spec,
        "record-lock": cmd_record_lock,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_quote_check(args):
    """Invoke louke._tools.discuss (FR-0450 resolve_spec_path, v0.7-003 inline-discussion).

    3 mutually-exclusive flags:
    --check-ready: exit 0 if is_ready (Maestro gate; emits blockers to stderr)
    --check-violations: detect status markers on nested reply lines (parser ignores them, but writer intent is wrong)
    --format text|json (default text): list all threads + status; do NOT combine --check-ready when requesting JSON
    """
    spec_path = _resolve_quote_check_spec(args)
    if not spec_path.exists():
        print(f"sage quote-check: {spec_path} not found", file=sys.stderr)
        return 2
    from ._tools import discuss

    if args.check_ready:
        # Aggregate across spec.md + design docs (architecture.md, interfaces.md,
        # test-plan.md). Per FR-0060 the gate must catch blockers in any doc;
        # otherwise chapter-anchored threads in design docs are silently ignored.
        spec_dir = spec_path.parent
        design_docs = [
            spec_path,
            spec_dir / "architecture.md",
            spec_dir / "interfaces.md",
            spec_dir / "test-plan.md",
        ]
        existing = [p for p in design_docs if p.exists()]
        all_blockers: list[str] = []
        ready = True
        for path in existing:
            ready_one, blockers = discuss.DiscussParser().is_ready(path)
            if not ready_one:
                ready = False
                # Annotate blockers with file basename so multi-file output is traceable
                for b in blockers:
                    all_blockers.append(f"[{path.name}] {b}")
        if not ready:
            print(
                f"spec not ready: {len(all_blockers)} blocker(s) across "
                f"{len(existing)} doc(s)",
                file=sys.stderr,
            )
            for b in all_blockers:
                print(f"  {b}", file=sys.stderr)
        return 0 if ready else 1
    if args.check_violations:
        exit_code, msg = discuss.check_violations(spec_path)
        print(msg)
        return exit_code
    exit_code, output = discuss.format_ready(spec_path, args.format)
    print(output)
    return exit_code


def _resolve_quote_check_spec(args) -> Path:
    """Resolve --spec argument to a spec.md Path (spec-id or direct path)."""
    spec_arg = args.spec
    candidate = Path(spec_arg)
    if candidate.exists():
        return candidate
    default = Path(f".louke/project/specs/{args.spec}/spec.md")
    if default.exists():
        return default
    return resolve_existing_path(spec_arg)


def cmd_commit_spec(args):
    """git add spec.md + acceptance.md + commit + push (multi-step wrapper)."""
    spec_path = f".louke/project/specs/{args.spec}"
    cmds = [
        ["git", "add", f"{spec_path}/spec.md", f"{spec_path}/acceptance.md"],
        ["git", "commit", "-m", args.message],
    ]
    if not args.no_push:
        cmds.append(["git", "push"])
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=Path.cwd())
        if result.returncode != 0:
            print(f"failed: {' '.join(cmd)}", file=sys.stderr)
            return result.returncode
    return 0


# ---- FR-0410: create-issues ----

RE_FR_ANCHOR = re.compile(r'<a\s+id="fr-(\d{4})"></a>', re.I)
RE_FR_HEADING = re.compile(r"^###\s+(FR|NFR)-(\d{4})\s+([^\n]+)$", re.MULTILINE)
RE_AC_ANCHOR = re.compile(r'<a\s+id="ac-(fr|nfr)-(\d{4})"></a>', re.I)


def _spec_anchor_fragment(fr_id: str) -> str:
    """Return the lowercase spec.md anchor fragment for a requirement id.

    Args:
        fr_id: requirement id of the form ``FR-XXXX`` or ``NFR-XXXX``.

    Returns:
        The lowercase anchor fragment, e.g. ``"fr-0001"`` or ``"nfr-0002"``.

    Raises:
        ValueError: if ``fr_id`` does not match ``^(FR|NFR)-\\d{4}$``.
    """
    m = re.match(r"^(FR|NFR)-(\d{4})$", fr_id)
    if not m:
        raise ValueError(f"invalid requirement id: {fr_id!r}")
    return f"{m.group(1).lower()}-{m.group(2)}"


def _read_project_info_value(label: str) -> str:
    # fix-002: delegate to _common. project.toml replaces project-info.md.
    from ._common import _read_project_info_field

    return _read_project_info_field(label)


def _find_spec_path(args) -> Path:
    if args.spec_file:
        candidate = Path(args.spec_file)
        if not candidate.exists():
            candidate = resolve_existing_path(args.spec_file)
        return Path(candidate)
    default = Path(f".louke/project/specs/{args.spec}/spec.md")
    if default.exists():
        return default
    return resolve_existing_path(args.spec)


def _extract_frs(spec_text: str) -> list[tuple[str, str]]:
    """Return list of (fr_id, title)."""
    frs = []
    seen = set()
    for m in RE_FR_HEADING.finditer(spec_text):
        prefix, num, title = m.group(1), m.group(2), m.group(3).strip()
        fr_id = f"{prefix}-{num}"
        if fr_id in seen:
            continue
        seen.add(fr_id)
        frs.append((fr_id, title))
    return frs


def _acceptance_spec_text(spec_id: str) -> str:
    acc_path = Path(f".louke/project/specs/{spec_id}/acceptance.md")
    return acc_path.read_text(encoding="utf-8") if acc_path.exists() else ""


def _decide_ac_value(
    fr_id: str, spec_id: str, spec_text: str, acc_text: str, branch: str, repo_url: str
) -> str:
    """Decide the Acceptance Criteria field value for an issue body.

    Prefers an acceptance.md AC anchor when present, then falls back to a
    spec.md section anchor, finally returning the literal ``"None"``.

    Args:
        fr_id: requirement id (``FR-XXXX`` or ``NFR-XXXX``).
        spec_id: spec id used in the URL path.
        spec_text: spec.md source text (used for the spec anchor fallback).
        acc_text: acceptance.md source text (used for the AC anchor path).
        branch: git branch used in the URL path.
        repo_url: fully-qualified repo URL prefix, or empty for relative paths.

    Returns:
        The AC field value (a URL or the literal ``"None"``).
    """
    num = fr_id.split("-")[1]
    prefix = fr_id.split("-")[0].lower()
    if RE_AC_ANCHOR.search(acc_text):
        if repo_url:
            return f"{repo_url}/blob/{branch}/.louke/project/specs/{spec_id}/acceptance.md#ac-{prefix}-{num}"
        return f".louke/project/specs/{spec_id}/acceptance.md#ac-{prefix}-{num}"
    if re.search(rf'<a\s+id="{prefix}-{num}"></a>', spec_text):
        if repo_url:
            return f"{repo_url}/blob/{branch}/.louke/project/specs/{spec_id}/spec.md#{prefix}-{num}"
        return f"spec.md#{prefix}-{num}"
    return "None"


def _gh_list_issues_with_fr(repo, fr_id, spec_id=None):
    """Return issues whose title contains ``[FR-XXXX]`` (or any ``[XX-XXXX]``).

    When ``spec_id`` is provided, only issues whose ``Spec Link`` body field
    references ``.louke/project/specs/{spec_id}/spec.md`` are returned. This
    prevents cross-version false positives (e.g. v0.12 FR-1301 vs v0.13
    FR-1301) when two specs happen to share an FR number. The body fetch
    incurs one extra GraphQL field per matching issue; the search itself is
    still title-only because GitHub's ``gh issue list --search`` cannot
    filter on body content.
    """
    try:
        out = subprocess.check_output(
            [
                "gh",
                "issue",
                "list",
                "--repo",
                repo,
                "--state",
                "all",
                "--search",
                f"in:title [{fr_id}]",
                "--json",
                "number,title,url,body",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        issues = json.loads(out) or []
    except Exception:
        return []
    if spec_id is None:
        return issues
    # Filter by Spec Link body field so we only treat issues as "exists"
    # for *this* spec, not for a different version that shares the FR number.
    needle = f"/specs/{spec_id}/spec.md"
    return [i for i in issues if needle in (i.get("body") or "")]


def _gh_create_issue(repo, title, body):
    try:
        out = subprocess.check_output(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                repo,
                "--title",
                title,
                "--label",
                "Feature",
                "--body",
                body,
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        m = re.search(r"/issues/(\d+)", out)
        return f"https://github.com/{repo}/issues/{m.group(1)}" if m else out.strip()
    except subprocess.CalledProcessError as e:
        print(
            f"gh issue create failed for {title}: {(e.stderr or e.stdout)[:200]}",
            file=sys.stderr,
        )
        return None


def _gh_link_to_project(project_url, issue_url):
    """Link an issue to a Project.

    ``project_url`` may be either a GitHub project URL like
    ``https://github.com/users/<owner>/projects/<N>`` or a bare
    ``<N>``. Modern ``gh project item-add`` only accepts a numeric project
    number as the positional argument, so we always extract owner + number
    and call ``gh project item-add <N> --owner <owner> --url <issue>``.
    """
    number, owner = _parse_project_url_local(project_url)
    if not number:
        # Fall back: caller passed a bare number string.
        number = str(project_url).strip()
    cmd = ["gh", "project", "item-add", number, "--url", issue_url]
    if owner:
        cmd += ["--owner", owner]
    try:
        subprocess.run(
            cmd,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(
            f"gh project item-add failed: {(e.stderr or e.stdout)[:200]}",
            file=sys.stderr,
        )
        return False


def _parse_project_url_local(project_url):
    """Local copy of URL-parsing logic; kept in sync with ``louke.lex._parse_project_url``.

    We do not import from ``louke.lex`` to avoid a potential circular import
    (lex already imports several louke internals). The logic is identical to
    the Lex helper so the two stay in step.
    """
    if not project_url:
        return None, None
    m_num = re.search(r"/projects/(\d+)", project_url)
    if not m_num:
        return None, None
    m_path = re.search(r"github\.com/(.+)", project_url)
    if not m_path:
        return None, None
    segments = m_path.group(1).split("/")
    if len(segments) < 3 or "projects" not in segments:
        return None, None
    if segments[0] == "users":
        owner = segments[1]
    else:
        owner = segments[0]
    return m_num.group(1), owner


def cmd_create_issues(args):
    """FR-0410: create GitHub issues from spec.md FR anchors (4-digit schema)."""
    spec_path = _find_spec_path(args)
    if not spec_path.exists():
        print(f"spec file not found: {args.spec_file or args.spec}", file=sys.stderr)
        return 1
    spec_text = spec_path.read_text(encoding="utf-8", errors="replace")
    frs = _extract_frs(spec_text)
    if not frs:
        print("0 created, 0 skipped")
        return 0
    acc_text = _acceptance_spec_text(args.spec)
    repo = _read_project_info_value("Repo").replace("github.com/", "")
    if not repo:
        print(
            f"Repo field missing in project.toml; run the {RUNTIME_FOUNDATION_PROGRAM} first",
            file=sys.stderr,
        )
        return 1
    branch = _read_project_info_value("Release Branch")
    if not branch:
        print(
            f"Release Branch field missing in project.toml; run the {RUNTIME_FOUNDATION_PROGRAM} first",
            file=sys.stderr,
        )
        return 1
    project_url = _read_project_info_value("Project ID")
    if not project_url and not args.skip_project:
        print(
            "Project URL field missing in project.toml; cannot link issues",
            file=sys.stderr,
        )
        print(
            f"  hint: run the {RUNTIME_FOUNDATION_PROGRAM} (writes Project ID) or pass --skip-project",
            file=sys.stderr,
        )
        return 1
    repo_url = f"https://github.com/{repo}"
    created, skipped, linked = 0, 0, 0
    for fr_id, title in frs:
        existing = _gh_list_issues_with_fr(repo, fr_id, spec_id=args.spec)
        if existing:
            skipped += 1
            print(f"[-] {fr_id} {existing[0].get('number', '?')} (exists)")
            continue
        ac_value = _decide_ac_value(
            fr_id, args.spec, spec_text, acc_text, branch, repo_url
        )
        body = (
            f"### Requirement ID\n{fr_id}\n\n"
            f"### Spec Link\n{repo_url}/blob/{branch}/.louke/project/specs/{args.spec}/spec.md#{_spec_anchor_fragment(fr_id)}\n\n"
            f"### Acceptance Criteria\n{ac_value}\n"
        )
        if args.dry_run:
            print(f"[+] {fr_id} {title!r} body len={len(body)}")
            created += 1
            continue
        issue_url = _gh_create_issue(repo, f"[{fr_id}] {title}", body)
        if not issue_url:
            continue
        created += 1
        print(f"[+] {fr_id} -> {issue_url}")
        if project_url and _gh_link_to_project(project_url, issue_url):
            linked += 1
    print(f"{created} created, {skipped} skipped, {linked} linked")
    return 0


def cmd_lock_spec(args):
    """Backward-compatible alias for record-lock requiring manual confirmation outside CLI."""
    print("lock-spec is deprecated; use record-lock --confirm", file=sys.stderr)
    return cmd_record_lock(argparse.Namespace(spec=args.spec, confirm=False))


def _run_lk(*args, cwd=None) -> int:
    return subprocess.run(
        [sys.executable, "-m", "louke.__main__", "agent", *args], cwd=cwd or Path.cwd()
    ).returncode


def cmd_record_lock(args):
    """FR-0420: 3-signal lock record. lock: true is a result, not a signal.

    FR-0060 v0.7-003: Sage signal uses inline-discussion protocol (call discuss.is_ready).
    """
    if not args.confirm:
        print(
            "User signal missing: pass --confirm after IDE confirmation",
            file=sys.stderr,
        )
        return 1
    # Sage signal (FR-0060: uses inline-discussion)
    spec_path = Path(f".louke/project/specs/{args.spec}/spec.md")
    if not spec_path.exists():
        spec_path = resolve_existing_path(args.spec)
    if spec_path is None or not spec_path.exists():
        print(f"spec not found: {args.spec}", file=sys.stderr)
        return 1
    from ._tools import discuss as _discuss

    design_docs = [
        spec_path,
        spec_path.parent / "architecture.md",
        spec_path.parent / "interfaces.md",
        spec_path.parent / "test-plan.md",
    ]
    existing_docs = [p for p in design_docs if p.exists()]
    all_blockers = []
    ready = True
    for p in existing_docs:
        r = _discuss.DiscussParser().parse_file(p)
        if not r.is_ready:
            ready = False
            for b in r.ready_blockers:
                all_blockers.append(f"[{p.name}] {b}")
    if not ready:
        print(
            "Sage signal: not passed (inline-discussion is_ready=False)",
            file=sys.stderr,
        )
        for b in all_blockers:
            print(f"  {b}", file=sys.stderr)
        return 1
    # Lex signal
    for sub in (
        ["lex", "verify-acceptance", "--spec", args.spec],
        ["lex", "verify-issue", "--spec", args.spec],
        ["lex", "verify-project", "--spec", args.spec],
    ):
        rc = _run_lk(*sub)
        if rc != 0:
            print(f"Lex signal: {sub[1]} failed (rc={rc})", file=sys.stderr)
            return rc
    text = spec_path.read_text(encoding="utf-8")
    text, locked_already = _apply_lock_to_frontmatter(text)
    if locked_already:
        print(f"spec already locked; idempotent (spec={args.spec})")
        return 0
    spec_path.write_text(text, encoding="utf-8")
    print(f"locked: true ({args.spec})")
    return 0


def _apply_lock_to_frontmatter(text):
    """Return ``(new_text, locked_already)`` with the YAML frontmatter in canonical form.

    Rules (bug fix for the frontmatter duplication observed when the spec
    already declares ``locked: false`` / ``locked-at:`` / ``locked-by:``
    placeholder keys):

    * If frontmatter exists and already says ``locked: true`` → return text
      unchanged and ``locked_already=True``.
    * If frontmatter exists but does NOT yet say ``locked: true`` → rewrite
      the frontmatter to a single canonical block containing exactly the
      three ``locked*`` keys (stripping any pre-existing duplicate keys).
    * If no frontmatter → prepend a canonical frontmatter block.

    The result always contains exactly one ``---\\n...\\n---\\n`` block at
    the top of the file (or none, only when ``locked_already=True`` and the
    file happens to lack frontmatter, which we treat as a no-op).
    """
    canonical = (
        "---\n"
        f"locked: true\n"
        f"locked-at: {datetime_now()}\n"
        f"locked-by: lk agent sage record-lock\n"
        "---\n"
    )
    if not text.startswith("---\n"):
        return canonical + text, False
    end = text.find("\n---\n", 4)
    if end == -1:
        # Malformed: opens with --- but never closes. Prepend canonical.
        return canonical + text, False
    fm = text[4:end]
    if re.search(r"^locked:\s*true\s*$", fm, re.MULTILINE):
        return text, True
    # Strip any pre-existing locked* placeholder keys, then rebuild.
    kept_lines = [
        line for line in fm.splitlines() if not re.match(r"^locked(-at|-by)?:\s*", line)
    ]
    rebuilt_fm = "\n".join(kept_lines)
    if rebuilt_fm.strip():
        rebuilt = (
            "---\n"
            + rebuilt_fm
            + f"\nlocked: true\nlocked-at: {datetime_now()}\nlocked-by: lk agent sage record-lock\n---\n"
        )
    else:
        rebuilt = canonical
    new_text = rebuilt + text[end + len("\n---\n") :]
    return new_text, False


def datetime_now():
    from datetime import datetime

    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
