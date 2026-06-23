# 006 — init 后目录收归到 .specforge/ 命名空间

- **状态**: 已采纳
- **日期**: 2026-06-23
- **影响**: init 目录布局、Agent prompt、bin/specforge、README、~25 个文件

## 背景

`specforge init`（含裸名新建与 adopt 模式）在项目根目录创建两类非源码目录：

- `wiki/{pages,decisions}/` + `wiki/{index,overview,log}.md` —— Agent 知识库（LLM-Wiki 三层架构）
- `raw/sources/` —— Agent 完整会话记录原始层

这两个目录在项目根目录存在三个具体问题：

1. **命名空间污染**：`raw/` 是泛用名，未来用户或第三方工具很可能也会用 `raw/`，冲突排查困难
2. **与"开发项目"语义不符**：LLM-Wiki 来自 Karpathy 的个人知识库场景，硬塞到 dev project 根目录显得别扭（"raw"这个词暗示"未加工的输入材料"，是资料库术语）
3. **持续累积的 git 风险**：`raw/sources/` 会话记录会无限增长，污染 history（即便 gitignore 也容易误 commit）

`wiki/` 同样有这些问题，但用户在前一轮 spec（v0.3-003）接受了"暂时把 `wiki/` 放根目录"的做法。本 spec 借机一次性把根目录整理干净。

## 决策

把 `init` 创建的全部 specforge 自有目录收归到 `.specforge/` 命名空间下：

| 旧路径 | 新路径 |
|---|---|
| `wiki/{pages,decisions}/` | `.specforge/wiki/{pages,decisions}/` |
| `wiki/{index,overview,log,consolidated}.md` | `.specforge/wiki/{index,overview,log,consolidated}.md` |
| `wiki/.cache` | `.specforge/wiki/.cache` |
| `raw/sources/` | `.specforge/raw/sources/` |

### 实施细节

- `init --adopt` 检测到旧路径后自动 `git mv`（跟踪时）或 `mv`（未跟踪时）到新位置
- 加 `--no-migrate` flag 跳过自动迁移（用户可手动控制）
- 旧路径与新路径并存时 **die**（防止数据丢失）
- tri-state 报告新增 `[→]` 档位表示迁移项
- specforge 自身升级时先吃狗粮（wiki/ 物理 git-mv 到 .specforge/wiki/）

## 备选

### 方案 A：只迁 `raw/`，保留 `wiki/`

只动 `raw/sources/`，`wiki/` 维持根目录。

**拒绝理由**：根目录仍被 specforge 占用；`wiki/` 与 `raw/` 关系密切（LLM-Wiki 三层），分开处理一致性差；"为求最小改动" 不值得留下技术债。

### 方案 B：彻底砍掉 `raw/` 与 LLM-Wiki 三层架构

承认 LLM-Wiki 是为个人知识库设计，specforge 的 dev workflow 实际上未实现 Hook 自动写会话（README §7 明说"未来 Hook 可用后"），整层砍掉最干净。

**拒绝理由**：LLM-Wiki 是 specforge 对外的差异化卖点（README §7 整章都在讲）；保留它对营销和长期愿景有利；当下没实现 Hook 不会阻碍将来加。把"承认现实"和"砍功能"分开：现实问题（路径污染）用方案 1 解，Hook 未实现是另一个独立问题。

### 方案 C：保留路径，强 gitignore

`raw/` 留在根目录，但在 `.gitignore` 写死。

**拒绝理由**：治标不治本。`raw/` 仍在根目录污染视觉，IDE 索引、find/grep、`tree` 命令都会扫到；gitignore 失误一次就破功。

## 后果

### 正面

- **项目根目录干净**：只含用户自己的代码、`.git/`、可能存在的 `.vscode/`、`.github/`
- **specforge 内部状态边界清晰**：`.specforge/` 整块可单独 gitignore（除 `.specforge/project/`），便于框架与项目分离
- **未来扩展性好**：若再增加 specforge 自有目录，约定是放进 `.specforge/`，不需要再讨论

### 负面

- **~25 个文件需要同步路径**：agent prompt（17 个）、README（§7 + §11.x ADR 表）、bin/specforge、测试文件
- **存量用户需升级**：v0.4 → v0.5 升级路径：`specforge init .`（自动迁移），或加 `--no-migrate` 后手动 `git mv`
- **wiki 文件内的 `[[wikilink]]` 不受路径影响**：因为 wikilink 是基于页面名（不带路径），不是文件路径
- **文档链接需手动修**：如 `README.md` 中 `wiki/decisions/001-x.md` 的链接需改为 `.specforge/wiki/decisions/001-x.md`

### 兼容性

- **FR 编号**：v0.3-003 FR-010 标 deprecated 但保留锚点（与 v0.4-004 废弃规则一致）
- **v0.5 FR 编号**：本 spec 的 FR-010~FR-090 是 v0.5-005 自身的
- **测试**：test_init.bats 4 个 pre-existing failure（UT-002-01/02/03/04）随本 spec 修复

## 关联

- 取代 v0.3-003 FR-010
- 实现：bin/specforge 新增 `migrate_legacy_paths` 函数 + `--no-migrate` flag
- 测试：tests/test_init_adopt_flow.bats 新增 MIG01-MIG08 共 8 个 case
- 文档：README §7 重写、§11.x ADR 表追加 006 行

## 决策日期

2026-06-23 by specforge self-bootstrap (v0.5 dogfooding)
