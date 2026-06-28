"""hp 共享模式扫描 — 安全 pattern 库.

被 hp judge, hp prism 共享。模式基于 `.holdpoint/templates/security-checklist.md`。
"""
import re
from pathlib import Path

SECURITY_PATTERNS = [
    {
        'id': 'eval-exec',
        'severity': 'critical',
        'description': '使用 eval/exec 动态执行代码',
        'patterns': [
            (r'\beval\s*\(', 'eval() 调用'),
            (r'\bexec\s*\(', 'exec() 调用'),
            (r'\bcompile\s*\(', 'compile() 调用 (潜在 exec)'),
        ],
        'file_exts': ['.py'],
    },
    {
        'id': 'hardcoded-secret',
        'severity': 'high',
        'description': '硬编码密钥/密码/token',
        'patterns': [
            (r'(?i)(password|passwd|secret|api_?key|token|access_?key|auth_?token)\s*=\s*["\'][^"\']{4,}["\']',
             '字符串字面量赋值敏感字段'),
        ],
        'file_exts': ['.py', '.js', '.ts', '.go', '.rs', '.java', '.rb', '.yml', '.yaml', '.env', '.json'],
    },
    {
        'id': 'sql-string-concat',
        'severity': 'high',
        'description': 'SQL 字符串拼接 (潜在注入)',
        'patterns': [
            (r'(execute|cursor\.execute)\s*\(\s*f["\']', 'f-string 拼接 SQL'),
            (r'(execute|cursor\.execute)\s*\([^)]*\+\s*\w+', '+ 拼接变量到 SQL'),
            (r'(SELECT|INSERT|UPDATE|DELETE)[^;]*["\'][^"\']*["\'][^;]*\+\s*\w+',
             'SELECT/INSERT/UPDATE/DELETE 字符串拼接'),
        ],
        'file_exts': ['.py'],
    },
    {
        'id': 'shell-injection',
        'severity': 'high',
        'description': 'subprocess shell=True + 字符串拼接',
        'patterns': [
            (r'subprocess\.[A-Za-z_]+\s*\([^)]*shell\s*=\s*True', 'shell=True 使用'),
        ],
        'file_exts': ['.py'],
    },
    {
        'id': 'pickle-load',
        'severity': 'high',
        'description': 'pickle 反序列化不可信数据',
        'patterns': [
            (r'pickle\.loads?\s*\(', 'pickle.load(s) 使用'),
        ],
        'file_exts': ['.py'],
    },
    {
        'id': 'yaml-unsafe-load',
        'severity': 'medium',
        'description': 'yaml.load (无 Loader)',
        'patterns': [
            (r'yaml\.load\s*\(\s*[^,]+\s*\)(?!\s*,)', 'yaml.load 无 Loader (PyYAML < 5.1 兼容问题)'),
        ],
        'file_exts': ['.py'],
    },
    {
        'id': 'todo-security',
        'severity': 'medium',
        'description': 'TODO/FIXME 涉及安全',
        'patterns': [
            (r'(?i)#\s*(TODO|FIXME|XXX).*(security|auth|password|token|secret|crypt|sanitize)',
             'TODO/FIXME 安全相关'),
        ],
        'file_exts': None,
    },
    {
        'id': 'logging-sensitive',
        'severity': 'medium',
        'description': '日志中记录敏感字段',
        'patterns': [
            (r'(?i)log(?:ger)?\.\w+\([^)]*(password|passwd|secret|token|api_?key)',
             '日志调用含敏感字段'),
        ],
        'file_exts': ['.py'],
    },
]

# 应扫描的文件扩展名（None 表示扫描所有文本文件）
SCANNABLE_EXTS = {'.py', '.js', '.ts', '.go', '.rs', '.java', '.rb',
                  '.yml', '.yaml', '.env', '.json', '.sh', '.toml'}

# Scanner 自身: regex 定义匹配自身, 跳过避免 false positive
SELF_SCAN_EXCLUDE = {'holdpoint/_security.py', 'holdpoint/_tests.py'}


def scan_file(filepath: Path):
    """扫描单个文件的 security patterns, 返回 findings list."""
    fp_str = str(filepath)
    if any(s in fp_str for s in SELF_SCAN_EXCLUDE):
        return []

    findings = []
    try:
        content = filepath.read_text(encoding='utf-8', errors='replace')
    except (UnicodeDecodeError, OSError, PermissionError):
        return findings

    for line_num, line in enumerate(content.split('\n'), 1):
        for pat_def in SECURITY_PATTERNS:
            file_exts = pat_def.get('file_exts')
            if file_exts is not None and filepath.suffix not in file_exts:
                continue
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
                    break  # 一个模式匹配后, 不重复匹配该行
    return findings