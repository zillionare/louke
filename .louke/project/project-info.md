# Project Info

## v0.1 (已完成基础设施)
- **Story**: 一个以 TDD 为核心，以双人评审为质量门禁，以 Github project/issues 为流程管理工具的多 Agent 开发流程，并且实现自举
- **Version**: 0.1
- **Repo**: github.com/zillionare/specforge
- **Project**: specforge-0.1 (#3)
- **Spec ID**: v0.1-001-specforge
- **Test Issue**: #12 (closed)
- **Test PR**: #13 (open — Sage spec discussion, 间接验证)
- **Created**: 2026-05-23

## v0.2 (当前活跃)
- **Story**: 在 specforge init 时，提示用户输入可用模型，自动为各 Agent 分配 model，第一版默认支持 OpenCode
- **Version**: 0.2
- **Repo**: github.com/zillionare/specforge
- **Project**: specforge-v0.2 (#4)
- **Spec ID**: v0.2-002-specforge
- **Test Issue**: #15 (closed)
- **Test PR**: #16 (closed)
- **Created**: 2026-06-02

## v0.4 (实战测试)
- **Story**: 通过 markdown quote 语法完成 spec 澄清，免去 PR 流程；sage 用 > 提问、用户用 >> 回答，按 > 个数缩进。
- **Version**: 0.4
- **Repo**: github.com/zillionare/specforge
- **Project**: specforge-v0.4 (#7) [owner: quantclaws]
- **Spec ID**: v0.4-004-quote-dialogue
- **Release Branch**: `releases/v0.4`
- **Created**: 2026-06-15

## v0.7 (已完成)
- **Story**: pre-commit 接管 lint/format/typecheck/test + R-G-R Red 去 commit + Keeper 瘦到 R-G-R/format/AC trace/反模式。详见 `.louke/project/specs/v0.7-001-pre-commit-quality-gates/spec.md`。
- **Version**: 0.7
- **Repo**: github.com/zillionare/louke
- **Project**: louke-v0.7 (#8)
- **Project ID**: https://github.com/users/quantclaws/projects/8
- **Spec ID**: v0.7-001-pre-commit-quality-gates
- **Release Branch**: `releases/v0.7` (待建)
- **Smoke Test Issue**: #80 (closed, previous v0.6 milestone 冒烟)
- **unittest**: bats (bash testing — v0.6 既有 20 份 .bats；本 v0.7 spec 新增/更新 5 份 bats；FR-0700 dogfood `pre-commit run --all-files` step 旁安装在 ci.yml，独立于 bats)
- **Spec Stage**: Archer 阶段一 + 阶段二 已完成 (test-plan + architecture + interfaces)
- **DoD**: e2e 全通过 + 单元测试覆盖率 ≥95%（AC 引用闭合 58/58；未启用 Security Audit 因本项目为内部工具）
- **Security Audit**: disabled
- **Created**: 2026-07-05
- **Closed**: 2026-07-05
- **Tag**: v0.7.0 (zillionare/louke@v0.7.0)
- **Implementation**: 12 commits (含 keeper R-G-R bug fix `11cd56a`); 50/50 spec bats 全绿 (含 NFR-0010/FR-0200/FR-0400/FR-0500/FR-0600/FR-0700/NFR-0020/NFR-0030 + keeper fix 4 项); keeper gate `lk keeper gate --commit-range HEAD~10..HEAD` exit 0 / 0 blocker
- **Related Issues** (本 spec 已建): #81 FR-0100, #82 FR-0200, #83 FR-0300, #84 FR-0400, #85 FR-0500, #86 FR-0600, #87 FR-0700, #88 NFR-0010, #89 NFR-0020, #90 NFR-0030
- **Known carryover** (非阻塞):
  - louke 工作树里有 ~70 个 pre-existing dirty 文件 (agents/ 目录迁移、Makefile 删除等), 跟本 spec 无关, 不影响 tag
  - Project `louke-v0.7` (#8) owner 是 quantclaws (gh auth 限制), zillionare 已加 ADMIN; 不影响使用
  - `lk agent devon commit-rgr` 当前版本要求 `--task-id` 参数, 后续 v0.7+ 应去掉以保持 R-G-R commit 格式干净
