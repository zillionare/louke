#!/usr/bin/env python3
"""
给 agents/*.md 加 YAML frontmatter, 使 VS Code 能识别为 custom agent.
幂等: 已有 frontmatter 的文件跳过.
"""
import re
from pathlib import Path

AGENTS_DIR = Path(__file__).parent.parent / "agents"
DESCRIPTIONS = {
    "Scout": "项目奠基 — 执行 §2.1 初始化流程",
    "Sage": "需求澄清与 spec 撰写 — 把 story 翻译为可追踪的 spec",
    "Lex": "spec 审查与 issue 组织者",
    "Archer": "测试计划 + 架构 — 设计 test-plan / architecture / interfaces",
    "Maestro": "Pipeline 编排者 — 管理开发工作流",
    "Devon": "编码实施 — 按 spec 实现功能（R-G-R）",
    "Prism": "多视角 — 同时考虑用户、安全、性能、可维护性等维度",
    "Keeper": "质量门禁 — commit 格式 + 测试 + lint gate",
    "Shield": "e2e 测试编写 — 按 test-plan 写 e2e（B 级）",
    "Judge": "S 级安全审计 — 深度审查敏感信息泄露风险",
    "Warden": "审核人 — 检查 foundation 是否达标并同意推进",
    "Librarian": "知识库 — 管理 wiki、决策记录和项目记忆",
    "REVIEW-PAIRINGS": "Agent 评审配对 — 实施者↔评审者映射与变更历史",
}

for md_file in sorted(AGENTS_DIR.glob("*.md")):
    name = md_file.stem  # e.g. "Sage", "REVIEW-PAIRINGS"
    text = md_file.read_text(encoding="utf-8")

    # Skip if already has frontmatter
    if text.startswith("---\n"):
        print(f"  ⏭️  {md_file.name} (已有 frontmatter)")
        continue

    desc = DESCRIPTIONS.get(name, name)

    frontmatter = f"---\nname: {name.lower()}\ndescription: {desc}\n---\n\n"
    md_file.write_text(frontmatter + text, encoding="utf-8")
    print(f"  ✅ {md_file.name} ({desc})")

print(f"\n完成: {len(list(AGENTS_DIR.glob('*.md')))} 个文件处理")
