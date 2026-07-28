"""DeepSeek 驱动的新手 AI；任何异常或非法决策都会回退到本地规则 AI。"""

from __future__ import annotations

import json
import random

from agent.decision_support import (
    build_decision_context as build_public_context,
    legal_actions_for,
    validate_decision,
)
from agent.deepseek_client import DeepSeekClient, DeepSeekError
from agent.default_agent import choose_action as choose_fallback_action


SYSTEM_PROMPT = """你是德州扑克游戏中的新手 AI。
你只能根据用户提供的 JSON 牌局状态，从 legal_actions 中选择一个合法行动。
你的水平是新手：偏爱跟注、会高估部分普通对子和高牌，偶尔会做出不够理想但合理的选择，
但不能无脑跟随全下。为了让牌局有互动，不要总是过牌：
- 无需跟注且允许 bet 时，普通可玩牌也可以做接近最小额度的小额试探下注；
- 翻前拿到对子、两张较大的牌或同花连张时，可以偶尔 raise；
- 翻牌后拿到对子、听顺或听同花时，可以更积极地 bet；
- 仍应保留过牌和弃牌，避免频繁全下或连续大额诈唬。
不要解释原因，不要输出隐藏思考。
只输出 JSON，例如 {"action":"call","amount_to":0}。
action 只能是 fold、check、call、bet、raise、all_in。"""

NOVICE_TENDENCIES = (
    "本回合稍微谨慎，弱牌更愿意放弃。",
    "本回合更想跟注看下一张牌。",
    "本回合更愿意做接近最小额度的试探下注。",
    "本回合可以偶尔尝试一次合法的小额加注。",
)


def choose_novice_tendency() -> str:
    return random.choices(NOVICE_TENDENCIES, weights=(20, 30, 32, 18), k=1)[0]


def build_decision_context(game, player_index: int) -> dict:
    return build_public_context(
        game,
        player_index,
        behavior_hint=choose_novice_tendency(),
    )


def choose_decision(game, player_index: int, client=None) -> tuple[str, int, str]:
    """返回行动及可公开的决策来源，不包含行动原因。"""
    try:
        active_client = client or DeepSeekClient.from_environment()
        context = build_decision_context(game, player_index)
        decision = active_client.complete_json(
            SYSTEM_PROMPT,
            "请根据以下 JSON 牌局状态作出行动：\n"
            + json.dumps(context, ensure_ascii=False),
        )
        action, amount = validate_decision(decision, game, player_index)
        return action, amount, "新手 AI"
    except (DeepSeekError, ValueError, TypeError, KeyError):
        action, amount = choose_fallback_action(game, player_index)
        return action, amount, "默认 AI 已接管"


def choose_action(game, player_index: int, client=None) -> tuple[str, int]:
    """兼容原有二元行动接口。"""
    action, amount, _ = choose_decision(game, player_index, client=client)
    return action, amount
