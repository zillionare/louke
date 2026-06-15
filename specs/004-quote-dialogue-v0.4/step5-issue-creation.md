# Step 5: Issue 创建日志 (spec 004)

**创建时间**: 2026-06-15
**操作者**: Sage (via gh 身份 quantclaws)
**Project**: specforge-v0.4 (#7, ID PVT_kwHOED0Dk84BasDf, owner quantclaws)

## 创建的 8 个 issue (FR/NFR 9 个 → 跳过废弃 NFR-010)

| FR/NFR | Issue # | 标题 | Project |
|--------|---------|------|---------|
| FR-010 | #53 | quote-block 语法识别 | specforge-v0.4 |
| FR-020 | #56 | speaker 身份由加粗 name 决定 | specforge-v0.4 |
| FR-030 | #57 | 状态标记 | specforge-v0.4 |
| FR-040 | #58 | unit 划分与 yaml 元数据 | specforge-v0.4 |
| FR-050 | #59 | unit-ready 判定 | specforge-v0.4 |
| FR-060 | #60 | 用户侧编辑器不需扩展 | specforge-v0.4 |
| FR-070 | #61 | agent 侧无 PR 依赖 | specforge-v0.4 |
| NFR-020 | #62 | 错误信息包含 quote 块行号 | specforge-v0.4 |
| ~~NFR-010~~ | skip | ~~废弃~~ (Aaron 决定) | n/a |

## 跳过说明

NFR-010 已在 spec.md 标 `~~废弃~~` + `valid: false` + `wontfix`, 锚点保留但不再创建对应 issue.
跳过原因: Aaron 决定"这个需求没必要", sage round 3 标 `[wontfix]`, Probe/Archer 不会为废弃 NFR 生成测试.

## Issue body 格式 (verify_issue_schema.py L1-L8 验证)

- 标题: `[FR-XXX] {需求标题}` (正则 `^\[FR-\d{3}\]`)
- 标签: `Feature`
- `### 需求 ID`: `FR-XXX` / `NFR-XXX`
- `### Spec 链接`: `https://github.com/zillionare/specforge/blob/releases/v0.4/specs/004-quote-dialogue-v0.4/spec.md#fr-XXX`
- `### 验收标准`: `AC-1: ...`, `AC-2: ...`, ... 连续编号
