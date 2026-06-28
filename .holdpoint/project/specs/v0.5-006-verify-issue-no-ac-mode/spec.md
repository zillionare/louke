# verify-issue L7 支持 No-Acceptance + spec-fragment 模式 — Spec

- **Spec ID**: v0.5-006-verify-issue-no-ac-mode
- **来源**: issue #75
- **创建日期**: 2026-06-23
- **状态**: 草稿

## 背景

`verify_issue_schema.py` L7 当前对 `### 验收标准` 字段强约束: 必须是 `acceptance.md#ac-fr-XXX` 完整 URL + 锚点可达。

但实际项目里有三类 FR 不需要单独的 `acceptance.md` 章节:

| FR 类型 | AC 来源 | 例子 |
|---|---|---|
| 撮合 ground truth | test-plan §3.2 | FR-050/060/070/080 |
| 算法定义 | spec 章节公式 | FR-185 (4 条公式) |
| 声明性 FR | spec 章节描述 | FR-080 (跨模式差异) |

强行加 acceptance.md 占位章节 (millionaire 现有 83 行冗余) 是噪音, 不是工程。

## 目标

L7 支持三种 acceptance 形式, 用 issue body 的 `### 验收标准` 字段值区分:

| 字段值 | 校验 | 用途 |
|---|---|---|
| `acceptance.md#ac-fr-XXX` URL | acceptance.md 锚点存在 + 上下文含 FR-XXX | 默认: 有专属 AC |
| `spec(-vol)?.md#fr-XXX` URL | spec 锚点存在 + 上下文含 FR-XXX | AC 在 spec 章节中 |
| 字面值 `无` | acceptance.md `## No Acceptance` 列表包含此 FR | 算法 / 声明性 / 撮合 ground truth |

向后兼容: 现有 acceptance.md URL 形式不变, 旧 issue 不受影响。

## 用户故事

### US-010
story: 作为 specforge 用户, 我希望撮合 / 算法 / 声明性 FR 的 issue `验收标准` 字段可以填 `无`, 以便不为这些 FR 写虚假的 acceptance.md 章节, 减少文档噪音。
priority: P0

### US-020
story: 作为 specforge 用户, 我希望 AC 写在 spec 章节里的 FR, issue `验收标准` 字段可以填 spec-fragment URL, 以便 L7 校验 spec 锚点存在 (L5) + 上下文含 FR-XXX (L6), 不需要 acceptance.md 重复。
priority: P0

### US-030
story: 作为 specforge 用户, 我希望 acceptance.md 有一个 `## No Acceptance` 列表, 显式声明 "哪些 FR 没有专属 acceptance", 以便 L8 双向覆盖 + Lex 阶段一可追溯这些 FR 的 AC 来源。
priority: P0

### US-040
story: 作为 specforge 维护者, 我希望 L7 三种形式互相排斥 (一个 issue 只能选一种), 以便误填 (如同时填 URL + 列表) 报错。
priority: P1

## 用户使用场景

### scenario-010 撮合 FR (用 `无`)

acceptance.md:
```markdown
## No Acceptance

以下 FR 无专属 acceptance (AC 在 test-plan §3.2 中描述):

- FR-050
- FR-060
- FR-070
- FR-080
```

issue body:
```
### 验收标准
无
```

期望: L7 pass, 继续走 L8 双向覆盖。

### scenario-020 算法 FR (用 spec-fragment)

issue body:
```
### 验收标准
https://github.com/.../spec-strategy.md#fr-185
```

期望: L7 通过 spec-fragment URL 校验: spec-strategy.md 中存在 `<a id="fr-185"></a>` 锚点 + 锚点上下文含 "FR-185"。

### scenario-030 误填 (FR 不在 No Acceptance 列表中)

issue body:
```
### 验收标准
无
```

但 acceptance.md `## No Acceptance` 不含此 FR。

期望: L7 fail, 提示 "请把该 FR 加入 No Acceptance 列表, 或改用 acceptance.md#ac-fr-XXX URL"。

## 功能需求

### FR-010 L7 三模式判断

`check_issue` L7 分支:

| `raw_ac` 值 | 处理 |
|---|---|
| 空 | 报错 `L7 字段 '验收标准' 缺失` |
| `== "无"` | 走 FR-020 |
| 匹配 `RE_SPEC_URL` | 走 FR-030 (用现有 RE_SPEC_URL, 不引入新正则) |
| 匹配 `RE_AC_URL` | 现有 L7 逻辑 (向后兼容) |
| 其它 | 报错 `L7 字段格式错误`, 提示三种合法形式 |

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-020 `无` 模式校验

校验链:
1. 取 acceptance.md 全文
2. 解析 `## No Acceptance` 节 (下一 `##` 之前), 抽取 `- FR-XXX` / `- NFR-XXX` 项
3. `raw_fr` (需求 ID 字段值) 必须在集合中
4. 不在 → fail: `L7 字段 '无' 但 acceptance.md 的 '## No Acceptance' 列表中找不到 {raw_fr}`

边界:
- acceptance.md 不存在 → fail: `L7 字段 '无' 需要 acceptance.md 存在`
- acceptance.md 存在但无 `## No Acceptance` 节 → fail: `L7 acceptance.md 缺 '## No Acceptance' 列表`
- `## No Acceptance` 节为空 (无 `- FR-XXX` 项) → 同上 fail

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-030 spec-fragment 模式校验

校验链 (复用 L3-L6 已有的 spec 文本缓存):
1. 解析 `raw_ac` 为 spec URL, 用现有 `RE_SPEC_URL`
2. 取 spec 文本 (优先用 `spec_cache[OFFLINE]` 离线模式 / 已有缓存; 否则 fetch)
3. 验证 fragment 是 spec 中的 `fr-XXX` / `nfr-XXX` 锚点
4. 验证锚点上下文 (锚点行 + 后续 5 行) 含 `raw_fr`
5. 跳过 acceptance.md 校验

`raw_ac` 必须是 spec URL, 不能是 acceptance URL。spec-fragment 走 RE_SPEC_URL, acceptance 走 RE_AC_URL, 二者格式不同, 不会混淆。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-040 form 模板 regex 放松

`.github/ISSUE_TEMPLATE/feature.yml` 的 `acceptance_criteria` 字段 `regex` 由:
```
^https://github\.com/.../acceptance\.md#ac-(fr|nfr)-\d{3}$
```
改为:
```
^(无|https://github\.com/.../spec(-\w+)?\.md#(fr|nfr)-\d{3}|https://github\.com/.../acceptance\.md#ac-(fr|nfr)-\d{3})$
```

字段 `description` 追加:
```
- 默认填 acceptance.md#ac-fr-XXX URL (有专属 AC 章节)
- 或填 spec(-vol)?.md#fr-XXX URL (AC 在 spec 章节中描述)
- 或填字面值 "无" (FR 在 acceptance.md No Acceptance 列表中)
```

`placeholder` 保留原 URL 示例, 但 description 把三种形式讲清。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-050 Sage Step 5 决策逻辑

`agents/Sage.md` Step 5 章节追加决策树:

```
创建 issue 时, "验收标准" 字段值按 FR 性质三选一:
  1. FR 有专属 acceptance.md 章节 (AC-1/AC-2/...):
     → acceptance.md#ac-fr-XXX URL
  2. FR 的 AC 在 spec 章节中 (如算法定义 FR-XXX 含 F-CB-1/2/3/4 公式):
     → spec(-vol)?.md#fr-XXX URL
  3. FR 是 ground truth 覆盖 / 声明性 / 撮合 等 "无 AC 章节" 类型:
     → 字面值 "无"
     (同时在 acceptance.md 的 ## No Acceptance 列表追加该 FR)
```

并在创建 issue 前, 先 grep acceptance.md 的 No Acceptance 列表决定路径 3 是否成立。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### FR-060 Lex 阶段一 接受三种形式

`agents/Lex.md` 阶段一追加说明:

```
"验收标准" 字段校验: verify_issue_schema.py L7 接受三种形式:
  - acceptance.md#ac-fr-XXX URL (默认)
  - spec(-vol)?.md#fr-XXX URL (AC 在 spec)
  - 字面值 "无" (FR 在 acceptance.md No Acceptance 列表)
Lex 阶段一不强制偏好, 按 Sage 决策为准。
```

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

## 非功能需求

### NFR-010 向后兼容

现有所有用 `acceptance.md#ac-fr-XXX` URL 的 issue 不受影响, VERIFY-100/301/400/401/402 等测试 (acceptance.md 模式) 必须继续 pass。

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |

---

### NFR-020 完整测试覆盖

`tests/test_issue_form.bats` 新增 5 个 case:

- VERIFY-500: `无` + FR 在 No Acceptance 列表 → pass
- VERIFY-501: `无` + FR 不在 No Acceptance 列表 → fail
- VERIFY-502: `无` + acceptance.md 缺 No Acceptance 列表 → fail
- VERIFY-503: spec-fragment URL + 锚点存在 → pass
- VERIFY-504: spec-fragment URL + 锚点不存在 → fail
- VERIFY-505: spec-fragment URL + 锚点上下文无 FR-XXX → fail
- FORM-010: feature.yml regex 接受三种形式

| 有效需求 | 可测性 | 是否已决定 |
|---|---|---|
| ✅ | ✅ | ✅ |
