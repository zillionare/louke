# Session Save Protocol (louke raw session notes)

## 1. 用途

保存 agent 工作会话的原始记录，供 Librarian 后续蒸馏为 wiki 知识。

**raw 与 wiki 不可混用**：
- raw =  episodic 记忆，保留试错与未决
- wiki = 蒸馏后的知识
- raw **不进入 git**，仅本地维护

## 2. 何时使用

- 任何 agent 工作会话结束时
- 会话产生了非平凡决策
- 会话尝试过被推翻的方案
- 会话留下开放问题给下一轮

## 3. 文件路径

```
.louke/raw/{yy-mm-dd}/{session-id}.md
```

- `yy-mm-dd` = 会话日期
- `session-id` = `{agent}-{spec-id 或 phase}-{议题}`
  - 例：`devon-v0.1-001-task-impl`

## 4. 格式

必带 frontmatter：

```markdown
---
date: 2026-06-27
session: devon-v0.1-001-task-impl
agents: [Devon, Prism]
spec: v0.1-001-init-adopt-mode
related_issues: [#142, #143]
status: resolved | superseded | open     # 必填
supersedes: []
---

## 议题 {在协调/决定什么}
## 决定 {结论，命令/文件/规范形式}
## 试过但放弃 {被推翻方案及理由——wiki 蒸馏关键输入}
## 开放问题 {留给下轮}
```

## 5. 约束

- `status` 必填（未填视为 `open`，Librarian 拒绝蒸馏）
- `supersedes` 引用时，被引用条目应在 frontmatter 加 `superseded-by` 双向追溯
- 返回结果前写入，但不阻塞流程
