"""lk shared utilities."""

import subprocess
from pathlib import Path
from typing import Iterable, Optional


PROJECT_INFO_PATH = Path(".louke/project/project.toml")  # fix-002: from project-info.md
PROJECT_HISTORY_PATH = Path(".louke/project/history.md")
RUNTIME_FOUNDATION_PROGRAM = "Runtime foundation program"


def _toml_load(path: Path) -> dict:
    """tomllib / tomli fallback (Py3.9 compatible)."""
    try:
        import tomllib  # type: ignore
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def normalize_repo_relative_roots(
    raw_roots: Optional[Iterable[object]], default: Optional[list[str]] = None
) -> list[str]:
    """Normalize repo-relative path-like strings for metadata and CLI reuse.

    Behavior:
    - trim surrounding whitespace
    - normalize path separators via Path(...).as_posix()
    - drop empty entries
    - de-duplicate while preserving order
    - fall back to `default` when nothing remains
    """
    out: list[str] = []
    seen: set[str] = set()
    for raw in raw_roots or []:
        text = str(raw).strip()
        if not text:
            continue
        normalized = Path(text).as_posix()
        if normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out or list(default or [])


def package_root() -> Path:
    return Path(__file__).resolve().parent


def _read_project_info_field(label: str, path: Path = PROJECT_INFO_PATH) -> str:
    """Read a nested-key string value from project.toml. e.g. `Repo` → `[project].repo`.

    fix-002: switched from Markdown line-level regex to tomllib direct load.
    Supports legacy labels with spaces or hyphens like `Repo` / `Spec ID` / `Pre-commit` (backward compatible).
    Compatibility logic: normalize the label to snake_case, then try `[project].<snake>` / `[meta].<snake>` / top-level.
    """
    data = _toml_load(path)
    if not data:
        return ""

    # Normalize label: 'Spec ID' → 'spec_id', 'Pre-commit' → 'pre_commit', 'Repo' → 'repo'
    snake = label.lower().replace(" ", "_").replace("-", "_")

    # Prefer [project].<snake>
    proj = data.get("project", {})
    if snake in proj:
        return str(proj[snake])

    # Then [meta].<snake>
    meta = data.get("meta", {})
    if snake in meta:
        return str(meta[snake])

    # Compatibility: top-level key from older project.toml layouts.
    if snake in data:
        return str(data[snake])

    return ""


def _read_project_info_all(path: Path = PROJECT_INFO_PATH) -> dict:
    """Read all project.toml fields as a flat dict {label: value}. Backward compatible with legacy callers."""
    data = _toml_load(path)
    if not data:
        return {}
    flat: dict[str, str] = {}
    # Prefer [project] section
    for k, v in (data.get("project") or {}).items():
        flat[k] = str(v)
    # [meta] section (overrides duplicates)
    for k, v in (data.get("meta") or {}).items():
        flat[k] = str(v)
    return flat


def _archive_current_to_history(
    version_label: str = "",
    path: Path = PROJECT_INFO_PATH,
    history_path: Path = PROJECT_HISTORY_PATH,
) -> bool:
    """Called at M-MILESTONE wrap-up: append the current project.toml content to history.md (Markdown), then clear project.toml.

    Returns: True if migration performed, False if no content to migrate.
    """
    if not path.exists():
        return False
    try:
        current = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError):
        return False
    body = current.strip()
    if not body or len(body.splitlines()) < 3:
        return False
    # Convert TOML to a Markdown block and append to history.md
    history_path.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if history_path.exists():
        existing = history_path.read_text(encoding="utf-8", errors="replace")
    md_lines = []
    md_lines.append(f"\n\n## {version_label or '(no version label)'}\n")
    md_lines.append("```toml")
    md_lines.append(body)
    md_lines.append("```")
    history_path.write_text(existing + "\n".join(md_lines) + "\n", encoding="utf-8")
    # Clear project.toml until the Runtime foundation program initializes it.
    path.write_text(
        "# Active version: waiting for Runtime M-FOUND initialization\n",
        encoding="utf-8",
    )
    return True


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


def raw_path(date: str = None, session_id: str = "") -> Path:
    """FR-0810 unified raw session path: .louke/raw/{yy-mm-dd}/{session_id}.md."""
    from datetime import datetime

    if date is None:
        date = datetime.now().strftime("%y-%m-%d")
    slug = session_id or "session"
    return Path(".louke/raw") / date / f"{slug}.md"


def git_root(cwd: Path = None):
    if cwd is None:
        cwd = Path.cwd()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def ensure_gitignore_line(path: Path, line: str, dry_run: bool = False, report=None):
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if line in {x.strip() for x in existing.splitlines()}:
        if report is not None:
            report.setdefault("skipped", []).append(str(path))
        return
    if report is not None:
        report.setdefault("added", []).append(f"{path}:{line}")
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    spacer = "" if not existing.strip() else prefix
    with path.open("a", encoding="utf-8") as f:
        f.write(f"{spacer}{line}\n")


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
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def get_diff_files(base: str, target: str, cwd: Path = None):
    """Return the list of files changed between base..target. Supports 'A..B' range or single ref."""
    if cwd is None:
        cwd = Path.cwd()
    if ".." in target and ".." not in base:
        # target is 'A..B'; base is single ref (default 'HEAD~1'); swap
        left, right = target.split("..", 1)
        rc, out, _ = git("diff", "--name-only", base, right, cwd=cwd)
    elif ".." in target and ".." in base:
        left, right = target.split("..", 1)
        rc, out, _ = git("diff", "--name-only", left, right, cwd=cwd)
    else:
        rc, out, _ = git("diff", "--name-only", base, target, cwd=cwd)
    if rc != 0:
        return []
    return [f for f in out.strip().split("\n") if f]


def get_diff_content(base: str, target: str, cwd: Path = None):
    """Return the diff content between base..target."""
    rc, out, _ = git("diff", base, target, cwd=cwd)
    if rc != 0:
        return ""
    return out


def group_findings_by_severity(findings):
    """Group findings by severity (critical/high/medium/low)."""
    grouped = {"critical": [], "high": [], "medium": [], "low": []}
    for f in findings:
        grouped.setdefault(f["severity"], []).append(f)
    return grouped


def print_findings(findings, header="Findings"):
    """Print findings in human-readable format."""
    grouped = group_findings_by_severity(findings)
    print(f"=== {header} ({len(findings)} total) ===")
    for sev in ("critical", "high", "medium", "low"):
        items = grouped[sev]
        if not items:
            continue
        print(f"\n[{sev.upper()}] {len(items)} findings")
        for f in items:
            print(f"  {f['file']}:{f['line']} - {f['description']}")
            print(f"    pattern: {f['pattern_id']} ({f['matched']})")
            print(f"    snippet: {f['snippet']}")


def has_blocking_severity(findings):
    """Return True if findings contain critical or high severity."""
    for f in findings:
        if f["severity"] in ("critical", "high"):
            return True
    return False
