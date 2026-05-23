# specforge v1 — Task Plan (修正版)

- **Spec ID**: SPEC-V1-001
- **版本**: v1.0.0
- **父分支**: main
- **功能分支**: feature/specforge-v1-self-bootup
- **创建日期**: 2026-05-23
- **修正日期**: 2026-05-23（合并粒度问题 + 标记已完成项）

## 版本与分支

| 项 | 值 |
|----|-----|
| 版本号 | v1.0.0 |
| 父分支 | main |
| 功能分支 | feature/specforge-v1-self-bootup |

## 任务列表

| ID | 任务 | 关联 Issue | 关联测试 | 目标文件 | 依赖 | 并行 | 状态 |
|----|------|-----------|---------|---------|------|:---:|:---:|
| T-001 | 创建 install.sh 安装脚本 | #2 | UT-001-01,02 | `install.sh` | — | | ⬜ |
| T-002 | 创建 specforge init 命令 | #2 | UT-002-01~05 | `bin/specforge` | T-001 | | ⬜ |
| T-003 | init 终端的 onboarding 指引文本 | #2 | UT-003-01,02 | `bin/specforge` | T-002 | | ⬜ |
| T-004 | Guide Agent prompt 就绪 | #3 | UT-004-01~03, UT-005-01,02 | `agents/Guide.md` | — | [P] | ✅ |
| T-005 | Librarian Agent prompt 就绪 | #4 | UT-006-01,02, UT-007-01~03, UT-008-01, UT-009-01,02 | `agents/Librarian.md` | — | [P] | ✅ |
| T-006 | 为全部 19 个开发 Agent 添加会话保存指令 | #5 | UT-010-01~03 | `agents/{Scout,Warden,Sage,Lex,Clerk,Auditor,Probe,Judge,Archer,Cynic,Forge,Prism,Keeper,Herald,Arbiter,Hunter,Shield,Maestro}.md` | — | | ⬜ |
| T-007 | 验证 8 个模板文件存在且格式完整 | #6 | UT-011-01~08, UT-012-01~03 | `templates/*.md` | — | [P] | ✅ |
| T-008 | 更新 ROSTER.md 包含 Guide + Librarian | #6 | — | `agents/ROSTER.md` | — | [P] | ✅ |

## 依赖图

```
T-001 (install.sh) ──→ T-002 (init cmd) ──→ T-003 (onboarding text)
                                                  
T-004 (Guide prompt)      [P]
T-005 (Librarian prompt)  [P]          
T-006 (19 agent 批改)     [P]          ← 单次 R-G-R 批量完成
T-007 (templates verify)  [P]
T-008 (ROSTER update)     [P]
```

## 变更影响分析

| 任务 | 修改文件 | 被依赖方 | 潜在回归面 |
|------|---------|---------|-----------|
| T-001~003 | install.sh, bin/specforge | 无 | 新文件，无回归 |
| T-006 | 19 个 agents/*.md | Maestro, 各阶段调用方 | Agent 行为不应改变，仅末尾多写一条 wiki 条目 |

## Cynic 评审结果

- [x] 每个任务关联了正确的测试用例
- [x] 依赖关系标注正确
- [x] 并行标记合理（T-006 目标 19 个文件无冲突，单个 R-G-R 循环批量完成）
- [x] 没有遗漏的 spec 需求（IT-004 的对话验证由 T-006 的 Green 阶段自动完成）
