"""进阶 AI：内部使用保守或激进策略，页面统一显示为进阶 AI。"""

from __future__ import annotations

import json
import random

from agent.decision_support import build_decision_context, validate_decision
from agent.deepseek_client import DeepSeekClient, DeepSeekError
from agent.default_agent import choose_action as choose_fallback_action


CONSERVATIVE_PROMPT = """你是德州扑克进阶 AI，内部采用保守策略。
严格从 legal_actions 选择行动；重视位置、跟注成本、底池和有效筹码。
弱牌面对下注时倾向弃牌，中等牌控制底池，强牌应主动价值下注或加注，
不能因为保守而总是过牌，也不要轻易用边缘牌跟随全下。
不要解释原因，不输出隐藏思考，只输出 JSON：
{"action":"fold/check/call/bet/raise/all_in","amount_to":整数}。"""

AGGRESSIVE_PROMPT = """你是德州扑克进阶 AI，内部采用激进策略。
严格从 legal_actions 选择行动；利用位置和筹码主动下注、加注与施压，
可以用听牌半诈唬并偶尔使用小额纯诈唬，但不能无脑全下或每次都加注。
面对明显强势行动时仍应合理弃牌，强牌优先做价值下注。
不要解释原因，不输出隐藏思考，只输出 JSON：
{"action":"fold/check/call/bet/raise/all_in","amount_to":整数}。"""

TENDENCIES = {
    "conservative": (
        "本回合更重视控制底池。",
        "本回合强牌可以主动获取价值。",
        "本回合面对大额下注提高弃牌倾向。",
    ),
    "aggressive": (
        "本回合更愿意使用小额持续下注。",
        "本回合可以在合法范围内提高加注频率。",
        "本回合保留一次半诈唬可能，但避免轻率全下。",
    ),
}


def choose_decision(
    game,
    player_index: int,
    style: str,
    client=None,
) -> tuple[str, int, str]:
    if style not in TENDENCIES:
        raise ValueError(f"未知进阶 AI 内部策略：{style}")
    prompt = CONSERVATIVE_PROMPT if style == "conservative" else AGGRESSIVE_PROMPT
    try:
        context = build_decision_context(
            game,
            player_index,
            behavior_hint=random.choice(TENDENCIES[style]),
        )
        active_client = client or DeepSeekClient.from_environment()
        raw_decision = active_client.complete_json(
            prompt,
            "请根据以下 JSON 牌局状态作出行动：\n"
            + json.dumps(context, ensure_ascii=False),
        )
        action, amount = validate_decision(raw_decision, game, player_index)
        return action, amount, "进阶 AI"
    except (DeepSeekError, ValueError, TypeError, KeyError):
        action, amount = choose_fallback_action(game, player_index)
        return action, amount, "默认 AI 已接管"
