#!/usr/bin/env python3
"""
给 agents/*.md 加 YAML frontmatter, 使 VS Code 能识别为 custom agent.
幂等: 已有 frontmatter 的文件跳过.
"""
import re
from pathlib import Path

AGENTS_DIR = Path(__file__).parent.parent / "agents"
DESCRIPTIONS = {
    "Arbiter": "评审人 — 促成共识、裁决分歧",
    "Archer": "测试计划 — 把 spec 需求解构成可执行的测试用例",
    "Cynic": "测试实施 — 编写并运行测试用例",
    "Forge": "编码实施 — 按 spec 实现功能",
    "Guide": "向导 — 帮助新用户理解 specforge 方法论",
    "Herald": "测试报告 — 汇总多轮测试结果形成报告",
    "Hunter": "代码搜索 — 从代码库中定位与需求相关的代码段",
    "Judge": "测试审计 — 跟踪回归测试结果并改善测试质量",
    "Keeper": "版本控制 — 管理 spec 版本锁定与交付质量",
    "Lex": "spec 审查与 issue 组织者",
    "Librarian": "知识库 — 管理 wiki、决策记录和项目记忆",
    "Maestro": "Pipeline 编排者 — 管理开发工作流",
    "Prism": "多视角 — 同时考虑用户、安全、性能、可维护性等维度",
    "Probe": "测试计划 — 从 spec 需求生成可执行的测试计划",
    "Sage": "需求澄清与 spec 撰写 — 把 story 翻译为可追踪的 spec",
    "Scout": "项目奠基 — 执行 §2.1 初始化流程",
    "Shield": "安全检查 — 审查敏感信息泄露风险",
    "Warden": "审核人 — 检查 foundation 是否达标并同意推进",
}
ROSTER = "ROSTER.md"

for md_file in sorted(AGENTS_DIR.glob("*.md")):
    name = md_file.stem  # e.g. "Sage", "ROSTER"
    text = md_file.read_text(encoding="utf-8")

    # Skip if already has frontmatter
    if text.startswith("---\n"):
        print(f"  ⏭️  {md_file.name} (已有 frontmatter)")
        continue

    if name == "ROSTER":
        desc = "Agent 花名册与阶段映射"
    else:
        desc = DESCRIPTIONS.get(name, name)

    frontmatter = f"---\nname: {name.lower()}\ndescription: {desc}\n---\n\n"
    md_file.write_text(frontmatter + text, encoding="utf-8")
    print(f"  ✅ {md_file.name} ({desc})")

print(f"\n完成: {len(list(AGENTS_DIR.glob('*.md')))} 个文件处理")
