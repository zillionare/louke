"""lk 共享工具."""
import subprocess
from pathlib import Path


def package_root() -> Path:
    return Path(__file__).resolve().parent


def levenshtein(s1: str, s2: str) -> int:
    """Levenshtein edit distance: minimum number of single-character edits
    (insertions, deletions, substitutions) to transform s1 into s2.

    Iterative two-row DP, O(len(s1) * len(s2)) time, O(min(len(s1), len(s2))) space.
    """
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if not s2:
        return len(s1)
    prev = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1, 1):
        curr = [i]
        for j, c2 in enumerate(s2, 1):
            ins = prev[j] + 1
            dele = curr[j - 1] + 1
            sub = prev[j - 1] + (c1 != c2)
            curr.append(min(ins, dele, sub))
        prev = curr
    return prev[-1]


def similarity(s1: str, s2: str) -> float:
    """Normalized similarity in [0, 1] based on Levenshtein distance.

    similarity = 1 - distance / max(len(s1), len(s2))
    Identical strings → 1.0; one is empty → 0.0.
    """
    if not s1 and not s2:
        return 1.0
    if not s1 or not s2:
        return 0.0
    return 1.0 - levenshtein(s1, s2) / max(len(s1), len(s2))


def raw_path(date: str = None, session_id: str = '') -> Path:
    """FR-0810 unified raw session path: .louke/raw/{yy-mm-dd}/{session_id}.md."""
    from datetime import datetime
    if date is None:
        date = datetime.now().strftime('%y-%m-%d')
    slug = session_id or 'session'
    return Path('.louke/raw') / date / f'{slug}.md'


def git_root(cwd: Path = None):
    if cwd is None:
        cwd = Path.cwd()
    result = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'],
        cwd=cwd, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def ensure_gitignore_line(path: Path, line: str, dry_run: bool = False, report=None):
    existing = path.read_text(encoding='utf-8') if path.exists() else ''
    if line in {x.strip() for x in existing.splitlines()}:
        if report is not None:
            report.setdefault('skipped', []).append(str(path))
        return
    if report is not None:
        report.setdefault('added', []).append(f'{path}:{line}')
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = '' if not existing or existing.endswith('\n') else '\n'
    spacer = '' if not existing.strip() else prefix
    with path.open('a', encoding='utf-8') as f:
        f.write(f'{spacer}{line}\n')


def resolve_existing_path(value: str, cwd: Path = None) -> Path:
    if cwd is None:
        cwd = Path.cwd()
    path = Path(value).expanduser()
    if path.is_absolute() and path.exists():
        return path
    candidate = cwd / path
    if candidate.exists():
        return candidate
    root = git_root(cwd)
    if root is not None:
        root_candidate = root / path
        if root_candidate.exists():
            return root_candidate
    return candidate


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
    """返回 base..target 之间变更的文件列表. 支持 'A..B' range 或单 ref."""
    if cwd is None:
        cwd = Path.cwd()
    if '..' in target and '..' not in base:
        # target is 'A..B'; base is single ref (default 'HEAD~1'); swap
        left, right = target.split('..', 1)
        rc, out, _ = git('diff', '--name-only', base, right, cwd=cwd)
    elif '..' in target and '..' in base:
        left, right = target.split('..', 1)
        rc, out, _ = git('diff', '--name-only', left, right, cwd=cwd)
    else:
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