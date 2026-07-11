# v0.11-001 LLM Wiki 能力拓展与实现探索

- **Spec ID**: v0.11-001-web-ide
- **Scope**: FR-0301 / FR-0401 的探索性设计输入
- **Status**: Proposal，未决项仍以 `spec.md` 的 `Decided: ⚠️` 为准
- **原则**: 本文不实施服务、不迁移目录，只把后续 M-ARCH / M-TEST 所需边界做实

## 1. 结论

v0.11 的 LLM Wiki 不应继续被实现为“把 raw 会话和旧 pages 拼成大 prompt，再让 Agent 直接重写 Markdown”。它应成为一个**以项目设计文档为事实源、以结构化 claim ledger 为中间表示、带完整 provenance 和依赖图的增量文档编译器**。

核心边界如下：

1. 确定性程序负责源文件发现、Markdown 切片、内容 hash、删除检测、依赖计算、编号、链接、覆盖率检查和原子发布。
2. LLM 只负责无法可靠规则化的语义工作：事实归一、跨版本主题对齐、冲突解释、review 裁决抽取、FAQ 归纳；输出必须满足 JSON schema，不得直接编辑 Wiki。
3. `.louke/raw/` 是补充证据和决策过程，不再是 Wiki 的唯一或主要输入。story、spec、acceptance、test-plan、architecture、interfaces、review、README、`docs/*.md` 与项目元信息才是 v0.11 的主要事实源。
4. Wiki 是当前事实的 materialized view，不是历史归档。历史版本保留在源文档与 Git 中；当前文档只保留仍然有效的事实，以及最终技术裁决。
5. “全局唯一、最新、最全”必须分别由唯一性、时效性和覆盖率三个机器可验的 invariant 保证，不能只写进 prompt。

## 2. 现状审计

### 2.1 输入域错误

当前 `louke/librarian.py` 的 `compact` 只扫描 `.louke/raw/` 中 `status: resolved` 且带日期的会话；它没有扫描 `.louke/project/specs/**`、README、`docs/*.md`、`project.toml` 或 review 文档。因此当前实现即使模型表现完美，也无法满足 FR-0301 的“story、spec、test-plan、architecture、interfaces 最新且最全”。

### 2.2 增量判定不可靠

当前 cache 的有效状态主要是 `last_distill` 日期水位：

- 无法发现旧 spec 被修改；
- 无法发现源文件删除、重命名或状态变化；
- 同一天多次修改可能被遗漏；
- compact 成功后即推进水位，而不是 Wiki 成功发布后推进；
- Web 刷新只在 bundle 不存在时 compact，已存在的 bundle 可能长期陈旧。
- 每日 cron 只执行 `compact` 并推进水位，不执行 `rewrite`，因而定时任务本身不会更新 Wiki。
- 代码注释和静态测试声称存在 SHA-256 incremental cache，实际 cache 没有任何 source hash 索引。

因此“无源变化不更新”和“有任意源变化必更新”都没有得到保证。

### 2.3 M2 与实现契约不一致

历史 v0.7 spec 定义真正的 map N 次 + reduce 1 次，但当前代码生成一个再次内联全部 raw 的 `.compact-bundle-merged.md`，随后只执行一次 rewrite。它减少了文件尺寸管理问题，却没有减少最终上下文，也不是实际 map-reduce。

### 2.4 生成结果不可验证

LLM 当前直接写 `pages/*.md` 并自行删除旧页，缺少以下硬门禁：

- 五份 canonical 汇总是否都存在；
- 一个事实是否恰有至少一个有效来源；
- 所有纳入范围的源 section 是否被消费或说明排除原因；
- 同一主题是否被多个页面重复声明为 canonical；
- 源变化期间是否发布了混合版本；
- 失败是否留下半新半旧的 Wiki。

### 2.5 现有 Wiki 已直接证明 prompt-only 方案失效

仓库当前 Wiki 首页最后更新时间仍为 2026-06-15，七个页面主要是 2026-05/06 的会话事件记录，例如 `first-conversation`、`sage-interview`、`end-to-end-test`。它既不反映 v0.8-v0.11 的当前设计，也与 Librarian prompt 中“删除历史/event 页面”的规则冲突。

### 2.6 来源链接尚无端到端契约

Web 目前只支持 `spec`、`acceptance`、`test-plan` 三种 `/docs/{spec_id}/{doc_name}` 路由；`story`、`architecture`、`interfaces`、review、README 和 `docs/*.md` 没有统一 source route。普通 Markdown 相对链接在 GitHub 与 `/wiki/...` Web 路由中的解析基准也不同。因此 FR-0301 的“链接到相应位置”需要先定义逻辑 source URI 和统一解析器。

## 3. 三个可验收 invariant

### 3.1 全局唯一

- canonical kind 固定为 `stories`、`spec`、`test-plan`、`architecture`、`interfaces`，每种必须且只能有一个生成产物；
- 每个当前事实具有稳定 `claim_id` 和 `topic_id`；
- 一个 `claim_id` 只能有一个 active 版本；旧版本标为 superseded，不得同时渲染；
- 手工 Wiki 与生成 Wiki 分 namespace，手工页面不能伪装成 canonical 汇总；
- lint 对重复 canonical kind、重复 active claim、重复 decision ID 返回非 0。

### 3.2 最新

- 每次 scan 对所有纳入范围的源文件计算 SHA-256，并记录新增、修改、删除、重命名；
- publish manifest 记录完整 `source_set_digest`，只有该 digest 与当前扫描一致时页面才显示 fresh；
- 源在 build 期间再次变化时，中止本次发布并重新排队；
- 无源变化时不调用 LLM、不改写产物、不改变文件 mtime，只记录 no-op run；
- cache 只在五份文档全部生成且 lint 通过、原子发布成功后提交。

### 3.3 最全

- 每个 in-scope section 必须在 coverage ledger 中处于 `rendered`、`superseded`、`conflict` 或 `excluded_with_reason` 之一；不允许 silent drop；
- 五类文档各自的 mandatory section 覆盖率为 100%；
- 每条渲染事实至少含一个可解析 source reference；
- review 中所有“已解决且包含明确结果和原因”的争议必须进入 decisions；
- 缺少 architecture/interfaces/test-plan 时不得生成看似完整的内容，应生成明确的 coverage gap，并使 build 状态为 `degraded` 而非 `fresh`。

## 4. 信息架构

建议生成区如下。具体目录属于 FR-0401 的待确认项，此处仅提供推荐映射。

```text
.louke/wiki/
├── index.md                         # 首页：README 入口、canonical docs、freshness、gap
├── pages/
│   ├── generated/
│   │   ├── stories.md             # 全局唯一
│   │   ├── spec.md                # 全局唯一
│   │   ├── test-plan.md           # 全局唯一
│   │   ├── architecture.md        # 全局唯一
│   │   ├── interfaces.md          # 全局唯一
│   │   ├── decisions.md           # review 最终裁决
│   │   ├── faq.md
│   │   └── project-info.md
│   └── manual/                         # 人工维护、非 canonical
└── .build/                           # 运行态，不进入页面导航
    ├── manifest.json                  # source hashes + publish digest
    ├── claims.jsonl                   # current/superseded claims + provenance
    ├── coverage.json                  # source section disposition
    ├── conflicts.json                 # 未裁定冲突
    ├── lock                           # 单项目互斥
    ├── runs/{run_id}.json             # 状态、耗时、模型、token、错误
    └── staging/{run_id}/              # 通过 lint 后才原子发布
```

不建议继续使用 `entries/`、`consolidated.md` 和按会话命名的 `pages/*.md` 承担 canonical 事实。迁移时先读入作为 legacy evidence，发布成功后移入 legacy 区或停止导航；是否物理删除另行确认。

## 5. 事实源与权威规则

### 5.1 默认纳入范围

| 源                                                        | 用途                         | 默认权威性                            |
| --------------------------------------------------------- | ---------------------------- | ------------------------------------- |
| `.louke/project/specs/*/story.md`、`prd.md`               | 原始意图、用户故事           | 意图权威                              |
| `spec.md`                                                 | 规范性需求、边界、约束       | 需求权威                              |
| `acceptance.md`                                           | 可观察通过条件               | 验收权威                              |
| `test-plan.md`                                            | 测试策略、覆盖与环境         | 测试权威                              |
| `architecture.md`                                         | 模块、依赖、trade-off        | 架构权威                              |
| `interfaces.md`                                           | CLI/HTTP/file/schema 契约    | 接口权威                              |
| `review*.md`、`code-review*.md`                           | 争议、裁决、理由、未决问题   | 仅显式已裁定内容可成为 final decision |
| `.louke/project/project.toml`、`history.md`、Git 本地状态 | 版本、分支、项目、开发时间   | 项目信息权威                          |
| `README*`、`docs/*.md`                                    | 首页入口、用户说明、补充解释 | 说明性证据，不能覆盖规范文档          |
| `.louke/raw/**/*.md`                                      | 决策过程和缺失上下文         | 补充证据；不能单独覆盖已发布规范      |

源发现规则必须配置化并固定排序；不能依赖 filesystem mtime 决定权威性。

### 5.2 冲突优先级

推荐顺序：

1. 同一主题的显式 `supersedes` / `replaces` 声明；
2. 已接受的最终裁决，且同时具有结果、原因和来源；
3. 同一 artifact kind 中状态更高、版本更新的规范文档；
4. 当前 active spec 对其明确覆盖的主题；
5. 更早仍未被覆盖的事实继续有效；
6. 无法证明覆盖关系时，不按“文件更新”猜测，写入 `conflicts.json` 并在 Wiki 显示未决冲突。

“最新版本整体覆盖全部旧版本”是错误规则，因为新 spec 通常只描述增量功能；正确语义是**按 topic 局部覆盖**。

### 5.3 状态要求

目录名中的版本号只能作为 fallback，不能单独代表有效状态。后续应让设计文档 frontmatter 或 manifest 至少提供：

```yaml
spec_id: v0.11-001-web-ide
status: draft | accepted | in_progress | shipped | superseded
effective_from: 2026-07-11
supersedes: []
```

缺失状态时允许索引，但标记 `status_unknown`，不得静默提升为 shipped。

## 6. 中间数据模型

LLM 不直接产 Markdown，而是产受 schema 约束的 records。最小 claim 结构建议为：

```json
{
  "claim_id": "claim:interfaces:wiki-refresh-trigger",
  "topic_id": "wiki-refresh",
  "kind": "interface",
  "text": "Wiki 支持手动更新，并每日仅在源变化时更新。",
  "state": "active",
  "authority": "normative",
  "source_refs": [
    {
      "path": ".louke/project/specs/v0.11-001-web-ide/spec.md",
      "anchor": "fr-0301",
      "section_hash": "sha256:...",
      "line_start": 92,
      "line_end": 105
    }
  ],
  "supersedes": [],
  "confidence": 1.0
}
```

技术裁决结构至少包括 `decision_id`、`topic_id`、`question`、`alternatives`、`ruling`、`rationale`、`status` 和 `source_refs`。

若 review 只有争议，没有明确 `ruling` 或 `rationale`，记录为 unresolved，不能伪造 final decision。

## 7. 编译流水线

```text
discover -> parse -> fingerprint -> impact -> extract/map
         -> reconcile/reduce -> render -> validate -> atomic publish
```

### 7.1 Discover

- 按 allowlist glob 扫描所有事实源；
- 记录 path、doc kind、spec ID、版本、状态、Git blob（若有）、SHA-256；
- 对比上次 manifest，识别 added/modified/deleted/renamed；
- 计算排序稳定的 `source_set_digest`。

### 7.2 Parse

- Markdown 按 heading tree 切 section，代码块和表格保持完整；
- 使用与 Web renderer 相同的 heading slug 算法；
- 复用 `DiscussParser` 提取 inline discussion，但扩展出 resolution/rationale/source span；
- TOML、Git 元信息使用确定性 parser，不交给 LLM 猜测。

### 7.3 Impact

依赖图至少维护 `source section -> claim -> output page`。只重新处理：

- 发生变化的 section；
- 引用这些 section 的 claim；
- 与这些 claim 同 topic、需要重新裁决的 claim；
- 受影响的 output page。

删除源文件必须传播为 claim retraction；不能只处理新增文本。

### 7.4 Extract / Map

- 每个 section 独立或按同一 heading subtree 分块；
- LLM 返回 JSON records，并逐字段带 source span；
- schema 校验失败可有限次数重试；仍失败则本次 build 失败，不发布部分结果；
- 未变化 section 复用缓存 records。

### 7.5 Reconcile / Reduce

- 先按 `topic_id + kind` 聚合，不按月份聚合；
- 将旧 active claims、changed claims、删除事件和相关 review decisions 一并输入；
- 按第 5 节权威规则产生 active/superseded/conflict disposition；
- 对大项目做 topic-level reduce，再做每个 canonical page 的 page-level reduce，不能把所有原文重新拼成一个 merged bundle。

### 7.6 Render

- 模板确定文档结构和标题序号，LLM 只提供内容 records；
- 展示标题用 `1.`、`1.1` 等文档内序号，不使用 FR-XXXX；
- 每个事实句或最小事实列表项末尾附来源标记；
- 禁止在正文写“由 Librarian 于某日生成”之类导致每日无意义 diff 的内容；freshness 放页面 metadata/UI。

### 7.7 Validate

发布前至少执行：

1. schema validation；
2. exactly-five canonical validation；
3. active claim uniqueness；
4. source link existence + anchor resolution；
5. mandatory coverage = 100%；
6. no silent drop；
7. no FR-XXXX display heading；
8. conflicts 不得伪装为 final facts；
9. source_set_digest 再检查；
10. Markdown render smoke test。

### 7.8 Atomic publish

- 先写 `.build/staging/{run_id}`；
- 全部门禁通过后，一次替换整个 `pages/generated/` 与 index；
- 最后提交 manifest/claims/coverage；
- 任一步失败保留上一个完整版本，并在 UI 显示 failed run；
- 单项目加文件锁，手动与定时 build 不并发；重复请求合并为一次 pending build。

## 8. 来源链接设计

建议引入逻辑 URI，而不是让生成器猜 Web 相对路径：

```text
louke-source:.louke/project/specs/v0.11-001-web-ide/spec.md#fr-0301
```

Markdown renderer 将它解析为统一只读 source viewer，例如：

```text
/workspace/source?path=.louke/project/specs/.../spec.md&anchor=fr-0301
```

source viewer 必须复用 FR-0701/NFR-0201 的 workspace 边界、符号链接和大文件批准规则。claim ledger 同时保留 line span 和 section hash：

- heading anchor 供人导航；
- line span 供 Web 高亮；
- section hash 供系统判断链接指向的证据是否已漂移。

如果希望 GitHub 中也可点击，renderer/exporter 可在导出时把逻辑 URI 重写为 repository-relative Markdown 链接；不要在 claim 中同时维护两套路径。

## 9. 首页、FAQ 与项目信息

### 9.1 首页

首页应由确定性模板生成，包含：

- README 标题、简短 lede 与“打开 README”入口；
- 五份 canonical docs 入口；
- decisions、FAQ、project-info 入口；
- freshness：当前 source digest、最后成功 build、是否有待处理源变化；
- coverage：已覆盖、冲突、缺失 artifact；
- 最近一次 build 失败时的非破坏性告警。

README 正文不建议全量复制到 index，否则形成第二份易陈旧副本；如用户最终要求“包含 README 内容”，可确定性嵌入当前 README，而不是让 LLM 摘写一份。

### 9.2 FAQ

FAQ 只能来自以下证据：

- 多个 source/review/raw 中反复出现的问题；
- README/docs 中已有问答；
- 已裁定 decision 可以回答的问题。

答案必须引用 active claims。无证据的问题进入 suggested questions，不自动生成答案。

### 9.3 项目信息

- 版本、GitHub Project、release branch：优先 `project.toml`；
- 当前实际分支：本地 Git；与 `project.toml` 不一致时同时显示 declared/observed 并报 conflict；
- 开发开始/结束时间：优先显式 metadata/history；缺少结束时间显示“进行中/未知”，不得用文件 mtime 猜；
- 外部 GitHub API 只用于补充校验，不应成为离线 build 的硬依赖。

## 10. Web 与定时更新协议

现有 `POST /api/wiki/refresh` 是同步、最长等待十分钟的单请求。v0.11 建议改为 job 协议：

```text
POST /api/wiki/build             -> 202 {job_id, change_summary}
GET  /api/wiki/build/{job_id}    -> queued|scanning|mapping|reducing|validating|published|noop|failed
GET  /api/wiki/status            -> freshness, source_digest, coverage, conflicts, latest_run
GET  /api/wiki/diff/{job_id}     -> 发布前/后的生成文档 diff
```

手动按钮与每日任务调用同一个 `scan -> maybe build` 服务：

- source digest 未变化：job 结束为 `noop`；
- 有变化：进入 build；
- build 失败：旧 Wiki 继续服务；
- build 成功：通过事件流通知浏览器刷新；
- `force` 只允许显式人工操作，用于模型/模板升级后的全量重建。

定时器不应再只运行 `compact`；“检查”和“发布”必须是同一事务链，cache 不得在 publish 前推进。

## 11. LLM 使用策略

### 11.1 应交给 LLM

- 不同版本对同一语义 topic 的对齐；
- 将长段规范拆成最小可引用事实；
- review 对话中的争议、方案、裁决与理由抽取；
- 多条一致 claims 的精炼表达；
- 从已有事实生成 FAQ 问法和回答草稿；
- 对显式冲突给出解释，但不能擅自拍板。

### 11.2 不应交给 LLM

- 文件发现、版本排序、hash、删除检测；
- source anchor 和 URL 拼接；
- 编号、模板结构、目录名；
- “是否有五份文档”“引用是否存在”等验证；
- 文件写入、删除和最终发布；
- 项目 branch/version 等可直接读取的值。

### 11.3 不立即引入向量数据库

v0.11 P0 的目标是构建五份全局文档，不是开放域问答。基于 heading/section、doc kind 和 topic graph 的确定性检索足够，且更容易证明 coverage。后续增加“Ask Wiki”时可先用 SQLite FTS5 + claim/source 图做 hybrid retrieval；只有规模和质量评测证明必要时再引入 embedding/vector store。

## 12. 可进一步拓展的能力

在上述 claim/provenance 基座上，可低成本扩展：

1. **反向影响分析**：修改某条 spec 时，显示受影响的接口、架构和测试段落。
2. **矛盾雷达**：展示 declared branch 与 observed branch、spec 与 interface、acceptance 与 test-plan 的冲突。
3. **覆盖缺口面板**：哪些 story 没有 spec，哪些 requirement 没有 acceptance/test，哪些 interface 没有 test-plan。
4. **Wiki time travel**：按 publish manifest 或 Git commit 查看当时的 current truth。
5. **变更说明生成**：比较两个 source digest，对 active claims 做 added/changed/retracted diff。
6. **Ask Wiki**：回答只允许基于 active claims，逐句引用；无证据时明确说不知道。
7. **Review decision registry**：按 topic、状态、版本过滤所有 final/unresolved 技术争议。
8. **人工纠偏**：用户可标记错误 merge/supersedes；纠偏写入规则层，不直接改生成 Markdown，后续 build 可复现。
9. **质量评测集**：维护一组项目问题及期望 source refs，做模型回归，而不只测试“进程返回 0”。

其中 1-3 是 v0.11 最值得一并保留接口余量的能力；4-9 可后续分期。

## 13. 推荐模块边界

后续 M-ARCH 可按以下 Python 模块拆分，避免继续扩大 `librarian.py` 与 `web/app.py`：

```text
louke/wiki/
├── sources.py       # allowlist discovery + metadata/status
├── markdown.py      # heading tree + anchors + source spans
├── manifest.py      # hashes, digest, rename/delete detection
├── claims.py        # schemas + ledger
├── decisions.py     # discussion/review extraction contract
├── impact.py        # source -> claim -> output dependencies
├── llm.py           # structured OpenCode invocation only
├── reconcile.py     # authority/supersedes/conflicts
├── render.py        # deterministic Markdown templates
├── validate.py      # uniqueness/provenance/coverage gates
├── publish.py       # lock, staging, atomic publish, run records
└── service.py       # scan/build/status orchestration
```

`louke/librarian.py` 变为兼容 CLI adapter；Web route 调 `wiki.service`，而不是自己拼 subprocess 前置条件。OpenCode 仍可作为模型运行时，但通过 `llm.py` 返回 JSON，不能拥有 Wiki 目录 edit 权限。

## 14. 测试策略与 FR-0301 验收补强

### 14.1 规则单元测试

- 同一 fixture 每次 scan 得到相同 digest；
- 修改、删除、重命名都能产生 change event；
- 无变化 build 不调用 LLM且不改 mtime；
- status/version/supersedes 优先级表逐项覆盖；
- source URI path traversal、symlink escape 被拒绝；
- heading anchor 与 Web renderer 完全一致。

### 14.2 编译集成测试

- 多版本 spec：新版本只覆盖一个 topic，旧版本未涉及 topic 仍保留；
- 删除源 section：对应 claim 被撤回，受影响页面更新；
- review 有争议但无结果：只进 unresolved；有结果无原因：不得成为 final；
- 五份文档任一缺失、任一 citation 断裂或一个 source section silent drop：不发布；
- build 中途源变化：本次 staging 丢弃；
- LLM 返回非法 JSON、重复 claim、幻觉 path：重试后失败且旧 Wiki 不变；
- 手动和 cron 并发：只产生一个 publish。

### 14.3 质量评测

为 Louke 自身维护 golden corpus，至少回答：

- 当前 Wiki 的输入源有哪些？
- 当前 Web 文档路由支持哪些 artifact？
- M2 是否为真实 map-reduce？
- 当前 active release/spec 与实际 branch 是否一致？
- 某个已裁决 review 的结果和原因是什么？

每题同时断言答案要点、禁止项和 source refs；模型或 prompt 升级必须跑回归。

### 14.4 建议新增/细化的 AC

1. 任一 in-scope 源新增、修改、删除后，成功 build 的 manifest digest 必须等于当前 source digest；无变化时产物字节与 mtime 不变。
2. 五种 canonical kind 各恰好一个；重复或缺失时 build 失败且旧产物不变。
3. 每条 active claim 至少一个可解析来源，所有 mandatory source section 均有 disposition。
4. 新版本部分覆盖旧版本时，只替换相关 topic，不得删除旧版本仍有效的未覆盖事实。
5. 显式冲突在无 final ruling 时必须作为 unresolved 展示，不得由模型静默选择。
6. review decision 只有同时具备争议、结果、原因和来源时才可标 final。
7. build 期间源变化或任一 validator 失败时不得发布部分页面。
8. 手动与每日任务走相同 change detector 和 publish pipeline。

## 15. 迁移顺序

### Phase 0：冻结契约

- 决定 source 范围、status schema、冲突优先级、目录映射和 source URI；
- 把第 14.4 节转成正式 AC；
- 先建立当前仓库 golden corpus。

### Phase 1：无 LLM 的确定性骨架

- source discovery、section parser、manifest/digest、source viewer/link resolver；
- 固定五文档模板、staging/atomic publish、validators；
- 用 fixture claims 走通完整编译。

### Phase 2：结构化 LLM extraction

- section map JSON schema、topic reconcile、decision extraction；
- 禁止 LLM 文件写权限；
- 加 invalid output 与 hallucinated source 对抗测试。

### Phase 3：增量与服务化

- impact graph、删除传播、job API、锁、事件与每日 scan；
- no-op、失败保留旧版、fresh/degraded/stale UI。

### Phase 4：迁移与 dogfood

- 用全量 rebuild 生成 Louke 自身五份 canonical docs；
- 与人工 source inventory 对账到 100%；
- 停止导航旧 event pages，但保留可回滚 snapshot；
- 连续运行一段时间后再决定物理清理 legacy。

## 16. 需要用户拍板的最小决策

| 决策                                 | 推荐                                      | 影响                                       |
| ------------------------------------ | ----------------------------------------- | ------------------------------------------ |
| canonical 输出是否只允许生成器写     | **是**                                    | 才能保证可复现和唯一；人工内容放 `manual/` |
| status 缺失如何处理                  | **索引但标 unknown，不视为 shipped**      | 避免最高版本 draft 静默覆盖现状            |
| unresolved conflict 是否阻塞全部发布 | **不阻塞无关 topic；相关页面标 degraded** | 兼顾可用性和诚实性                         |
| README 首页策略                      | **确定性 lede + 入口；可配置全量嵌入**    | 避免第二份 LLM 摘要漂移                    |
| 缺失某类源文档时是否生成占位         | **生成 gap 页面但状态 degraded**          | 五个入口稳定，同时不伪造完整性             |
| 是否立即引入向量库                   | **否**                                    | 先把 provenance、coverage、冲突做对        |
| 旧 Wiki pages 处理                   | **停止导航并保留 snapshot，稳定后再清理** | 可回滚，避免继续污染 canonical             |

> **Aaron:** 除旧 wiki pages 之外，都同意推荐项。旧 wiki pages 如果是指 louke 本项目，不用考虑。用户将完全清除掉它们。如果是指最终用户那里，也不考虑。

## 17. 外部探索带来的取舍

[仓库级文档生成研究 RepoAgent](https://aclanthology.org/2024.emnlp-demo.46/) 采用结构化仓库分析和增量更新；[Microsoft GraphRAG 索引数据流](https://microsoft.github.io/graphrag/index/default_dataflow/) 显式保留 document 到 text unit 的 provenance，其 global search 使用分层 map-reduce。Louke 无需立即复制完整知识图谱或向量设施，但应采用“结构化中间表示 + provenance + dependency-driven rebuild”原则。
