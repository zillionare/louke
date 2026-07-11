"""FR-0201: 用户指令意图分类与路由. 纯规则/关键词分类, 不用 LLM, 不真触发 Backlog/Maestro."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse


# Intent 关键词正则 (中英文, 用 search 匹配, 命中数驱动 confidence)
_STORY_PATTERNS = [
    r"新做", r"做个", r"开发", r"做一个", r"实现", r"加个", r"增加",
    r"build", r"create", r"implement", r"develop",
]
_SPEC_PATTERNS = [
    r"改\s*spec", r"修改\s*spec", r"改一下", r"spec\s*改", r"acceptance\s*改",
    r"改\s*AC", r"spec\s*变", r"update\s*spec", r"revise\s*spec", r"change\s*spec",
]
_BUG_PATTERNS = [
    r"修.*bug", r"fix", r"修复", r"报错", r"异常", r"挂了", r"崩了",
    r"broken", r"crash", r"修一下", r"出错了",
]

_CLARIFY_QUESTION = "请问您想做: 新功能 / 改 spec / 修 bug?"
_STORY_CLARIFY_QUESTION = "请问您想立即进入开发, 还是先存入 backlog?"


@dataclass
class IntentRouteResult:
    """意图路由结果。executed 永远 False (本期不真执行), execution_id 永远 None。"""
    intent: str  # "story" | "spec_change" | "bug_fix" | "unknown"
    confidence: float
    proposed_action: str  # "choose_story_destination" | "spec_change" | "fix" | "clarify" | "start_development" | "save_backlog"
    requires_confirmation: bool
    clarification_question: str | None = None
    executed: bool = False
    execution_id: str | None = None


def classify(input_str: str) -> IntentRouteResult:
    """Pure function: classify the user input into an IntentRouteResult.

    Args:
        input_str: 原始用户输入。

    Returns:
        IntentRouteResult: executed 永远 False, 不触发任何副作用。
    """
    if not input_str or not input_str.strip():
        return IntentRouteResult(
            intent="unknown", confidence=0.0, proposed_action="clarify",
            requires_confirmation=True, clarification_question=_CLARIFY_QUESTION,
            executed=False,
        )
    s = input_str.lower()
    story_hits = sum(1 for p in _STORY_PATTERNS if re.search(p, s))
    spec_hits = sum(1 for p in _SPEC_PATTERNS if re.search(p, s))
    bug_hits = sum(1 for p in _BUG_PATTERNS if re.search(p, s))

    if spec_hits > 0 and spec_hits >= max(story_hits, bug_hits):
        return IntentRouteResult(
            intent="spec_change", confidence=min(0.95, 0.6 + spec_hits * 0.15),
            proposed_action="spec_change", requires_confirmation=True,
            executed=False,
        )
    if bug_hits > 0 and bug_hits >= max(story_hits, spec_hits):
        return IntentRouteResult(
            intent="bug_fix", confidence=min(0.95, 0.6 + bug_hits * 0.15),
            proposed_action="fix", requires_confirmation=True, executed=False,
        )
    if story_hits > 0:
        return IntentRouteResult(
            intent="story", confidence=min(0.95, 0.6 + story_hits * 0.15),
            proposed_action="choose_story_destination", requires_confirmation=True,
            clarification_question=_STORY_CLARIFY_QUESTION, executed=False,
        )
    return IntentRouteResult(
        intent="unknown", confidence=0.0, proposed_action="clarify",
        requires_confirmation=True, clarification_question=_CLARIFY_QUESTION,
        executed=False,
    )


async def route_intent(request: Request) -> JSONResponse:
    """POST /api/intent/route: 分类用户输入并返回拟执行动作。

    Args:
        request: Starlette Request, body 为 JSON, 含 {input, selection?, confirmation?}。

    Returns:
        JSONResponse: 200 IntentRouteResult; 400 VALIDATION_ERROR (input 缺失/空)。
    """
    body = await request.json()
    input_str = body.get("input", "")
    selection = body.get("selection")
    confirmation = body.get("confirmation", False)

    if not isinstance(input_str, str) or not input_str.strip():
        return JSONResponse(
            {"error_code": "VALIDATION_ERROR", "message": "input is required"},
            status_code=400,
        )

    result = classify(input_str)

    # story 输入 + selection: 收敛 proposed_action, 清掉澄清问题
    if result.intent == "story" and selection in ("start_development", "save_backlog"):
        result.clarification_question = None
        result.proposed_action = selection

    # confirmation=True 且 intent 可执行: 不再需要二次确认, 但本期仍不真执行
    if confirmation and result.intent in ("story", "spec_change", "bug_fix"):
        result.requires_confirmation = False

    return JSONResponse(asdict(result))


app = Starlette()
app.add_route("/api/intent/route", route_intent, methods=["POST"])
