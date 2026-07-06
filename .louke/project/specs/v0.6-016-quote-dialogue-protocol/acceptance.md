# 验收报告 — v0.6-016 — Quote Dialogue Speaker-Tag 协议

## AC 覆盖

| FR/NFR | AC 数 | 覆盖范围 |
|---|---|---|
| FR-0010 (speaker-tag 正式语法) | 4 | parser 解析 / 嵌套 depth / 大小写 / lazy continuation |
| FR-0020 (三类 speaker-tag 语义) | 3 | 解析三类 / 隐藏草稿 / `[note]` vs speaker 区分 |
| FR-0030 (多轮协议) | 3 | commit per round / 不用纯文字 / 不擅自 ✅ |
| FR-0040 (12 agent 学习) | 3 | 12 文件含引用 / 不重复语法 / bats 测试 |
| FR-0050 (用户教程) | 3 | cookbook 段 / 3 example / 链接到本 spec |
| NFR-0010 (向后兼容) | 2 | 老 spec 走通 / parser exit 0 |
| NFR-0020 (草稿不入 git) | 2 | commit hook 拦截 / bats 验证 |
| NFR-0030 (文档语言) | - | 描述性, 不需单独 AC |

## 验收标准

(待 Sage 阶段填, 与本 spec 同步走 quote dialogue)
