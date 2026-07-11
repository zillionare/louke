# sample spec for quote_parser tests
# demonstrates all FR-017 status markers and FR-024 nesting depth ≥ 3

## 功能需求

<a id="fr-001"></a>
**FR-001**: 示例功能 1

> **Sage:** 这是单层 quote，应被解析为 depth=1, status=open [open]
>> **Aaron:** 用户回复了，应被解析为 depth=2 [open]
>>> **Sage:** Sage 追问，应被解析为 depth=3 [open]
>>>> **Aaron:** 深度 4 用户回复 ✓ resolved

<a id="fr-002"></a>
**FR-002**: 示例功能 2

> **Sage:** 已闭环的 quote。 ✓ resolved
>> **Sage:** 后续追问。 ✓ resolved

<a id="fr-003"></a>
**FR-003**: 示例功能 3 (有阻塞)

> **Sage:** 这条被 FR-001 阻塞。 [blocked-by-001]

<a id="fr-004"></a>
**FR-004**: 示例功能 4

> **Sage:** wontfix 的 quote [wontfix]

<a id="fr-005"></a>
**FR-005**: 示例功能 5

> **Sage:** superseded 的 quote [superseded]

## 代码块中的 > 不应被解析为 quote

下面这个代码块包含 `>` 字符，不应被解析：

```
> **Sage:** 这是代码块内，**不是**真 quote [open]
> 普通注释行
```

## 引号嵌套

普通文本里出现 `>` 字符但不是 quote 起始（例如列表里）：

- 项目 A
- 项目 B
- 项目 C

以上都不应被解析为 quote。

## 单层多说话人

> **Sage:** 1st quote [open]
> **Lex:** 2nd quote in same depth [open]
> **Aaron:** 3rd quote [open]
