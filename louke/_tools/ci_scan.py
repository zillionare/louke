#!/usr/bin/env python3
"""Run specforge CI static scanners."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> tuple[int, str]:
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p.returncode, p.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--acceptance")
    ap.add_argument("--spec")
    ap.add_argument("--tests", default="tests")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    if args.acceptance:
        acceptance = Path(args.acceptance)
    elif args.spec:
        acceptance = Path(".louke/project/specs") / args.spec / "acceptance.md"
    else:
        print("--acceptance or --spec is required", file=sys.stderr)
        return 2
    root = Path(__file__).resolve().parent
    legacy_baseline = Path.cwd() / ".louke" / "project" / "baselines" / "keeper-anti-pattern.txt"
    # Exclude tests/fixtures/ from scan: these are check_assertions' own test fixtures
    # containing intentional anti-pattern code (assert True, try/except/pass, etc.).
    exclude = ["tests/fixtures"]
    ac_cmd = [
        sys.executable,
        str(root / "check_acs.py"),
        "--acceptance",
        str(acceptance),
        "--tests",
        args.tests,
        "--exclude",
        *exclude,
    ]
    assert_cmd = [
        sys.executable,
        str(root / "check_assertions.py"),
        "--tests",
        args.tests,
        "--exclude",
        *exclude,
    ]
    if legacy_baseline.exists():
        assert_cmd.extend(["--legacy-baseline", str(legacy_baseline)])
    if args.json:
        ac_cmd.append("--json")
        assert_cmd.append("--json")
    ac_status, ac_out = run(ac_cmd)
    assert_status, assert_out = run(assert_cmd)
    ok = ac_status == 0 and assert_status == 0
    if args.json:

        def parse(text: str):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw": text}

        print(
            json.dumps(
                {"ok": ok, "acs": parse(ac_out), "assertions": parse(assert_out)},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("== check_acs ==")
        print(ac_out.rstrip())
        print("== check_assertions ==")
        print(assert_out.rstrip())
        print("[pass]" if ok else "[fail]")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
