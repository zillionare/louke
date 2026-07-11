#!/usr/bin/env python3
"""
verify_issue_schema.py — validate the schema compliance of GitHub Feature issues

This is the gate script run after Lex/Sage create issues. It treats "does the issue
contain machine-readable structured data" as the single invariant to check; all
Archer/Devon/Keeper depend on this invariant.

Design goals:
- Zero LLM tokens: pure structural checks, any C-tier or lower model can run it
- Zero extra dependencies: Python stdlib only
- Offline-testable: supports --offline + fixture files, bats can feed samples directly

Checks (L1-L8):
  L1 Title format:    ^\\[FR-\\d{4}\\]
  L2 Requirement ID field: present and matches ^FR-\\d{4}$
  L3 Spec URL field: present and matches ^https://github.com/.../spec(-\\w+)?\\.md#(fr|nfr)-\\d{4}$
                  (supports single-file spec.md and multi-volume spec-{name}.md)
  L4 Spec reachable:  gh api can fetch the spec source (tries both /specs/{id}/ and /{id}/ layouts)
  L5 Anchor exists:    spec contains <a id="fr-XXXX"></a>
  L6 Anchor content:   the anchor context contains "FR-XXXX" (prevents anchor misuse)
  L7 AC anchor:       the acceptance criteria field supports three forms (v0.5-006):
                  a) acceptance.md#ac-fr-XXXXX URL (default, backward compatible)
                  b) spec(-vol)?.md#fr-XXXX URL (AC inside a spec section, falls through L4-L6)
                  c) literal "None" + acceptance.md ## No Acceptance list contains this FR
  L8 Bidirectional coverage: every FR in the spec has an issue; every FR in issues exists in the spec

Usage:
  python louke/_tools/verify_issue_schema.py --spec v0.1-001-louke
  python louke/_tools/verify_issue_schema.py --spec v0.1-001-louke --repo owner/repo
  python louke/_tools/verify_issue_schema.py --offline \\
      --spec-file .louke/project/specs/v0.1-001-louke/spec.md \\
      --issues-json /tmp/issues.json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------- Regex definitions (single source of truth) ----------

RE_FR_ID = re.compile(r"^(FR|NFR)-\d{4}$")
RE_FR_IN_TITLE = re.compile(r"^\[(FR|NFR)-(\d{4})\]")
# spec file path: supports single file (spec.md) and multi-volume (spec-{name}.md)
# directory: /specs/{id}/ (spec 004 default) or /{id}/ (some projects, e.g. millionaire)
RE_SPEC_URL = re.compile(
    r"^https://github\.com/"
    r"(?P<owner>[A-Za-z0-9._-]+)/(?P<repo>[A-Za-z0-9._-]+)/blob/"
    r"(?P<branch>[A-Za-z0-9._/-]+)"
    r"/\.louke/project/(?:specs/)?(?P<spec_id>[A-Za-z0-9._-]+)/spec(?P<vol_suffix>-\w+)?\.md"
    r"#(?P<fragment>(?:fr|nfr)-\d{4})$"
)
# acceptance.md has no vol_suffix: one acceptance.md per spec-id
RE_AC_URL = re.compile(
    r"^https://github\.com/"
    r"(?P<owner>[A-Za-z0-9._-]+)/(?P<repo>[A-Za-z0-9._-]+)/blob/"
    r"(?P<branch>[A-Za-z0-9._/-]+)"
    r"/\.louke/project/(?:specs/)?(?P<spec_id>[A-Za-z0-9._-]+)/acceptance\.md"
    r"#(?P<fragment>ac-(?:fr|nfr)-\d{4})$"
)
RE_ANCHOR = re.compile(r'<a\s+id="((?:fr|nfr)-\d{4})"></a>')
RE_AC_ANCHOR = re.compile(r'<a\s+id="(ac-(?:fr|nfr)-\d{4})"></a>')
RE_AC_LINE = re.compile(r"^AC-\d+:\s*\S+")
RE_AC_FULL = re.compile(r"^AC-(\d+):\s*(.+)$")
# v0.5-006: literal "None" goes through the No Acceptance list (## No Acceptance section of acceptance.md)
RE_NO_AC_HEADER = re.compile(r"^##\s+No\s+Acceptance\s*$")
RE_NO_AC_ITEM = re.compile(r"^\s*-\s+((?:FR|NFR)-\d{4})\b")

# Field titles after issue form rendering (must match .github/ISSUE_TEMPLATE/feature.yml)
FIELD_FR_ID = "Requirement ID"
FIELD_SPEC_URL = "Spec Link"
FIELD_AC = "Acceptance Criteria"


# ---------- Data structures ----------


@dataclass
class IssueCheck:
    number: int
    title: str
    fr_id: str = ""
    spec_url: str = ""
    spec_url_parsed: dict = field(default_factory=dict)
    ac_url: str = ""
    ac_url_parsed: dict = field(default_factory=dict)
    ac_lines: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


# ---------- Parse issue body ----------


def parse_issue_form(body: str) -> dict[str, str]:
    """
    Extract field values from the markdown rendered by the issue form.

    GitHub renders form fields as:
        ### Requirement ID
        FR-0001

        ### Spec Link
        https://.../spec.md#fr-0001

        ### Acceptance Criteria
        https://.../acceptance.md#ac-fr-0001
    """
    fields: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            if current is not None:
                fields[current] = "\n".join(buf).strip()
            current = m.group(1).strip()
            buf = []
        else:
            if current is not None:
                buf.append(line)
    if current is not None:
        fields[current] = "\n".join(buf).strip()
    return fields


# ---------- Checks ----------


def check_issue(issue: dict[str, Any], spec_cache: dict[str, str]) -> IssueCheck:
    """Run L1-L7 for a single issue, return check result (spec_cache is reused across calls for L4-L6)."""
    ic = IssueCheck(number=issue["number"], title=issue["title"])
    body = issue.get("body") or ""

    # L1: Title
    m = RE_FR_IN_TITLE.match(ic.title)
    if not m:
        ic.failures.append(
            f"L1 title must start with [FR-XXXX] or [NFR-XXXXX], got: {ic.title!r}"
        )
    else:
        ic.fr_id = m.group(1) + "-" + m.group(2)

    # Parse form fields
    fields = parse_issue_form(body)

    # L2: Requirement ID field
    raw_fr = fields.get(FIELD_FR_ID, "").strip()
    if not raw_fr:
        ic.failures.append(f"L2 field '{FIELD_FR_ID}' missing")
    elif not RE_FR_ID.match(raw_fr):
        ic.failures.append(
            f"L2 field '{FIELD_FR_ID}' has invalid format, expected ^(FR|NFR)-\\d{{3}}$, got: {raw_fr!r}"
        )
    elif ic.fr_id and raw_fr != ic.fr_id:
        ic.failures.append(
            f"L2 field '{FIELD_FR_ID}' ({raw_fr}) does not match title [{ic.fr_id}]"
        )
    else:
        ic.fr_id = raw_fr

    # L3: Spec URL field
    raw_url = fields.get(FIELD_SPEC_URL, "").strip()
    if not raw_url:
        ic.failures.append(f"L3 field '{FIELD_SPEC_URL}' missing")
    else:
        m = RE_SPEC_URL.match(raw_url)
        if not m:
            ic.failures.append(
                f"L3 field '{FIELD_SPEC_URL}' has invalid format, expected a full GitHub URL "
                f"+ #fr-XXXX (lowercase) or #nfr-XXXX (lowercase), got: {raw_url!r}"
            )
        else:
            ic.spec_url = raw_url
            ic.spec_url_parsed = m.groupdict()
            expected_fragment = (
                raw_fr.split("-")[0].lower() + "-" + raw_fr.split("-")[1]
                if raw_fr
                else ""
            )
            if m.group("fragment") != expected_fragment:
                ic.failures.append(
                    f"L3 URL fragment {m.group('fragment')!r} does not match requirement ID {raw_fr!r} "
                    f"(should be #{expected_fragment!r})"
                )

            # L4-L6: spec reachable + anchor exists + content matches
            if "OFFLINE" in spec_cache:
                # Offline mode: reuse fixture spec
                spec_text = spec_cache["OFFLINE"]
            else:
                spec_filename = f"spec{m.group('vol_suffix') or ''}.md"
                spec_key = f"{m.group('owner')}/{m.group('repo')}@{m.group('branch')}:{m.group('spec_id')}/{spec_filename}"
                if spec_key not in spec_cache:
                    spec_cache[spec_key] = fetch_spec_markdown(
                        m.group("owner"),
                        m.group("repo"),
                        m.group("branch"),
                        m.group("spec_id"),
                        spec_filename,
                    )
                spec_text = spec_cache[spec_key]

            if spec_text is None:
                spec_filename = f"spec{m.group('vol_suffix') or ''}.md"
                ic.failures.append(
                    f"L4 unable to fetch spec file .louke/project/(specs/)?{m.group('spec_id')}/{spec_filename} "
                    f"(repo {m.group('owner')}/{m.group('repo')}@{m.group('branch')})"
                )
            else:
                anchors = RE_ANCHOR.findall(spec_text)
                if m.group("fragment") not in anchors:
                    ic.failures.append(
                        f"L5 anchor {m.group('fragment')!r} not found in spec.md; "
                        f"declared FR anchors: {sorted(set(anchors))}"
                    )
                else:
                    # L6: anchor context (anchor line + next 5 lines) must contain "FR-XXXX"
                    lines = spec_text.splitlines()
                    for i, line in enumerate(lines):
                        if f'<a id="{m.group("fragment")}">' in line:
                            context = "\n".join(lines[i : i + 6])
                            if raw_fr not in context:
                                ic.failures.append(
                                    f"L6 {raw_fr!r} not found around anchor {m.group('fragment')!r}; "
                                    f"the anchor may have been misused. Context:\n{context}"
                                )
                            break

    # L7: Acceptance Criteria field — supports three forms (v0.5-006):
    #   a) acceptance.md#ac-fr-XXXXX URL (default, backward compatible)
    #   b) spec(-vol)?.md#fr-XXXX URL (AC inside a spec section)
    #   c) literal "None" (FR listed in acceptance.md ## No Acceptance)
    raw_ac = fields.get(FIELD_AC, "").strip()
    if not raw_ac:
        ic.failures.append(f"L7 field '{FIELD_AC}' missing")
    elif raw_ac.lower() in ("无", "none"):
        # (c) No Acceptance mode
        check_no_acceptance(ic, raw_ac, raw_fr, spec_cache)
    elif RE_SPEC_URL.match(raw_ac):
        # (b) spec-fragment mode — reuse L3-L6 spec text cache
        check_spec_fragment_ac(ic, raw_ac, raw_fr, spec_cache)
    elif RE_AC_URL.match(raw_ac):
        # (a) acceptance.md URL mode (backward compatible)
        check_acceptance_url(ic, raw_ac, raw_fr, spec_cache)
    else:
        ic.failures.append(
            f"L7 field '{FIELD_AC}' has invalid format; expected one of:\n"
            f"  1) acceptance.md#ac-fr-XXXXX URL (default, with dedicated AC section)\n"
            f"  2) spec(-vol)?.md#fr-XXXX URL (AC in spec section)\n"
            f"  3) literal value 'None' (FR listed in acceptance.md ## No Acceptance)\n"
            f"actual: {raw_ac!r}"
        )

    return ic


# ---------- L7 sub-checks (split in v0.5-006 for easier testing and maintenance) ----------


def check_acceptance_url(
    ic: IssueCheck,
    raw_ac: str,
    raw_fr: str,
    spec_cache: dict[str, str],
) -> None:
    """L7 form (a): acceptance.md#ac-fr-XXXXX URL (default, backward compatible)"""
    m = RE_AC_URL.match(raw_ac)
    if not m:
        ic.failures.append(
            f"L7 field '{FIELD_AC}' has invalid format, expected a full GitHub URL "
            f"+ #ac-fr-XXXXX or #ac-nfr-XXXX (lowercase), got: {raw_ac!r}"
        )
        return
    ic.ac_url = raw_ac
    ic.ac_url_parsed = m.groupdict()
    expected_frag = (
        "ac-" + (raw_fr.split("-")[0].lower() + "-" + raw_fr.split("-")[1])
        if raw_fr
        else ""
    )
    if m.group("fragment") != expected_frag:
        ic.failures.append(
            f"L7 URL fragment {m.group('fragment')!r} does not match requirement ID {raw_fr!r} "
            f"(should be #{expected_frag!r})"
        )

    # Fetch acceptance.md to validate the anchor
    if "OFFLINE" in spec_cache and "OFFLINE_ACC" in spec_cache:
        acc_text = spec_cache["OFFLINE_ACC"]
    else:
        acc_key = f"{m.group('owner')}/{m.group('repo')}@{m.group('branch')}:{m.group('spec_id')}"
        if acc_key not in spec_cache:
            spec_cache[acc_key] = fetch_acceptance_markdown(
                m.group("owner"),
                m.group("repo"),
                m.group("branch"),
                m.group("spec_id"),
            )
        acc_text = spec_cache[acc_key]

    if acc_text is None:
        ic.failures.append(
            f"L7 unable to fetch acceptance file .louke/project/(specs/)?{m.group('spec_id')}/acceptance.md "
            f"(repo {m.group('owner')}/{m.group('repo')}@{m.group('branch')})"
        )
        return

    acc_anchors = RE_AC_ANCHOR.findall(acc_text)
    if m.group("fragment") not in acc_anchors:
        ic.failures.append(
            f"L7 anchor {m.group('fragment')!r} not found in acceptance.md; "
            f"declared AC anchors: {sorted(set(acc_anchors))}"
        )
        return

    # Anchor context (anchor line + next 8 lines) must contain "FR-XXXX"
    lines = acc_text.splitlines()
    for i, line in enumerate(lines):
        if f'<a id="{m.group("fragment")}">' in line:
            context = "\n".join(lines[i : i + 9])
            if raw_fr not in context:
                ic.failures.append(
                    f"L7 {raw_fr!r} not found around anchor {m.group('fragment')!r}; "
                    f"the anchor may have been misused. Context:\n{context}"
                )
            break


def check_spec_fragment_ac(
    ic: IssueCheck,
    raw_ac: str,
    raw_fr: str,
    spec_cache: dict[str, str],
) -> None:
    """L7 form (b): spec(-vol)?.md#fr-XXXX URL (AC inside a spec section)

    Reuses the spec text cache from L3-L6: L3 already stored the same spec in spec_cache
    (possibly with a different vol_suffix, but the same spec_id usually points to the same file);
    here we rerun L5+L6 validation.
    """
    m = RE_SPEC_URL.match(raw_ac)
    if not m:
        # In theory RE_SPEC_URL.match already passed above; this is a second safety net
        ic.failures.append(f"L7 spec-fragment URL parse failed: {raw_ac!r}")
        return

    spec_text = _get_spec_text(
        spec_cache,
        m.group("owner"),
        m.group("repo"),
        m.group("branch"),
        m.group("spec_id"),
        m.group("vol_suffix") or "",
    )
    if spec_text is None:
        ic.failures.append(
            f"L7 spec-fragment URL unable to fetch spec source "
            f".louke/project/(specs/)?{m.group('spec_id')}/spec{m.group('vol_suffix') or ''}.md "
            f"(repo {m.group('owner')}/{m.group('repo')}@{m.group('branch')})"
        )
        return

    anchors = RE_ANCHOR.findall(spec_text)
    if m.group("fragment") not in anchors:
        ic.failures.append(
            f"L7 spec-fragment URL fragment {m.group('fragment')!r} not found in spec; "
            f"declared FR anchors: {sorted(set(anchors))}"
        )
        return

    # Anchor context must contain raw_fr (same as L6)
    lines = spec_text.splitlines()
    for i, line in enumerate(lines):
        if f'<a id="{m.group("fragment")}">' in line:
            context = "\n".join(lines[i : i + 6])
            if raw_fr not in context:
                ic.failures.append(
                    f"L7 {raw_fr!r} not found around spec-fragment anchor {m.group('fragment')!r}; "
                    f"the anchor may have been misused. Context:\n{context}"
                )
            break

    # Record parsed result (used by report)
    ic.ac_url = raw_ac
    ic.ac_url_parsed = m.groupdict()


def check_no_acceptance(
    ic: IssueCheck,
    raw_ac: str,
    raw_fr: str,
    spec_cache: dict[str, str],
) -> None:
    """L7 form (c): literal 'None' — verify acceptance.md ## No Acceptance list contains this FR.

    The No Acceptance list in acceptance.md is the single authoritative source
    for declaring "this FR has no dedicated AC".
    """
    # Get acceptance.md text
    if "OFFLINE" in spec_cache and "OFFLINE_ACC" in spec_cache:
        acc_text = spec_cache["OFFLINE_ACC"]
    else:
        # In L7 (a) mode acceptance.md is already in spec_cache; here it is first access, need to fetch.
        # owner/repo/branch/spec_id are unknown; use what was previously stored in ic; if missing, error out.
        # Production path: use ic.spec_url_parsed
        if not ic.spec_url_parsed:
            ic.failures.append(
                "L7 field 'None' requires the Spec Link field (L3) to be parsed "
                "first to locate acceptance.md; please provide a valid Spec URL"
            )
            return
        p = ic.spec_url_parsed
        acc_key = f"{p['owner']}/{p['repo']}@{p['branch']}:{p['spec_id']}"
        if acc_key not in spec_cache:
            spec_cache[acc_key] = fetch_acceptance_markdown(
                p["owner"],
                p["repo"],
                p["branch"],
                p["spec_id"],
            )
        acc_text = spec_cache[acc_key]

    if acc_text is None:
        ic.failures.append(
            "L7 field 'None' requires acceptance.md to exist "
            "(to declare the '## No Acceptance' list); unable to fetch acceptance.md"
        )
        return

    no_acc_frs = parse_no_acceptance_list(acc_text)
    if raw_fr not in no_acc_frs:
        # Distinguish two failure causes for more precise hints
        if "## No Acceptance" not in acc_text and "No Acceptance" not in acc_text:
            ic.failures.append(
                "L7 field 'None' indicates no dedicated acceptance, "
                "but the '## No Acceptance' section cannot be found in acceptance.md; "
                f"please append that section to acceptance.md and add {raw_fr!r} to the list"
            )
        else:
            listed = sorted(no_acc_frs) if no_acc_frs else "(empty)"
            ic.failures.append(
                f"L7 field 'None' but {raw_fr!r} not found in the "
                "'## No Acceptance' list of acceptance.md; "
                f"FRs already listed in No Acceptance: {listed}. "
                f"Please add {raw_fr!r} to that list, "
                "or switch to an acceptance.md#ac-fr-XXXXX URL"
            )

    # Record parsed result
    ic.ac_url = "None"
    ic.ac_url_parsed = {"mode": "no_acceptance"}


def parse_no_acceptance_list(acc_text: str) -> set[str]:
    """Extract the FR list from the '## No Acceptance' section of acceptance.md.

    Each line in the section looks like '- FR-XXXX' or '- FR-XXXX (description)'; take the first token as fr_id.
    """
    frs: set[str] = set()
    in_section = False
    for line in acc_text.splitlines():
        if RE_NO_AC_HEADER.match(line):
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            m = RE_NO_AC_ITEM.match(line)
            if m:
                frs.add(m.group(1))
    return frs


def _get_spec_text(
    spec_cache: dict[str, str],
    owner: str,
    repo: str,
    branch: str,
    spec_id: str,
    vol_suffix: str,
) -> str | None:
    """Reuse the L3 spec text cache"""
    if "OFFLINE" in spec_cache:
        return spec_cache["OFFLINE"]
    spec_filename = f"spec{vol_suffix}.md"
    spec_key = f"{owner}/{repo}@{branch}:{spec_id}/{spec_filename}"
    if spec_key not in spec_cache:
        spec_cache[spec_key] = fetch_spec_markdown(
            owner,
            repo,
            branch,
            spec_id,
            spec_filename,
        )
    return spec_cache[spec_key]


def fetch_spec_markdown(
    owner: str, repo: str, branch: str, spec_id: str, spec_filename: str = "spec.md"
) -> str | None:
    """
    Fetch the spec source via gh api. Returns None on fetch failure.
    gh api handles auth for both public and private repos.

    spec_filename: defaults to spec.md; for multi-volume it is spec-{vol}.md (e.g. spec-strategy.md).
    Tries both directory layouts: /specs/{id}/ (spec 004+) and /{id}/ (some projects).
    """
    candidates = [
        f".louke/project/specs/{spec_id}/{spec_filename}",
        f".louke/project/{spec_id}/{spec_filename}",
    ]
    last_err: str | None = None
    for path in candidates:
        try:
            out = subprocess.check_output(
                [
                    "gh",
                    "api",
                    f"repos/{owner}/{repo}/contents/{path}",
                    "-H",
                    "Accept: application/vnd.github.raw",
                    "--method",
                    "GET",
                    "--field",
                    f"ref={branch}",
                ],
                stderr=subprocess.STDOUT,
            )
            return out.decode("utf-8", errors="replace")
        except subprocess.CalledProcessError as e:
            last_err = e.output.decode(errors="replace")
            continue
    if last_err:
        sys.stderr.write(
            f"[warn] gh api failed for {owner}/{repo}@{branch}: tried {candidates}\n"
            f"       {last_err}\n"
        )
    return None


def fetch_acceptance_markdown(
    owner: str, repo: str, branch: str, spec_id: str
) -> str | None:
    """Fetch the acceptance.md source via gh api. Returns None on fetch failure.

    Also tries both directory layouts: /specs/{id}/ and /{id}/.
    """
    candidates = [
        f".louke/project/specs/{spec_id}/acceptance.md",
        f".louke/project/{spec_id}/acceptance.md",
    ]
    last_err: str | None = None
    for path in candidates:
        try:
            out = subprocess.check_output(
                [
                    "gh",
                    "api",
                    f"repos/{owner}/{repo}/contents/{path}",
                    "-H",
                    "Accept: application/vnd.github.raw",
                    "--method",
                    "GET",
                    "--field",
                    f"ref={branch}",
                ],
                stderr=subprocess.STDOUT,
            )
            return out.decode("utf-8", errors="replace")
        except subprocess.CalledProcessError as e:
            last_err = e.output.decode(errors="replace")
            continue
    if last_err:
        sys.stderr.write(
            f"[warn] gh api failed for {owner}/{repo}@{branch}: tried {candidates}\n"
            f"       {last_err}\n"
        )
    return None


# ---------- Report ----------


def report(checks: list[IssueCheck], spec_frs: set[str] | None) -> int:
    ok = [c for c in checks if c.ok]
    bad = [c for c in checks if not c.ok]
    print(
        f"\nSummary: {len(checks)} Feature issues validated, {len(ok)} PASS, {len(bad)} FAIL\n"
    )

    if bad:
        print("[REJECT]\n")
        for c in bad:
            print(f"Issue #{c.number}  {c.title}")
            for f in c.failures:
                print(f"  - {f}")
            print()
        # List at most 3 blocking issues (Lex style)
        flat = []
        for c in bad:
            for f in c.failures:
                flat.append((c, f))
        if len(flat) > 3:
            print(f"... and {len(flat) - 3} more issues (truncated in Lex style)\n")
        return 1

    # Bidirectional coverage
    if spec_frs is not None and checks:
        issue_frs = {c.fr_id for c in ok}
        orphans_in_spec = sorted(spec_frs - issue_frs)
        orphans_in_issues = sorted(issue_frs - spec_frs)
        if orphans_in_spec or orphans_in_issues:
            print("[REJECT] L8 bidirectional coverage failed\n")
            if orphans_in_spec:
                print(f"  - FRs in spec without a matching issue: {orphans_in_spec}")
            if orphans_in_issues:
                print(
                    f"  - issues referencing FRs not present in spec: {orphans_in_issues}"
                )
            print()
            return 1

    print("[PASS]\n")
    for c in checks:
        print(
            f"  Issue #{c.number}  {c.title}  "
            f"(AC anchor: {c.ac_url_parsed.get('fragment', '-')})"
        )
    return 0


# ---------- Entry point ----------


def load_issues_from_gh(repo: str) -> list[dict[str, Any]]:
    out = subprocess.check_output(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--label",
            "Feature",
            "--state",
            "all",
            "--json",
            "number,title,body,state",
            "--limit",
            "500",
        ]
    )
    return json.loads(out)


def load_spec_frs_from_gh(
    owner: str, repo: str, branch: str, spec_id: str
) -> set[str] | None:
    text = fetch_spec_markdown(owner, repo, branch, spec_id)
    if text is None:
        return None
    return {f"FR-{a.split('-')[1].zfill(3)}" for a in RE_ANCHOR.findall(text)}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", help="spec-id, e.g. v0.1-001-specforge")
    p.add_argument("--repo", help="owner/repo, inferred from gh repo view by default")
    p.add_argument(
        "--branch", help="default branch, inferred from gh repo view by default"
    )
    p.add_argument(
        "--offline",
        action="store_true",
        help="offline mode (for bats): use --spec-file + --acceptance-file + --issues-json",
    )
    p.add_argument("--spec-file", help="offline mode: path to spec.md")
    p.add_argument(
        "--acceptance-file",
        help="offline mode: path to acceptance.md (for L7 anchor validation)",
    )
    p.add_argument("--issues-json", help="offline mode: path to issue list JSON")
    args = p.parse_args()

    if args.offline:
        if not (args.spec_file and args.issues_json):
            sys.stderr.write("--offline requires --spec-file and --issues-json\n")
            return 2
        spec_text = Path(args.spec_file).read_text(encoding="utf-8")
        spec_frs = {
            f"FR-{a.split('-')[1].zfill(3)}" for a in RE_ANCHOR.findall(spec_text)
        }
        with open(args.issues_json, "r", encoding="utf-8") as f:
            issues = json.load(f)
        # Offline mode: any spec_url/ac_url is treated as pointing to the same fixture
        # (L4/L7 do not make network requests; L5/L6 use the spec fixture anchor table; L7 uses the acceptance fixture)
        spec_cache: dict[str, str] = {"OFFLINE": spec_text}
        if args.acceptance_file:
            acc_path = Path(args.acceptance_file)
            if acc_path.exists():
                spec_cache["OFFLINE_ACC"] = acc_path.read_text(encoding="utf-8")
    else:
        if not args.spec:
            sys.stderr.write("--spec is required (or use --offline)\n")
            return 2
        repo = args.repo
        branch = args.branch
        if not repo:
            repo = (
                subprocess.check_output(
                    [
                        "gh",
                        "repo",
                        "view",
                        "--json",
                        "nameWithOwner",
                        "-q",
                        ".nameWithOwner",
                    ]
                )
                .decode()
                .strip()
            )
        if not branch:
            branch = (
                subprocess.check_output(
                    [
                        "gh",
                        "repo",
                        "view",
                        repo,
                        "--json",
                        "defaultBranchRef",
                        "-q",
                        ".defaultBranchRef.name",
                    ]
                )
                .decode()
                .strip()
            )
        owner, reponame = repo.split("/", 1)
        spec_frs = load_spec_frs_from_gh(owner, reponame, branch, args.spec)
        issues = load_issues_from_gh(repo)
        spec_cache = {}

    checks = [check_issue(i, spec_cache) for i in issues]
    return report(checks, spec_frs)


if __name__ == "__main__":
    sys.exit(main())
