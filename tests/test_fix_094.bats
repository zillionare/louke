#!/usr/bin/env bats
# Tests for fix-094: lex verify-issue should support --branch

REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

@test "FIX-094-1: verify-issue_argparser_accepts_branch" {
    # The argparser should accept --branch without "unrecognized arguments" error.
    run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
from louke.lex import register
import argparse
p = argparse.ArgumentParser(prog='lk')
sub = p.add_subparsers(dest='agent', required=True)
register(sub)
ns = p.parse_args(['lex', 'verify-issue', '--spec', 'v0.1', '--branch', 'releases/v0.2'])
print('branch=', repr(ns.branch))
print('spec=', repr(ns.spec))
print('command=', repr(ns.command))
"
    [[ "$output" == *"branch= 'releases/v0.2'"* ]]
    [[ "$output" == *"spec= 'v0.1'"* ]]
    [[ "$output" == *"command= 'verify-issue'"* ]]
}

@test "FIX-094-2: verify-issue_branch_passed_to_subprocess" {
    # When --branch is given, cmd_verify_issue should include --branch in the
    # command it runs. Assert via monkey-patched subprocess.run.
    workdir="$BATS_TEST_TMPDIR/with_proj"
    mkdir -p "$workdir/.louke/project"
    echo '[project]' > "$workdir/.louke/project/project.toml"
    echo 'repo = "github.com/foo/bar"' >> "$workdir/.louke/project/project.toml"
    cd "$workdir"
    PYTHONPATH="$REPO_ROOT" run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
import louke.lex as lex
captured = {}
def fake_run(cmd, *a, **kw):
    captured['cmd'] = cmd
    class R: returncode = 0
    return R()
lex.subprocess.run = fake_run
ns = type('A', (), {'spec': 'v0.1', 'repo': '', 'branch': 'releases/v0.2'})()
lex.cmd_verify_issue(ns)
print('cmd=', captured['cmd'])
assert '--branch' in captured['cmd'], captured['cmd']
assert 'releases/v0.2' in captured['cmd'], captured['cmd']
print('OK')
"
    [[ "$output" == *"OK"* ]]
}

@test "FIX-094-3: verify-issue_branch_default_empty" {
    # No --branch and no project-info Release Branch: should not append --branch.
    # cd to a tmpdir with no .louke/project/ so _read_project_info returns ''.
    workdir="$BATS_TEST_TMPDIR/no_proj"
    mkdir -p "$workdir"
    cd "$workdir"
    PYTHONPATH="$REPO_ROOT" run python3 -c "
import sys
sys.path.insert(0, '$REPO_ROOT')
import louke.lex as lex
captured = {}
def fake_run(cmd, *a, **kw):
    captured['cmd'] = cmd
    class R: returncode = 0
    return R()
lex.subprocess.run = fake_run
ns = type('A', (), {'spec': 'v0.1', 'repo': '', 'branch': ''})()
lex.cmd_verify_issue(ns)
print('cmd=', captured['cmd'])
assert '--branch' not in captured['cmd'], captured['cmd']
print('OK')
"
    [[ "$output" == *"OK"* ]]
}
