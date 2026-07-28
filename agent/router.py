"""根据座位人格选择 AI 决策器。"""

from __future__ import annotations

from agent.advanced_agent import choose_decision as choose_advanced_decision
from agent.default_agent import choose_action as choose_fallback_action
from agent.expert_agent import choose_decision as choose_expert_decision
from agent.modes import (
    ADVANCED_AGGRESSIVE,
    ADVANCED_CONSERVATIVE,
    EXPERT,
    NOVICE,
    OFFLINE,
)
from agent.novice_agent import choose_decision as choose_novice_decision


def choose_persona_decision(game, player_index: int) -> tuple[str, int, str]:
    persona = getattr(game.players[player_index], "ai_persona", NOVICE)
    if persona == OFFLINE:
        action, amount = choose_fallback_action(game, player_index)
        return action, amount, "默认 AI 已接管"
    if persona == NOVICE:
        return choose_novice_decision(game, player_index)
    if persona == ADVANCED_CONSERVATIVE:
        return choose_advanced_decision(game, player_index, "conservative")
    if persona == ADVANCED_AGGRESSIVE:
        return choose_advanced_decision(game, player_index, "aggressive")
    if persona == EXPERT:
        return choose_expert_decision(game, player_index)
    action, amount = choose_fallback_action(game, player_index)
    return action, amount, "默认 AI 已接管"
