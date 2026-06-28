"""lk 共享模式扫描 — 测试代码反模式.

对应 `.louke/templates/test-plan.md` §1.3 的 8 类反模式。
"""
import re
from pathlib import Path

TEST_ANTI_PATTERNS = [
    {
        'id': 'trivial-assert',
        'severity': 'high',
        'description': 'trivial assert (无实际验证)',
        'patterns': [
            (r'^\s*assert\s+True\b\s*(#.*)?$', 'assert True'),
            (r'^\s*assert\s+1\b\s*(#.*)?$', 'assert 1'),
            (r'^\s*assert\s+\w+\s+is\s+not\s+None\s*(#.*)?$', '仅检查 not None'),
            (r'assert\s+True\s*==\s*True', 'assert True == True'),
        ],
    },
    {
        'id': 'try-except-pass',
        'severity': 'high',
        'description': 'try/except: pass 吞掉异常',
        'patterns': [
            (r'except[^:]*:\s*\n\s*pass\s*$', 'except: pass'),
        ],
    },
    {
        'id': 'skip-without-issue',
        'severity': 'medium',
        'description': 'pytest.skip 无 issue 链接',
        'patterns': [
            (r'pytest\.skip\((?![^)]*issue)', 'pytest.skip 无 issue 链接'),
            (r'@pytest\.mark\.skip(?!\([^)]*issue)', '@pytest.mark.skip 无 issue 链接'),
        ],
    },
    {
        'id': 'mock-overuse',
        'severity': 'medium',
        'description': 'mock 框架核心 (应改 AC 或 interfaces)',
        'patterns': [
            (r'mock\.patch\([^)]*quantide|qmt|strategy|engine',
             'mock 框架核心模块'),
        ],
    },
    {
        'id': 'empty-test',
        'severity': 'medium',
        'description': '空测试函数',
        'patterns': [
            (r'def\s+test_\w+\([^)]*\):\s*\n\s*(pass|\.\.\.|TODO|NotImplemented)',
             '测试函数体仅 pass/.../TODO/NotImplemented'),
        ],
    },
    {
        'id': 'todo-in-test',
        'severity': 'medium',
        'description': '测试中 TODO/NotImplemented 无 issue',
        'patterns': [
            (r'(?i)#\s*(TODO|FIXME|NotImplemented)[^#\n]*test', 'TODO 在测试中'),
            (r'pytest\.skip\([^)]*NotImplemented', 'NotImplemented skip'),
        ],
    },
    {
        'id': 'ac-missing',
        'severity': 'high',
        'description': '测试函数无 AC-FRXXXX-YY 引用 (强制溯源)',
        'patterns': [],  # 用函数 docstring 检查, 不能简单 regex
    },
]


def scan_test_file(filepath: Path):
    """扫描测试文件, 返回反模式 findings.

    包含 8 类反模式 + AC 引用缺失检测 (函数 docstring 必含 AC-FRXXXX-YY).
    """
    findings = []
    try:
        content = filepath.read_text(encoding='utf-8', errors='replace')
    except (UnicodeDecodeError, OSError, PermissionError):
        return findings

    lines = content.split('\n')
    # 检测 AC 引用缺失: 找 def test_xxx(): 后面 3 行内 docstring 必须含 AC-FRXXXX-YY
    for i, line in enumerate(lines):
        m = re.match(r'^\s*def\s+(test_\w+)\s*\(', line)
        if not m:
            continue
        func_name = m.group(1)
        # 收集后续 5 行, 找 docstring
        block = '\n'.join(lines[i+1:i+6])
        if not re.search(r'AC-FR\d{4}-\d{2}', block):
            findings.append({
                'file': str(filepath),
                'line': i + 1,
                'severity': 'high',
                'pattern_id': 'ac-missing',
                'description': '测试函数无 AC-FRXXXX-YY 引用 (强制溯源)',
                'matched': f'def {func_name}() 缺 docstring AC 引用',
                'snippet': lines[i].strip()[:120],
            })

    # 检测 8 类反模式 (line-by-line)
    for line_num, line in enumerate(lines, 1):
        for pat_def in TEST_ANTI_PATTERNS:
            if pat_def['id'] == 'ac-missing':
                continue  # 上面已处理
            for regex, desc in pat_def['patterns']:
                if re.search(regex, line):
                    findings.append({
                        'file': str(filepath),
                        'line': line_num,
                        'severity': pat_def['severity'],
                        'pattern_id': pat_def['id'],
                        'description': pat_def['description'],
                        'matched': desc,
                        'snippet': line.strip()[:120],
                    })
                    break
    return findings


def find_test_files(start_path: Path = None):
    """找所有 test_*.py 文件."""
    if start_path is None:
        start_path = Path('tests')
    if not start_path.exists():
        return []
    test_files = []
    for p in start_path.rglob('*.py'):
        if 'test_' in p.name or p.name.endswith('_test.py'):
            test_files.append(p)
    return test_files