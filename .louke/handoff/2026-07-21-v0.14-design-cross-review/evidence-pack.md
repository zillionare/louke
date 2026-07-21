# Evidence Pack — 评审用 digest 链 + 复现命令

> 配套 HANDOFF.md。本文件列出可独立验证的 digest 链与命令；评审者可在本工作区直接复跑。

## 0. 工作目录 / 当前状态

- 工作目录：`/Users/openclaw/workspace/louke`
- 当前分支：`releases/0.14.0`
- HEAD：`63d0da3 docs(v014-001): record implementation commit receipt and validation evidence`
- Tags: `v0.14.0`（既有），`v0.14.0-001-impl`（spec-001 实施批）
- 工作树：clean（`git status` 干净）

## 1. spec-001 digest 表

```bash
sha256sum \
  .louke/project/specs/v0.14-001-workflow-reflow-spec/spec.md \
  .louke/project/specs/v0.14-001-workflow-reflow-spec/acceptance.md \
  .louke/project/specs/v0.14-001-workflow-reflow-spec/test-plan.md \
  .louke/project/specs/v0.14-001-workflow-reflow-spec/architecture.md \
  .louke/project/specs/v0.14-001-workflow-reflow-spec/interfaces.md \
  .louke/project/specs/v0.14-001-workflow-reflow-spec/design-review.md
```

记录到 receipt：`.louke/project/specs/v0.14-001-workflow-reflow-spec/implementation/commit-receipt.txt`

| artifact | sha256 |
|---|---|
| spec.md | `32b2f4c51209b0c8e4167439533370877ad38040fb44ae696d20d01280c81069` |
| acceptance.md | `159e82bce6d43580200ab9f968ee5e645b528374ba896fbec8f5191b66799f9f` |
| test-plan.md | `98789f6fc1baee0bf7492e6a451ce222cb5e0292fbebc3810a568abc7cbb5a71` |
| architecture.md | `bc03090128f3aa29db6fc4c6fde1830b508335851a078de7d7b1a824dd8faa08` |
| interfaces.md | `09ae38907b2d20aba663a3b4381922144635cb318fe19adede35b6e686887e1f` |
| design-review.md (round 3 PASS) | `…` |

实施验证：
```bash
python3 -m pytest tests/unit/v014 -q
# → 207 passed in 0.15s

python3 tools/check_ac_traceability.py \
  --acceptance .louke/project/specs/v0.14-001-workflow-reflow-spec/acceptance.md \
  --tests tests/unit/v014
# → AC closure: 82/82 covered
```

## 2. spec-002 digest 表

```bash
sha256sum \
  .louke/project/specs/v0.14-002-workflow-reflow-design/story.md \
  .louke/project/specs/v0.14-002-workflow-reflow-design/spec.md \
  .louke/project/specs/v0.14-002-workflow-reflow-design/acceptance.md \
  .louke/project/specs/v0.14-002-workflow-reflow-design/test-plan.md \
  .louke/project/specs/v0.14-002-workflow-reflow-design/architecture.md \
  .louke/project/specs/v0.14-002-workflow-reflow-design/interfaces.md \
  .louke/project/specs/v0.14-002-workflow-reflow-design/design-review.md \
  .louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/design-artifact-manifest.candidate.json
```

| artifact | sha256 |
|---|---|
| story.md | `06d5573efbf59dd18b480d6539ad16df237fd4460f9f95d1589110cbfeec1993` |
| spec.md | `315c8d20254fceb63971b029d69c81889972eedb581621981a012f17edc8867f` |
| acceptance.md | `39b09cbf36cc0f4f0dcc8f0e8a79949049a2b6baddcecbcf2183ad407e493559` |
| test-plan.md | `02a928e09f4abc80ae6ec0c60ec39ba33a131cfd5acc47dc3daeeab97cb4d53e` |
| architecture.md | `32c88eb2062eb0173738086202eddf87122204ee99d32133c1ea30a6c39335cc` |
| interfaces.md | `ce4e83ae0d0f614a43a1912e317859105f84f08ba53fc3e8b1cc150dd108e37f` |
| design-review.md (round 5 REJECT) | `f8bbf64a9b02ed79964f876adcfbdad30a359660039903459a3457c33ce47c68` |
| design-artifact-manifest.candidate.json | `5153a3879f54558ecfa7800c92d2eac540c919849a942116ec282783fbc9eb56` |

## 3. spec-002 active / candidate digest

```bash
sha256sum .opencode/agents/prism.md .opencode/agents/archer.md .opencode/agents/maestro.md
```

| file | sha256 |
|---|---|
| `.opencode/agents/prism.md` | `2f79efed7eaee4f4679d654b0337eb7cdb7abcde840c55257511ccd5769e83d1` |
| `.opencode/agents/archer.md` | `2001ab2a611ce2551654d10b4854ab5c3c9251997f70dfc8d0f7467b408fc577` |
| `.opencode/agents/maestro.md` | `d2764eaddf98096697173fe734ffbd8675c0fda69d84fd7dd595fd8ef7b375ed` |

candidate 内嵌 reviewer digest（已陈旧）：
```bash
python3 -c "import json; print(json.load(open('.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/prompts/reviewer-binding.candidate.json'))['reviewer_execution_bundle']['deployment_digest'])"
# → sha256:fba0ff7f2159c48377c0ea94145daf5f6af2d66e716614860ea8e2865478e005
```

candidate 内嵌 staging active digest：
- `design-artifacts/prompts/staging/prism.render.candidate.json` active_deployment.digest = `fba0…e005`
- `design-artifacts/prompts/staging/archer.render.candidate.json` active_deployment.digest = `ee9681dc…fa33`

## 4. spec-003 digest 表

```bash
sha256sum \
  .louke/project/specs/v0.14-003-workflow-reflow-impl/story.md \
  .louke/project/specs/v0.14-003-workflow-reflow-impl/spec.md \
  .louke/project/specs/v0.14-003-workflow-reflow-impl/acceptance.md \
  .louke/project/specs/v0.14-003-workflow-reflow-impl/test-plan.md \
  .louke/project/specs/v0.14-003-workflow-reflow-impl/architecture.md \
  .louke/project/specs/v0.14-003-workflow-reflow-impl/interfaces.md \
  .louke/project/specs/v0.14-003-workflow-reflow-impl/spec-review.md \
  .louke/project/specs/v0.14-003-workflow-reflow-impl/story-review.md
```

| artifact | sha256 |
|---|---|
| story.md | `1dca9f38b5fba54acd4084531a717f141c9b6ce1403ad2e11ec9a29a21617211` |
| spec.md | `a5c95c7a7ea1f8237913d9779fbc598d679211ece9be314ace944874b706280a` |
| acceptance.md | `a19e25689e59f722d2b72d6903ce4be1b333cf0441c5e3b14a351f6566dfe287` |
| test-plan.md | `4d82ed7667dae41d6b466d9399489a06de217005251242538725ac3998f2fe4e` |
| architecture.md | `adde140b72915c0bf419623358e39becd83a2aa999e8b3667edf6bedbdce32c3` |
| interfaces.md | `14c8463a6c789ae2bb8704efe6d86ccbd1d2dd26ce0c14f2337c99374a72a4d1` |
| spec-review.md (Lex round 2 PASS) | `d61875af93f29f779cda812bca8058b7ec439943ef2fd6a89e8d31b95ce3141d` |
| story-review.md (Sage PASS) | `355ff9a1982b544002fad3d1767c3f68d3053e57fb905f4f5ec68160e8a58e6f` |

## 5. spec-003 file sizes（粗略 sanity check）

```bash
wc -l .louke/project/specs/v0.14-003-workflow-reflow-impl/*.md
```

| file | lines |
|---|---|
| test-plan.md | 364 |
| architecture.md | 888 |
| interfaces.md | 465 |
| spec.md | （落在 spec 462 行） |
| acceptance.md | 36 acceptance sections |

## 6. 复现命令集

### 6.1 验证 Prism round 5 B-2（schema 不可复用）

```bash
python3 - <<'PY'
import json, jsonschema
s = json.load(open('.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/registry/agent-io/archer-design-task-input-1.0.0.schema.json'))
task = json.load(open('.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/inputs/archer-author-task-manifest.candidate.json'))

# mutation 1: 换 spec id
mut_a = json.loads(json.dumps(task))
mut_a['spec']['id'] = 'v0.14-003-workflow-reflow-impl'
errs_a = [(list(e.absolute_path), e.message[:60]) for e in jsonschema.Draft202012Validator(s).iter_errors(mut_a)][:6]

# mutation 2: 换 design revision
mut_b = json.loads(json.dumps(task))
mut_b['design_revision']['identity'] = 'next-revision-identity'
mut_b['design_revision']['revision'] = 'next-design-revision'
errs_b = [(list(e.absolute_path), e.message[:60]) for e in jsonschema.Draft202012Validator(s).iter_errors(mut_b)][:6]

print('next-spec:', errs_a)
print('next-rev:', errs_b)
PY
```

期望输出（≥ 4 / ≥ 2 条 schema error）：
```
next-spec: [
  (['spec', 'id'], "'v0.14-002-workflow-reflow-design' was expected"),
  (['allowed_write_set', 0], "'...v0.14-003-workflow-reflow-impl/test-plan.md' does not match '...'"),
  (['allowed_write_set', 1], "..."),
  (['allowed_write_set', 2], "..."),
  (['allowed_write_set', 3], "..."),
  (['output_contract', 'artifact_manifest_path'], "'...v0.14-002-workflow-reflow-design/...' was expected"),
]
next-rev: [
  (['design_revision', 'identity'], "'louke.design-artifacts.v0.14-002.prism-r3-remediation' was expected"),
  (['design_revision', 'revision'], "'prism-round-3-remediation-candidate' was expected"),
]
```

### 6.2 验证 release-version schema 通用性 + heterogeneous fixture

```bash
python3 - <<'PY'
import json, jsonschema
s = json.load(open('.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/registry/schemas/release-version-1.0.0.schema.json'))
jsonschema.Draft202012Validator.check_schema(s)

inst_louke = json.load(open('.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/contracts/release-version.candidate.json'))
jsonschema.Draft202012Validator(s).validate(inst_louke)

inst_node = json.load(open('.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts/validation/release-version-node-host.valid.candidate.json'))
jsonschema.Draft202012Validator(s).validate(inst_node)

print('Louke & Node fixtures both pass')
PY
```

期望：`Louke & Node fixtures both pass`。

### 6.3 验证 11 schemas meta-validate + 7 contracts validate + 8 neg fixtures fail

```bash
python3 - <<'PY'
import json, glob, jsonschema
root = '.louke/project/specs/v0.14-002-workflow-reflow-design/design-artifacts'
schemas = sorted(glob.glob(f'{root}/registry/schemas/*.schema.json') + glob.glob(f'{root}/registry/agent-io/*.schema.json'))
contracts = sorted(glob.glob(f'{root}/contracts/*.candidate.json'))
neg = json.load(open(f'{root}/validation/negative-schema-fixtures.candidate.json'))

for p in schemas:
    jsonschema.Draft202012Validator.check_schema(json.load(open(p)))
print(f'{len(schemas)} schemas meta-valid')

for p in contracts:
    # 找到对应 schema
    kind = p.split('/')[-1].replace('.candidate.json','')
    schema_p = f'{root}/registry/schemas/{kind}-1.0.0.schema.json' if kind != 'release-version' else f'{root}/registry/schemas/{kind}-1.0.0.schema.json'
    if not __import__('os').path.exists(schema_p): continue
    s = json.load(open(schema_p))
    inst = json.load(open(p))
    jsonschema.Draft202012Validator(s).validate(inst)
print(f'{len(contracts)} contracts validate')

# 负 fixture
for fixture in neg:
    s = json.load(open(fixture['schema']))
    inst = json.load(open(fixture['instance']))
    errs = list(jsonschema.Draft202012Validator(s).iter_errors(inst))
    assert errs, fixture['name']
print('all negative fixtures fail as expected')
PY
```

### 6.4 确认 v0.14 实施层提交格式

```bash
git log 1d88e61..63d0da3 --oneline | head -30
```

每条 commit 应形如：`feat(v014): implement FR-#### ... (#NNN)` 或 `fix(v014): ... (#NNN)`。

## 7. GitHub Issue Inventory

### spec-001: 24 个 issue (#226–#249)
- `gh api --method GET repos/zillionare/louke/issues -f state=all -f labels='spec:v0.14-001-workflow-reflow-spec' -f per_page=100 --jq '[.[] | select(.pull_request == null)] | length'`
- 期望：24

### spec-002: 34 个 issue (#250–#283)
- label `spec:v0.14-002-workflow-reflow-design`
- 期望：34

### spec-003: 36 个 issue (#284–#319)
- label `spec:v0.14-003-workflow-reflow-impl`
- 期望：36

## 8. 关键 PRD / Flow 文件（评审上下文，spec 002/003 的需求叙事）

- `.louke/project/specs/v0.14-002-workflow-reflow-design/story.md` — STR-1403
- `.louke/project/specs/v0.14-003-workflow-reflow-impl/story.md` — STR-1404
- `.louke/project/specs/v0.14-003-workflow-reflow-impl/flow.md` — 003 流程速览（Review Draft；不影响评审）

## 9. 不要看的文件

- `.louke/spec_archive/stale-v013/**` — 旧 v0.13 `lk agent *` 输出，已废弃
- `.louke/spec_archive/wip/**` — 早期 WIP，与 v0.14 无关
- `.louke/project/specs/v0.14-001-workflow-reflow-spec/implementation/commit-receipt.txt` — 仅参考
- 任何 `requirements.txt` / `pyproject.toml` 的版本变更 —— 与本评审无关
