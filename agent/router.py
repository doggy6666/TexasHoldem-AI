"""根据座位人格选择 AI 决策器。"""

from __future__ import annotations

from copy import deepcopy
from queue import Empty, Queue
from threading import Thread
from typing import Callable, cast

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

AI_DECISION_TIMEOUT_SECONDS = 5.0
DecisionFunction = Callable[[object, int], tuple[str, int, str]]


def _fallback_decision(game, player_index: int) -> tuple[str, int, str]:
    action, amount = choose_fallback_action(game, player_index)
    return action, amount, "默认 AI 已接管"


def _decision_with_timeout(
    decision_function: DecisionFunction,
    game,
    player_index: int,
) -> tuple[str, int, str]:
    """联网 AI 最多思考五秒，迟到结果不会再影响真实牌局。"""
    result_queue: Queue[tuple[str, object]] = Queue(maxsize=1)
    game_snapshot = deepcopy(game)

    def run_decision() -> None:
        try:
            result_queue.put(
                (
                    "ok",
                    decision_function(game_snapshot, player_index),
                )
            )
        except Exception as error:
            result_queue.put(("error", error))

    Thread(
        target=run_decision,
        daemon=True,
        name=f"poker-ai-seat-{player_index}",
    ).start()

    try:
        status, payload = result_queue.get(
            timeout=AI_DECISION_TIMEOUT_SECONDS
        )
    except Empty:
        return _fallback_decision(game, player_index)

    if status != "ok":
        return _fallback_decision(game, player_index)
    return cast(tuple[str, int, str], payload)


def choose_persona_decision(game, player_index: int) -> tuple[str, int, str]:
    persona = getattr(game.players[player_index], "ai_persona", NOVICE)
    if persona == OFFLINE:
        return _fallback_decision(game, player_index)
    if persona == NOVICE:
        return _decision_with_timeout(
            choose_novice_decision,
            game,
            player_index,
        )
    if persona == ADVANCED_CONSERVATIVE:
        return _decision_with_timeout(
            lambda snapshot, index: choose_advanced_decision(
                snapshot,
                index,
                "conservative",
            ),
            game,
            player_index,
        )
    if persona == ADVANCED_AGGRESSIVE:
        return _decision_with_timeout(
            lambda snapshot, index: choose_advanced_decision(
                snapshot,
                index,
                "aggressive",
            ),
            game,
            player_index,
        )
    if persona == EXPERT:
        return _decision_with_timeout(
            choose_expert_decision,
            game,
            player_index,
        )
    return _fallback_decision(game, player_index)
