"""第四阶段联网教练：仅在页面按钮被明确点击时调用 DeepSeek。"""

from __future__ import annotations

import json

from agent.decision_support import build_decision_context
from agent.deepseek_client import DeepSeekClient, DeepSeekError


class CoachError(RuntimeError):
    """策略提示或复盘无法生成。"""


TIP_SYSTEM_PROMPT = """你是德州扑克实时策略教练。
只能使用用户提供的牌局信息，不能假设或猜测对手隐藏手牌。
根据 legal_actions 给真人玩家一个可执行建议。
输出 JSON：
{
  "action": "fold/check/call/bet/raise/all_in",
  "amount_to": 整数或 null,
  "reason": "给玩家看的简短依据",
  "risk": "一句风险提醒"
}
不要输出隐藏思考过程，不要添加 JSON 以外的内容。"""

TIP_ACTION_LABELS = {
    "fold": "弃牌（fold）",
    "check": "过牌（check）",
    "call": "跟注（call）",
    "bet": "下注（bet）",
    "raise": "加注（raise）",
    "all_in": "全下（all in）",
}


REVIEW_SYSTEM_PROMPT = """你是德州扑克赛后复盘教练。
基于结构化牌局记录分析真人玩家的决策，不得虚构对手隐藏手牌。
输出 JSON：
{
  "summary": "本局总结",
  "strengths": ["做得好的地方"],
  "improvements": ["可以改进的地方"],
  "next_focus": "下一局训练重点"
}
建议必须对应记录中的具体行动，不要输出隐藏思考过程或 JSON 以外内容。"""


def decision_cache_key(game) -> str:
    parts = [
        str(game.hand_number),
        game.street_name,
        str(game.pot),
        str(game.current_bet),
        str(game.human.chips),
        ",".join(str(card) for card in game.human.hole_cards),
        ",".join(str(card) for card in game.community_cards),
        str(len(game.current_hand_record.get("actions", []))),
    ]
    return "|".join(parts)


def review_cache_key(game) -> str:
    return (
        f"{game.hand_number}|{game.result}|"
        f"{len(game.current_hand_record.get('actions', []))}"
    )


def build_tip_payload(game) -> dict:
    if game.status != "进行中" or not game.turn_is_human:
        raise CoachError("只有轮到你行动时才能获取实时策略提示。")
    context = build_decision_context(game, 0)
    context["structured_actions_this_hand"] = list(
        game.current_hand_record.get("actions", [])
    )
    return context


def build_review_payload(game) -> dict:
    record = game.current_hand_record
    if game.status != "已结束" or not record.get("completed"):
        raise CoachError("牌局结束后才能生成 AI 深度复盘。")
    return record


def generate_realtime_tip(game, client=None) -> dict:
    try:
        payload = build_tip_payload(game)
        active_client = client or DeepSeekClient.from_environment()
        result = active_client.complete_json(
            TIP_SYSTEM_PROMPT,
            "请分析以下当前决策：\n"
            + json.dumps(payload, ensure_ascii=False),
        )
        return _validate_tip(result, payload["legal_actions"])
    except DeepSeekError as error:
        raise CoachError(str(error)) from None


def generate_deep_review(game, client=None) -> dict:
    try:
        active_client = client or DeepSeekClient.from_environment()
        result = active_client.complete_json(
            REVIEW_SYSTEM_PROMPT,
            "请复盘以下结构化牌局记录：\n"
            + json.dumps(build_review_payload(game), ensure_ascii=False),
        )
        return _validate_review(result)
    except DeepSeekError as error:
        raise CoachError(str(error)) from None


def _validate_tip(result: dict, legal_actions: dict) -> dict:
    if not isinstance(result, dict):
        raise CoachError("实时策略提示格式错误。")
    required_text = ("action", "reason", "risk")
    if any(not isinstance(result.get(key), str) or not result[key].strip() for key in required_text):
        raise CoachError("实时策略提示缺少必要内容。")
    action = result["action"].strip()
    if action not in legal_actions["actions"]:
        raise CoachError("实时策略提示返回了当前不可执行的行动。")
    amount = result.get("amount_to")
    if action in {"bet", "raise"}:
        if isinstance(amount, bool) or not isinstance(amount, int):
            raise CoachError("实时策略提示的金额格式错误。")
        minimum = (
            legal_actions["minimum_bet_to"]
            if action == "bet"
            else legal_actions["minimum_raise_to"]
        )
        if not minimum <= amount <= legal_actions["maximum_to"]:
            raise CoachError("实时策略提示的金额超出合法范围。")
    else:
        amount = None
    return {
        "recommended_action": TIP_ACTION_LABELS[action],
        "amount_to": amount,
        "reason": result["reason"].strip(),
        "risk": result["risk"].strip(),
    }


def _validate_review(result: dict) -> dict:
    if not isinstance(result, dict):
        raise CoachError("AI 深度复盘格式错误。")
    if not isinstance(result.get("summary"), str) or not result["summary"].strip():
        raise CoachError("AI 深度复盘缺少总结。")
    if not isinstance(result.get("next_focus"), str) or not result["next_focus"].strip():
        raise CoachError("AI 深度复盘缺少训练重点。")
    for key in ("strengths", "improvements"):
        value = result.get(key)
        if not isinstance(value, list) or not value or not all(
            isinstance(item, str) and item.strip() for item in value
        ):
            raise CoachError("AI 深度复盘条目格式错误。")
    return {
        "summary": result["summary"].strip(),
        "strengths": [item.strip() for item in result["strengths"]],
        "improvements": [item.strip() for item in result["improvements"]],
        "next_focus": result["next_focus"].strip(),
    }
