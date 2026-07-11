"""Maestro commands - flow advancement control.

Maestro responsibilities: coordinate all agents, monitor exit conditions,
decide advance/regress/escalate.
lk provides: status query + advance/regress/escalate operations.
"""

import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from ._common import git, raw_path, normalize_repo_relative_roots
from .stage_results import (
    artifact_path,
    compute_contract_bundle_hash,
    load_stage_result,
    write_stage_result,
    verify_stage_result_hash,
)


STAGES = [
    ("M-FULL", "full", None, None),
    ("M-FOUND", "foundation", "Scout", "Warden"),
    ("M-SPEC", "define requirements", "Sage", "Lex"),
    ("M-TESTPLAN", "define test plan", "Archer", "Sage"),
    ("M-ARCH", "architecture design", "Archer", "Prism"),
    ("M-LOCK", "requirement lock", "Maestro", "human"),
    ("M-DEV", "development execution", "Devon", "Prism -> Keeper"),
    ("M-E2E", "e2e development", "Shield", "Prism -> Keeper"),
    ("M-BUGFIX", "bug fix", "Devon", "Keeper"),
    ("M-SECURITY", "security audit", "Judge (S level)", "user"),
    ("M-MILESTONE", "milestone close", "Maestro", "human"),
]


def register(subparsers):
    parser = subparsers.add_parser("maestro", help="flow advancement control (Maestro)")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p = sub.add_parser("status", help="view current spec/milestone stage progress")
    p.add_argument("--spec", default="", help="spec-id (empty for full table)")

    p = sub.add_parser("advance", help="advance to next stage (FR-0700 auto holdpoint)")
    p.add_argument("--stage", required=True, help="current stage code, e.g. M-DEV")
    p.add_argument(
        "--spec-id", default="", help="target spec-id (required by some stages)"
    )
    p.add_argument(
        "--commit-range", default="HEAD~1..HEAD", help="used by M-DEV / M-E2E gate"
    )
    p.add_argument("--release", default="releases/v0.1", help="used by M-SECURITY")
    p.add_argument("--confirm", action="store_true", help="M-LOCK user confirmation")
    p.add_argument(
        "--force",
        action="store_true",
        help="skip automated exit-condition checks (manual confirmation scenario)",
    )

    p = sub.add_parser("regress", help="regress current stage")
    p.add_argument("--stage", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--spec-id", default="")

    p = sub.add_parser(
        "escalate",
        help="escalate to user (repeated no-response / fundamental requirement conflict)",
    )
    p.add_argument("--reason", required=True)
    p.add_argument("--agent", default="", help="which agent triggered escalation")

    p = sub.add_parser(
        "waive", help="write a waiver artifact for a forced stage advance"
    )
    p.add_argument("--stage", required=True)
    p.add_argument("--spec-id", required=True)
    p.add_argument("--reason", required=True)
    p.add_argument("--approved-by", required=True)
    p.add_argument("--commit-range", default="")
    p.add_argument("--accepted-risk", action="append", default=[])


def run(args):
    handlers = {
        "status": cmd_status,
        "advance": cmd_advance,
        "regress": cmd_regress,
        "escalate": cmd_escalate,
        "waive": cmd_waive,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def _read_project_info(label):
    # fix-002: delegate to _common. project.toml replaces project-info.md.
    from ._common import _read_project_info_field

    return _read_project_info_field(label)


def _set_project_info_current_stage(stage):
    path = Path(".louke/project/project.toml")
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    pattern = r'^(current_stage\s*=\s*)"[^"]*"'
    if re.search(pattern, text, flags=re.MULTILINE):
        escaped = stage.replace("\\", "\\\\").replace('"', '\\"')
        text = re.sub(pattern, rf'\1"{escaped}"', text, count=1, flags=re.MULTILINE)
        path.write_text(text, encoding="utf-8")


def _run_lk(*args):
    return subprocess.run(
        [sys.executable, "-m", "louke.__main__", "agent", *args], cwd=Path.cwd()
    ).returncode


def _require_stage_artifact(spec_id, stage, kind, role, verdict, metadata=None):
    path = artifact_path(spec_id, stage, kind)
    data = load_stage_result(spec_id, stage, kind)
    if not data:
        return False, f"missing artifact: {path}"
    if not verify_stage_result_hash(data):
        return False, f"artifact hash mismatch: {path}"
    if data.get("role") != role:
        return (
            False,
            f"artifact role mismatch in {path} (expected {role}, got {data.get('role')})",
        )
    if data.get("verdict") != verdict:
        return (
            False,
            f"artifact verdict mismatch in {path} (expected {verdict}, got {data.get('verdict')})",
        )
    current_bundle_hash = compute_contract_bundle_hash(spec_id)
    if data.get("contract_bundle_hash") != current_bundle_hash:
        return False, f"artifact contract bundle hash stale: {path}"
    for key, expected in (metadata or {}).items():
        actual = (data.get("metadata") or {}).get(key)
        if actual != expected:
            return (
                False,
                f"artifact metadata mismatch in {path}: {key} expected {expected!r}, got {actual!r}",
            )
    return True, f"artifact OK: {path}"


def _read_e2e_paths():
    from ._common import _toml_load, PROJECT_INFO_PATH

    data = _toml_load(PROJECT_INFO_PATH)
    e2e = (data or {}).get("e2e") or {}
    raw = e2e.get("paths")
    if isinstance(raw, str):
        return normalize_repo_relative_roots([raw])
    if isinstance(raw, list):
        return normalize_repo_relative_roots(raw)
    return normalize_repo_relative_roots([])


def _record_raw_event(stage, event, status="open", extra=None):
    raw_dir = Path(
        raw_path(
            date=datetime.now().strftime("%Y-%m-%d"),
            session_id=f"maestro-stage-{stage.lower()}-{datetime.now().strftime('%H%M%S')}",
        )
    ).parent
    raw_dir.mkdir(parents=True, exist_ok=True)
    fp = raw_path(
        date=datetime.now().strftime("%Y-%m-%d"),
        session_id=f"maestro-stage-{stage.lower()}-{datetime.now().strftime('%H%M%S')}",
    )
    fm = (
        "---\n"
        f"date: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"session: maestro-{event}-{stage}\n"
        "agents: [Maestro]\n"
        f"status: {status}\n"
        "supersedes: []\n"
        "---\n\n"
        f"## Topic\nMaestro {event} {stage}\n\n"
        f"## Decision\n{extra or ''}\n"
    )
    fp.write_text(fm, encoding="utf-8")


def cmd_status(args):
    """Show stage table + current progress."""
    cwd = Path.cwd()
    print("=== Maestro Status ===")
    info_path = cwd / ".louke/project/project.toml"
    if info_path.exists():
        print("\n--- project.toml ---")
        print(info_path.read_text(encoding="utf-8"))
    print("\n--- Stage Table ---")
    print(f"{'Code':<14} {'Stage':<14} {'Implementer':<14} {'Reviewer':<20}")
    for code, name, impl, rev in STAGES:
        print(f"{code:<14} {name:<14} {str(impl or '-'):<14} {str(rev or '-'):<20}")
    rc, branch, _ = git("branch", "--show-current", cwd=cwd)
    if rc == 0 and branch.strip():
        print(f"\nCurrent branch: {branch.strip()}")
    return 0


# ---- FR-0700 holdpoint dispatch ----


def _holdpoint(stage, args):
    """Return (ok, message)."""
    spec = args.spec_id or _read_current_spec()
    if stage == "M-FOUND":
        if not Path(".louke/project/project.toml").exists():
            return False, "project.toml missing; run lk agent scout foundation first"
        return True, "project.toml exists"
    if stage == "M-SPEC":
        if not spec:
            return False, "spec-id required (--spec-id)"
        rc = _run_lk("sage", "quote-check", "--spec", spec)
        if rc != 0:
            return False, f"sage quote-check failed (rc={rc})"
        # Lex verify (both signals required to advance)
        for lex_cmd in (
            ["lex", "verify-acceptance", "--spec", spec],
            ["lex", "verify-issue", "--spec", spec],
            ["lex", "verify-project", "--spec", spec],
        ):
            rc = _run_lk(*lex_cmd)
            if rc != 0:
                return False, f"lex {lex_cmd[1]} failed (rc={rc})"
        return True, "quote-check + lex verify exit 0"
    if stage == "M-TESTPLAN":
        # FR-0700: lk agent archer validate-test-plan
        if not spec:
            return False, "spec-id required (--spec-id)"
        rc = _run_lk("archer", "validate-test-plan", "--spec", spec)
        if rc != 0:
            return False, f"archer validate-test-plan failed (rc={rc})"
        ok, msg = _require_stage_artifact(
            spec, "M-TESTPLAN", "author-result", "Archer", "pass"
        )
        if not ok:
            return False, msg
        ok, msg = _require_stage_artifact(
            spec,
            "M-TESTPLAN",
            "review-result",
            "Sage",
            "pass",
            metadata={"source_command": "review"},
        )
        if not ok:
            return False, msg
        return True, f"test-plan validated ({spec})"
    if stage == "M-ARCH":
        # FR-0700: lk agent archer validate-arch
        if not spec:
            return False, "spec-id required (--spec-id)"
        rc = _run_lk("archer", "validate-arch", "--spec", spec)
        if rc != 0:
            return False, f"archer validate-arch failed (rc={rc})"
        ok, msg = _require_stage_artifact(
            spec, "M-ARCH", "author-result", "Archer", "pass"
        )
        if not ok:
            return False, msg
        ok, msg = _require_stage_artifact(
            spec,
            "M-ARCH",
            "review-result",
            "Prism",
            "pass",
            metadata={"source_command": "review"},
        )
        if not ok:
            return False, msg
        return True, f"architecture validated ({spec})"
    if stage == "M-LOCK":
        if not spec:
            return False, "spec-id required"
        if not args.confirm:
            return False, "User signal missing: pass --confirm (Maestro via IDE)"
        rc = _run_lk("sage", "record-lock", "--spec", spec, "--confirm")
        if rc != 0:
            return False, f"sage record-lock failed (rc={rc})"
        return True, "record-lock exit 0 (Sage+Lex+User signals)"
    if stage == "M-DEV":
        if not spec:
            return False, "spec-id required (--spec-id)"
        ok, msg = _require_stage_artifact(
            spec,
            "M-DEV",
            "review-result",
            "Prism",
            "pass",
            metadata={"commit_range": args.commit_range, "source_command": "review"},
        )
        if not ok:
            return False, msg
        keeper_args = ["keeper", "gate", "--commit-range", args.commit_range]
        if spec:
            keeper_args.extend(["--spec-id", spec, "--stage", "M-DEV"])
        rc = _run_lk(*keeper_args)
        if rc != 0:
            return False, f"keeper gate failed (rc={rc})"
        ok, msg = _require_stage_artifact(
            spec,
            "M-DEV",
            "gate-result",
            "Keeper",
            "pass",
            metadata={"commit_range": args.commit_range},
        )
        if not ok:
            return False, msg
        return True, "keeper gate exit 0"
    if stage == "M-E2E":
        if not spec:
            return False, "spec-id required (--spec-id)"
        ok, msg = _require_stage_artifact(
            spec,
            "M-E2E",
            "review-result",
            "Prism",
            "pass",
            metadata={"commit_range": args.commit_range, "source_command": "review"},
        )
        if not ok:
            return False, msg
        rc = _run_lk("shield", "run-e2e")
        if rc != 0:
            return False, f"shield run-e2e failed (rc={rc})"
        ok, msg = _require_stage_artifact(
            spec, "M-E2E", "author-result", "Shield", "pass"
        )
        if not ok:
            return False, msg
        keeper_args = ["keeper", "gate", "--commit-range", args.commit_range]
        tests_roots = _read_e2e_paths()
        if spec:
            keeper_args.extend(["--spec-id", spec, "--stage", "M-E2E"])
        for test_root in tests_roots:
            keeper_args.extend(["--tests-root", test_root])
        rc = _run_lk(*keeper_args)
        if rc != 0:
            return False, f"keeper gate failed (rc={rc})"
        ok, msg = _require_stage_artifact(
            spec,
            "M-E2E",
            "gate-result",
            "Keeper",
            "pass",
            metadata={
                "commit_range": args.commit_range,
                "tests_roots": tests_roots or ["tests/"],
            },
        )
        if not ok:
            return False, msg
        return True, "shield run-e2e + keeper gate exit 0"
    if stage == "M-BUGFIX":
        rc = _run_lk("keeper", "regression", "--baseline", "main", "--current", "HEAD")
        if rc != 0:
            return False, f"keeper regression failed (rc={rc})"
        return True, "keeper regression exit 0"
    if stage == "M-SECURITY":
        # FR-0720: skip if Security Audit disabled
        sec = _read_project_info("Security Audit").strip().lower()
        if sec == "disabled":
            return True, "Security Audit disabled in DoD; skip"
        rc = _run_lk("judge", "security-audit", "--release", args.release)
        if rc == 1:
            return False, "judge security-audit fail"
        if rc == 2:
            return False, "judge security-audit needs-human-review (treat as blocked)"
        return True, "judge security-audit pass"
    if stage == "M-MILESTONE":
        # FR-0730
        rc, out, _ = git("status", "--porcelain")
        if rc == 0 and out.strip():
            return False, "git working tree not clean; commit/stash before milestone"
        # check release merge (best-effort)
        rc, out, _ = git(
            "rev-parse", "--verify", f"refs/tags/{args.release.lstrip('releases/')}"
        )
        if rc != 0:
            return (
                False,
                f"git tag v{args.release} missing; run: git tag {args.release.lstrip('releases/')}",
            )
        return True, "working tree clean + tag present"
    return True, "no automated holdpoint"


def _read_current_spec():
    return _read_project_info("Spec ID")


def cmd_advance(args):
    """Advance to next stage (FR-0700 auto holdpoint + FR-0710 state update)."""
    print("=== Advance ===")
    print(f"From: {args.stage}")
    idx = next((i for i, t in enumerate(STAGES) if t[0] == args.stage), None)
    if idx is None:
        print(f"unknown stage: {args.stage}", file=sys.stderr)
        return 1

    if args.stage == "M-MILESTONE":
        print("M-MILESTONE is the final stage; advance marks milestone close.")
        _set_project_info_current_stage("M-MILESTONE")
        _record_raw_event(
            args.stage, "closed", status="resolved", extra="milestone closed"
        )
        print("-> milestone closed")
        return 0
    if idx + 1 >= len(STAGES):
        print(f"unknown tail stage {args.stage}", file=sys.stderr)
        return 1
    next_code = STAGES[idx + 1][0]
    print(f"To:   {next_code}")

    if args.force:
        spec = args.spec_id or _read_current_spec()
        if not spec:
            print("[--force] requires --spec-id and a waiver artifact", file=sys.stderr)
            return 1
        metadata = {}
        if args.stage in {"M-DEV", "M-E2E"} and args.commit_range:
            metadata["commit_range"] = args.commit_range
        ok, msg = _require_stage_artifact(
            spec, args.stage, "waiver", "human", "waived", metadata=metadata
        )
        print(f"[{'ok' if ok else 'high'}] {msg}")
        if not ok:
            print("\n-> REJECT (missing or stale waiver artifact)")
            print(
                f'  hint: run "lk agent maestro waive --stage {args.stage} --spec-id {spec} --approved-by <name> --reason <text>" first'
            )
            return 1
        print("[--force] waiver accepted; skipping automated checks")
        _set_project_info_current_stage(next_code)
        _record_raw_event(
            args.stage, "advance-force", extra=f"forced advance to {next_code}"
        )
        print(f"-> forced advance to {next_code}")
        return 0

    ok, msg = _holdpoint(args.stage, args)
    print(f"[{'ok' if ok else 'high'}] {msg}")
    if not ok:
        print(f"\n-> REJECT ({msg})")
        print(
            f'  hint: after manual review, run "lk agent maestro advance --stage {args.stage} --force" to force advance'
        )
        return 1
    _set_project_info_current_stage(next_code)
    _record_raw_event(args.stage, "advance", extra=f"advanced to {next_code}")
    print(f"-> advanced to {next_code}")
    return 0


def cmd_regress(args):
    """Regress current stage."""
    print("=== Regress ===")
    print(f"Stage: {args.stage}")
    print(f"Reason: {args.reason}")
    raw_dir = Path(
        raw_path(
            date=datetime.now().strftime("%Y-%m-%d"),
            session_id=f"maestro-regress-{args.stage.lower()}-{datetime.now().strftime('%H%M%S')}",
        )
    ).parent
    raw_dir.mkdir(parents=True, exist_ok=True)
    fp = raw_path(
        date=datetime.now().strftime("%Y-%m-%d"),
        session_id=f"maestro-regress-{args.stage.lower()}-{datetime.now().strftime('%H%M%S')}",
    )
    fm = (
        "---\n"
        f"date: {datetime.now().strftime('%Y-%m-%d')}\n"
        f"session: maestro-regress-{args.stage}\n"
        "agents: [Maestro]\n"
        "related_issues: []\n"
        "status: open\n"
        "supersedes: []\n"
        "---\n\n"
        "## Topic\n"
        f"Stage {args.stage} regressed\n\n"
        "## Decision\n"
        f"Reason for regression: {args.reason}\n\n"
        "## Open Questions\n"
        f"Implementer of stage {args.stage} must fix, then re-apply advance\n"
    )
    fp.write_text(fm, encoding="utf-8")
    print(f"✓ Recorded in {fp}")
    return 0


def cmd_escalate(args):
    """Escalate to user - generate alert for user."""
    print("=== Escalate to User ===")
    print(f"Reason: {args.reason}")
    print(f"Agent: {args.agent or '(not specified)'}")
    alert = (
        "@user **human intervention required**\n\n"
        f"Agent: {args.agent or '(unknown)'}\n"
        f"Reason: {args.reason}\n\n"
        "Please intervene.\n"
    )
    print(alert)
    print("-> send the above alert to the user in chat")
    return 0


def cmd_waive(args):
    """Write an explicit waiver artifact for a forced advance."""
    metadata = {"approved_by": args.approved_by}
    if args.commit_range:
        metadata["commit_range"] = args.commit_range
    path = write_stage_result(
        spec_id=args.spec_id,
        stage=args.stage,
        kind="waiver",
        role="human",
        verdict="waived",
        accepted_risks=args.accepted_risk or [args.reason],
        metadata=metadata,
        reviewed_targets=[],
        blocking_findings=[args.reason],
    )
    print(f"✓ waiver written: {path}")
    return 0
