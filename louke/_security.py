"""lk shared-mode scanner — security pattern library.

Shared by `lk agent judge` and `lk agent prism`. Patterns based on `.louke/templates/security-checklist.md`.
"""

import re
from pathlib import Path

SECURITY_PATTERNS = [
    {
        "id": "eval-exec",
        "severity": "critical",
        "description": "using eval/exec to dynamically execute code",
        "patterns": [
            (r"\beval\s*\(", "eval() call"),
            (r"\bexec\s*\(", "exec() call"),
            (r"\bcompile\s*\(", "compile() call (potential exec)"),
        ],
        "file_exts": [".py"],
    },
    {
        "id": "hardcoded-secret",
        "severity": "high",
        "description": "hardcoded secret/password/token",
        "patterns": [
            (
                r'(?i)(password|passwd|secret|api_?key|token|access_?key|auth_?token)\s*=\s*["\'][^"\']{4,}["\']',
                "string literal assignment to sensitive field",
            ),
        ],
        "file_exts": [
            ".py",
            ".js",
            ".ts",
            ".go",
            ".rs",
            ".java",
            ".rb",
            ".yml",
            ".yaml",
            ".env",
            ".json",
        ],
    },
    {
        "id": "sql-string-concat",
        "severity": "high",
        "description": "SQL string concatenation (potential injection)",
        "patterns": [
            (r'(execute|cursor\.execute)\s*\(\s*f["\']', "f-string concatenating SQL"),
            (
                r"(execute|cursor\.execute)\s*\([^)]*\+\s*\w+",
                "+ concatenating variable into SQL",
            ),
            (
                r'(SELECT|INSERT|UPDATE|DELETE)[^;]*["\'][^"\']*["\'][^;]*\+\s*\w+',
                "SELECT/INSERT/UPDATE/DELETE string concatenation",
            ),
        ],
        "file_exts": [".py"],
    },
    {
        "id": "shell-injection",
        "severity": "high",
        "description": "subprocess shell=True + string concatenation",
        "patterns": [
            (r"subprocess\.[A-Za-z_]+\s*\([^)]*shell\s*=\s*True", "shell=True usage"),
        ],
        "file_exts": [".py"],
    },
    {
        "id": "pickle-load",
        "severity": "high",
        "description": "pickle deserializing untrusted data",
        "patterns": [
            (r"pickle\.loads?\s*\(", "pickle.load(s) usage"),
        ],
        "file_exts": [".py"],
    },
    {
        "id": "yaml-unsafe-load",
        "severity": "medium",
        "description": "yaml.load (no Loader)",
        "patterns": [
            (
                r"yaml\.load\s*\(\s*[^,]+\s*\)(?!\s*,)",
                "yaml.load without Loader (PyYAML < 5.1 compatibility issue)",
            ),
        ],
        "file_exts": [".py"],
    },
    {
        "id": "todo-security",
        "severity": "medium",
        "description": "TODO/FIXME involving security",
        "patterns": [
            (
                r"(?i)#\s*(TODO|FIXME|XXX).*(security|auth|password|token|secret|crypt|sanitize)",
                "TODO/FIXME security related",
            ),
        ],
        "file_exts": None,
    },
    {
        "id": "logging-sensitive",
        "severity": "medium",
        "description": "logging sensitive fields",
        "patterns": [
            (
                r"(?i)log(?:ger)?\.\w+\([^)]*(password|passwd|secret|token|api_?key)",
                "log call contains sensitive field",
            ),
        ],
        "file_exts": [".py"],
    },
]

# File extensions that should be scanned (None means scan all text files)
SCANNABLE_EXTS = {
    ".py",
    ".js",
    ".ts",
    ".go",
    ".rs",
    ".java",
    ".rb",
    ".yml",
    ".yaml",
    ".env",
    ".json",
    ".sh",
    ".toml",
}

# The scanner itself: its regex definitions match itself, so skip to avoid false positives
SELF_SCAN_EXCLUDE = {"louke/_security.py", "louke/_tests.py"}


def scan_file(filepath: Path):
    """Scan a single file for security patterns, returns findings list."""
    fp_str = str(filepath)
    if any(s in fp_str for s in SELF_SCAN_EXCLUDE):
        return []

    findings = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except (UnicodeDecodeError, OSError, PermissionError):
        return findings

    for line_num, line in enumerate(content.split("\n"), 1):
        for pat_def in SECURITY_PATTERNS:
            file_exts = pat_def.get("file_exts")
            if file_exts is not None and filepath.suffix not in file_exts:
                continue
            for regex, desc in pat_def["patterns"]:
                if re.search(regex, line):
                    findings.append(
                        {
                            "file": str(filepath),
                            "line": line_num,
                            "severity": pat_def["severity"],
                            "pattern_id": pat_def["id"],
                            "description": pat_def["description"],
                            "matched": desc,
                            "snippet": line.strip()[:120],
                        }
                    )
                    break  # after a pattern matches, do not match the same line again
    return findings
