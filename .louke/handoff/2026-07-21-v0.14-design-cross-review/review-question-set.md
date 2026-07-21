# Review Question Set — 外部交叉评审

> 配套 HANDOFF.md。每题一句话答复 + file:line 引用即可。Verdict / blockers 是主要产物；这些问题是辅助维度。

## A. spec-002 (workflow-reflow-design) — M-DESIGN 评审

### A1. Runtime authority 单一性
- **Q**：所有 `design-artifacts/` 里的 schema、contract instance、prompt candidate、agent task/result schema，是否在 dispatch、validation、persistence 三个语义点上都只赋予 Runtime/program 唯一 authority？有没有任何文件把 authority 隐式外移给 Agent（Archer/Prism）、subagent provider、Maestro 或 Human？
- **期望证据**：在 `architecture.md §1`、`interfaces.md IF-DES-01/02`、`archer-design-task-input-1.0.0.schema.json` 的 `dispatch.authority` / `prism-design-review-task-input` 的同类字段中分别确认。

### A2. Schema / contract 的复用性（FR-1900/2500/2600）
- **Q**：把 `archer-design-task-input-1.0.0.schema.json` 当 program-owned registry schema 时，下一 design revision（同样 spec 002，下一 design revision）能否被同样 schema 接受？跨 spec（如 spec 003）能否被同样 schema 接受？
- **期望**：当前答案是 NO（Prism round 5 B-2 已确认）。请独立验证：修改 `task spec.id` 或 `design_revision.revision` 之后 schema 是否仍校验通过？
- **复现**：
  ```python
  import json, jsonschema
  s = json.load(open('.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/registry/agent-io/archer-design-task-input-1.0.0.schema.json'))
  task = json.load(open('.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/inputs/archer-author-task-manifest.candidate.json'))
  mut = json.loads(json.dumps(task))
  mut['spec']['id'] = 'v0.14-003-workflow-reflow-impl'
  list(jsonschema.Draft202012Validator(s).iter_errors(mut))  # 应非空
  ```

### A3. release-version schema 是否真通用
- **Q**：`design-artifacts/registry/schemas/release-version-1.0.0.schema.json` 是不是只约束 envelope/类型/required mapping？有没有 hard-code 当前 release 的 0.14.0 / 分支 / pyproject.toml / adapter 等值？
- **期望**：是通用 schema；具体 release 值只出现在 `contracts/release-version.candidate.json`。Node/SemVer fixture `validation/release-version-node-host.valid.candidate.json` 应当用同样 schema 校验通过。

### A4. Trust binding 一致性
- **Q**：`prompts/reviewer-binding.candidate.json` 和 `prompts/deployment-readback.candidate.json` 中声明的 trusted active reviewer digest 是否与磁盘 `.opencode/agents/prism.md` 的实际 digest 一致？`staging/{archer,prism}.render.candidate.json` 中的 `active_digest` 是否一致？
- **期望**：三个文件全部 current 时应一致；当前 disk digest 是 `2f79efed7eaee4f4679d654b0337eb7cdb7abcde840c55257511ccd5769e83d1`。

### A5. AC ↔ IF ↔ ARC ↔ contract 四向闭环
- **Q**：每个 AC（在 acceptance.md 中）是否能找到至少 1 个 observable interface、1 个 architecture anchor、1 个 machine contract kind？
- **期望**：34 AC 全部闭环；至少在 sample 5 条上验证（推荐 AC-FR0100-01、AC-FR0700-01、AC-FR1400-01、AC-FR1700-01、AC-FR2500-01）。

### A6. Machine contract required kinds 完整
- **Q**：`registry/registry.candidate.json` 中声明的 active schema kinds 是不是覆盖 spec 强制的 7 类？`integration-test`、`e2e-test`、`pre-commit`、`github-actions-ci`、`release-version`、`build-artifact`、`publish-recovery` 是不是全部有 schema + 至少一份 candidate instance？
- **期望**：7/7。

### A7. 7 schemas（contract） + 4 schemas（Agent I/O） meta-validity
- **Q**：所有 11 个 schema 在 `python -c "import jsonschema; jsonschema.Draft202012Validator.check_schema(load(open(path)))"` 下是否都 meta-valid？所有 7 份 candidate contract instance 是否都对各自 schema validate？8 份 negative fixture 是否都 fail？
- **期望**：全 pass；负 fixture 全 fail。

### A8. PR-1900 secret hygiene
- **Q**：candidate JSON artifact 中是否含任何明文 secret / password / token / API key（即便非完整）？
- **期望**：否；如发现任何明文 secret，必须 REJECT。

### A9. 流程基线
- **Q**：候选合同是否清晰区分 candidate / canonical / active 状态？是否声明 explicit current_fail_closed 列表？是否禁止 candidate 自证或自激活？
- **期望**：是；candidate-vs-active 分离正确。

### A10. Issue traceability
- **Q**：spec-002 的 34 个 GitHub Issue (#250–#283) 是否覆盖 28 FR + 6 NFR？是否有重复 / 缺失？
- **期望**：34/34 issue，无重复 id，Project 20 全关联。

---

## B. spec-003 (workflow-reflow-impl) — M-DESIGN 评审（首次）

### B1. 需求范围与 density
- **Q**：spec-003 的 30 FR + 6 NFR + 36 AC 是否内部一致（无 orphan FR、无重复 AC）？scope 是否 ≤ 30 FR（满足 v0.14 scope gate）？
- **期望**：30/6/36 一致；FR ≤ 30。

### B2. 与 spec-002 的继承关系
- **Q**：`spec-003/test-plan.md` 与 `architecture.md` 中是否声明 inherited `IF-*`（来自 spec-002）？这些 inherited IF 是不是与 spec-002 的 `interfaces.md` 真实存在并 digest 对应？
- **期望**：声明的 inherited IF 全部存在；digest 链可独立验证。

### B3. ARC-01 命名 vs spec-002 的 ARC-WEB/IF-DES 命名
- **Q**：spec-002 用语义化 anchor（`ARC-WEB`、`IF-DES-01`），spec-003 用编号 anchor（`ARC-01` 或类似）。这种命名分歧是设计分歧还是 isolated 决定？是否会破坏跨 spec 检索 / validation tool 的统一性？
- **期望**：评估是否需要在 implementation 阶段统一，或保留作为两个 spec 的 explicit 约定。

### B4. ARC-01.. / IF-#### 完整性
- **Q**：spec-003 的 architecture.md 共有多少个 ARC-##？interfaces.md 共有多少个 IF-####？每个 ARC 是否至少 1 个 IF 引用？每个 IF 是否有 1 个 ARC 承载？
- **期望**：≥ 36 个 ARC、≥ 16 个 IF（参考 sizes）；双向无 orphan。

### B5. 36 AC ↔ IF ↔ ARC ↔ test layer 闭环
- **Q**：每个 AC 是否都能在 test-plan.md 找到 1 个 assigned test layer？是否在 interfaces.md 找到 1 个 observable interface？是否在 architecture.md 找到 1 个 architecture anchor？
- **期望**：36/36 闭环，sample 5 条独立验证。

### B6. 安全 / 隐私 / Secret
- **Q**：spec-003 的 design 是否覆盖 secret scanning、权限边界、replay 防护、rollback 策略？是否有任何 step 把 secret 写入日志或 evidence？
- **期望**：覆盖；evidence 不含明文 secret。

### B7. R-G-R / B/R/G/(Refactor) sibling Git 模型
- **Q**：spec-003 architecture.md 是否清晰描述 Red → Green → Refactor 的 sibling Git 模式（避免 squash merge 破坏 trace）？Devon 的 commit 格式是否强制 FR/NFR + issue 号？
- **期望**：清晰；强制；spec-001 实施已示范，可对照。

### B8. Release / publish / rollback 流程
- **Q**：spec-003 的 release 流程是否定义 pre-flight gate、artifact identity、rollback 路径？与 spec-002 的 publish-recovery contract 是否一致？
- **期望**：完整；与 spec-002 contract 一致。

### B9. Issue traceability
- **Q**：spec-003 的 36 个 GitHub Issue (#284–#319) 是否覆盖 30 FR + 6 NFR？是否都标了 `Feature` + `v0.14` + `FR-1800` + `spec:v0.14-003-workflow-reflow-impl`？Project 20 是否全关联？
- **期望**：36/36 issue，无重复，Project 20 关联。

### B10. flow.md 流程图
- **Q**：spec-003/flow.md 是否覆盖 M-STORY → M-SPEC → M-ACC → M-LOCK-1 → M-DESIGN → M-DEV → M-E2E → M-SECURITY → M-MILESTONE？是否清晰标记返回上游路径与权限边界？
- **期望**：完整；不漏阶段；返回路径明确。

---

## C. 全局 / 跨 spec 维度

### C1. candidate 部署边界
- **Q**：spec-002 的 candidate prompt bundle / schema / contract 与 `.opencode/agents/**`（active deployment）之间的边界是否清晰？是否有任何"candidate 自激活"风险？
- **期望**：边界清晰；candidate 不可自证或自激活。

### C2. mid-v0.14 约束
- **Q**：是否注意到本项目处于 v0.14 建设期，因此**不应**将"Runtime 已激活"、"registry 已部署"、"CI 已跑过 real-smoke"等作为评审门槛？
- **期望**：是；如不这样理解，请明确指出。

### C3. 提交 / push / tag 边界
- **Q**：从评审角度看，spec-002 / spec-003 在被设计 PASS 后，Devon 实现期间应采用什么 commit / branch / tag 策略？是否与 spec-001 的 `v0.14.0-001-impl` 命名风格一致？
- **期望**：`v0.14.0-002-impl` / `v0.14.0-003-impl` 风格；feature 不分多 branch；单 release branch 模式。

### C4. spec 拆分逻辑
- **Q**：把 v0.14 拆成 001/002/003 三批 release 是否合理？是否有 spec 跨度过大、应进一步拆分？或反之，过度拆分？
- **期望**：合理 / 建议拆分 / 建议合并 + 理由。
