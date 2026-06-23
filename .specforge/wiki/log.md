# Wiki Operations Log

## 2026-06-23 — 目录收归到 .specforge/ 命名空间
- 操作: NAMESPACE_MIGRATE
- 描述: 把根目录的 `wiki/` 和 `raw/` 自动 git-mv 到 `.specforge/wiki/` 与 `.specforge/raw/`（v0.5-005 决策，见 decisions/006）
- 处理文件: 所有 wiki/* (含 5 份 ADR + 7 份 page + index/overview/log/consolidated)
- 产出: `.specforge/wiki/`
- 触发: specforge 自身升级到 v0.5（自举）

## 2026-05-31 — Wiki 架构迁移
- 操作: ARCHITECTURE_MIGRATE
- 描述: 从 wiki/entries/ 迁移到 wiki/pages/ + frontmatter + [[wikilink]] 三层架构
- 处理文件: 6 (first-conversation, sage-interview, scout-v0.1, archer-cynic, clerk-auditor, herald-arbiter)
- 产出: .specforge/wiki/index.md, .specforge/wiki/overview.md, .specforge/wiki/log.md
- 触发: 手动 (架构升级)

## 2026-05-23 — V1 自举完成
- 操作: BOOTSTRAP_COMPLETE
- 描述: specforge v0.1 完成 7 阶段自举流程
- 处理文件: 6 (全部 v0.1 会话记录)
- 产出: wiki/entries/ 下 6 个条目 + wiki/consolidated.md
- 触发: 手动
