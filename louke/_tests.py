"""lk shared-mode scanner — test code anti-patterns.

Corresponds to the 8 anti-patterns in `.louke/templates/test-plan.md` §1.3.
"""

import re
from pathlib import Path

TEST_ANTI_PATTERNS = [
    {
        "id": "trivial-assert",
        "severity": "high",
        "description": "trivial assert (no real validation)",
        "patterns": [
            (r"^\s*assert\s+True\b\s*(#.*)?$", "assert True"),
            (r"^\s*assert\s+1\b\s*(#.*)?$", "assert 1"),
            (r"^\s*assert\s+\w+\s+is\s+not\s+None\s*(#.*)?$", "only checks not None"),
            (r"assert\s+True\s*==\s*True", "assert True == True"),
        ],
    },
    {
        "id": "try-except-pass",
        "severity": "high",
        "description": "try/except: pass swallows exception",
        "patterns": [
            (r"except[^:]*:\s*\n\s*pass\s*$", "except: pass"),
        ],
    },
    {
        "id": "skip-without-issue",
        "severity": "medium",
        "description": "pytest.skip without issue link",
        "patterns": [
            (r"pytest\.skip\((?![^)]*issue)", "pytest.skip without issue link"),
            (
                r"@pytest\.mark\.skip(?!\([^)]*issue)",
                "@pytest.mark.skip without issue link",
            ),
        ],
    },
    {
        "id": "mock-overuse",
        "severity": "medium",
        "description": "mocking framework core (should refactor AC or interfaces)",
        "patterns": [
            (
                r"mock\.patch\([^)]*quantide|qmt|strategy|engine",
                "mocking framework core modules",
            ),
        ],
    },
    {
        "id": "empty-test",
        "severity": "medium",
        "description": "empty test function",
        "patterns": [
            (
                r"def\s+test_\w+\([^)]*\):\s*\n\s*(pass|\.\.\.|TODO|NotImplemented)",
                "test function body is only pass/.../TODO/NotImplemented",
            ),
        ],
    },
    {
        "id": "todo-in-test",
        "severity": "medium",
        "description": "TODO/NotImplemented in test without issue",
        "patterns": [
            (r"(?i)#\s*(TODO|FIXME|NotImplemented)[^#\n]*test", "TODO in test"),
            (r"pytest\.skip\([^)]*NotImplemented", "NotImplemented skip"),
        ],
    },
    {
        "id": "ac-missing",
        "severity": "high",
        "description": "test function has no AC-FRXXXX-YY reference (mandatory tracing)",
        "patterns": [],  # checked via function docstring, cannot use simple regex
    },
]


def scan_test_file(filepath: Path):
    """Scan a test file, return anti-pattern findings.

    Includes 8 anti-patterns + AC reference missing detection (function docstring must contain AC-FRXXXX-YY).
    """
    findings = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except (UnicodeDecodeError, OSError, PermissionError):
        return findings

    lines = content.split("\n")
    # Detect missing AC reference: find def test_xxx(): then within the next 3 lines the docstring must contain AC-FRXXXX-YY
    for i, line in enumerate(lines):
        m = re.match(r"^\s*def\s+(test_\w+)\s*\(", line)
        if not m:
            continue
        func_name = m.group(1)
        # Collect the next 5 lines and look for the docstring
        block = "\n".join(lines[i + 1 : i + 6])
        if not re.search(r"AC-FR\d{4}-\d{2}", block):
            findings.append(
                {
                    "file": str(filepath),
                    "line": i + 1,
                    "severity": "high",
                    "pattern_id": "ac-missing",
                    "description": "test function has no AC-FRXXXX-YY reference (mandatory tracing)",
                    "matched": f"def {func_name}() missing docstring AC reference",
                    "snippet": lines[i].strip()[:120],
                }
            )

    # Detect 8 anti-patterns (line-by-line)
    for line_num, line in enumerate(lines, 1):
        for pat_def in TEST_ANTI_PATTERNS:
            if pat_def["id"] == "ac-missing":
                continue  # already handled above
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
                    break
    return findings


def find_test_files(start_path: Path = None):
    """Find all test_*.py files."""
    if start_path is None:
        start_path = Path("tests")
    if not start_path.exists():
        return []
    test_files = []
    for p in start_path.rglob("*.py"):
        if "test_" in p.name or p.name.endswith("_test.py"):
            test_files.append(p)
    return test_files
