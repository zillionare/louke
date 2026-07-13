# Lex Stage 1 Attempt（2026-07-13）

> 运行审计记录，不是 Lex verdict。

## 尝试 1：直接指定 Lex

- 入口：`opencode run --agent lex ...`
- OpenCode 明确报告 `lex` 为 `mode: subagent`，不能作为 primary，随后回退到默认 Maestro。
- 回退会话只读取三份文档并运行 `verify-acceptance`；没有语义 verdict、没有 inline-discussion。
- 结论：不能把结果记作 Lex review。

## 尝试 2：由 Maestro 使用 task 调度 Lex

- 入口：primary Maestro，被明确限制为只调度 Lex Stage 1。
- Maestro 显示 Lex task started/completed，但 subagent 返回空 body。
- `spec.md` 没有新增 discussion，调用者没有收到 pass/reject、blocker 或 thread id。
- 结论：空 Agent 结果缺少语义证据，必须视为失败/needs-attention，而不是 pass。

## 目前可证明的结果

离线 `lk agent lex verify-acceptance` 通过：29 条 FR/NFR 同名覆盖、127 条 AC 连续且非空、反向覆盖闭合。`quote-check` 因全部 `Decided=⚠️` 返回非零，符合尚未人工批准的阶段状态。

以上计数是首次尝试时的历史快照；后续合同补全后的当前计数见下方尝试 3。

## 尝试 3：人类批准后的最终 OpenCode 调度

- 入口：OpenCode Maestro session `ses_0a5b0c01effei9VRJG71wiZVJ4`，任务被严格限制为只调度 Lex Stage 1。
- Maestro 创建 Lex subtask 后仍得到空 body；继续同一 session 再次要求有效 verdict，结果仍为空。
- Maestro 最终明确返回 `[LEX STAGE1 FAILED]`，没有把 task completed 或自身结构检查冒充 Lex PASS。
- 其 CLI fallback 因 `project.toml` 仍指向 v0.11/release branch，尝试从 GitHub `releases/v0.10` 读取尚未提交的 v0.12 文件而失败；根 agent 另用显式本地 `--spec-file/--acceptance-file` 路径完成结构校验。

## 独立 Lex-rubric fallback review

- 为保留独立语义判断且不绕过门禁，使用隔离 reviewer `/root/lex_stage1_review`，严格按仓库 `louke/agents/Lex.md` Stage 1 rubric 只读评审三份合同。
- 第一轮 verdict：`[LEX STAGE1 REJECT]`。三个 blocker 是：hotfix requirements approval 场景矛盾；FR-1601 的条件式 AC 无法证明程序职责零遗漏；FR-0001/FR-0601/NFR-0301 若干规范性子条款缺少直接 AC。
- 三项原始意见已作为 Lex inline threads 写入 `spec.md`，Codex 的对应修订回复紧随其后。修订新增 built-in responsibility inventory 与 AC-FR1601-06、AC-NFR0301-06，并扩充 AC-FR0001-01、AC-FR0601-01。
- 修订后本地结构验证为 30/30 FR/NFR、144/144 AC，L1—L5 全部通过。
- 同一隔离 reviewer 随后重新读取完整三份合同，而非只看 diff，给出 `[LEX STAGE1 PASS]`：三个 blocker 全部闭合且没有新 blocker；对应 Lex root threads 已由 initiator 标记 `[RESOLVED]`。
- 当前剩余门禁不是 Lex 问题，而是 FR-1601 新增了实质产品合同，必须由 Aaron 重新批准当前版本。

## 对 v0.12 的反馈

该失败直接支持 FR-1401、FR-1501、FR-1601 与 FR-2001：Runtime 必须保存 task/session identity、要求 schema-valid Agent result、对空结果显示稳定失败并提供恢复，而不能因为调度工具返回 completed 就推进 workflow。
