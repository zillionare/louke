"""hp 共享工具."""
import subprocess
from pathlib import Path


def git(*args, cwd: Path = None):
    """Run git command, return (returncode, stdout, stderr)."""
    if cwd is None:
        cwd = Path.cwd()
    result = subprocess.run(
        ['git', *args],
        cwd=cwd, capture_output=True, text=True,
    )
    return result.returncode, result.stdout, result.stderr


def get_diff_files(base: str, target: str, cwd: Path = None):
    """返回 base..target 之间变更的文件列表."""
    rc, out, _ = git('diff', '--name-only', base, target, cwd=cwd)
    if rc != 0:
        return []
    return [f for f in out.strip().split('\n') if f]


def get_diff_content(base: str, target: str, cwd: Path = None):
    """返回 base..target 之间变更的 diff 内容."""
    rc, out, _ = git('diff', base, target, cwd=cwd)
    if rc != 0:
        return ''
    return out


def group_findings_by_severity(findings):
    """Group findings by severity (critical/high/medium/low)."""
    grouped = {'critical': [], 'high': [], 'medium': [], 'low': []}
    for f in findings:
        grouped.setdefault(f['severity'], []).append(f)
    return grouped


def print_findings(findings, header='Findings'):
    """Print findings in human-readable format."""
    grouped = group_findings_by_severity(findings)
    print(f'=== {header} ({len(findings)} total) ===')
    for sev in ('critical', 'high', 'medium', 'low'):
        items = grouped[sev]
        if not items:
            continue
        print(f'\n[{sev.upper()}] {len(items)} findings')
        for f in items:
            print(f"  {f['file']}:{f['line']} - {f['description']}")
            print(f"    pattern: {f['pattern_id']} ({f['matched']})")
            print(f"    snippet: {f['snippet']}")


def has_blocking_severity(findings):
    """Return True if findings contain critical or high severity."""
    for f in findings:
        if f['severity'] in ('critical', 'high'):
            return True
    return False