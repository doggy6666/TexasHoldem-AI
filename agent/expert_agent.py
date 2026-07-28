"""结合胜率抽样和博弈论指标的 GTO 启发式高手 AI。"""

from __future__ import annotations

import json
import random

from agent.decision_support import (
    build_decision_context,
    legal_actions_for,
    validate_decision,
)
from agent.deepseek_client import DeepSeekClient, DeepSeekError
from agent.default_agent import choose_action as choose_fallback_action
from poker.cards import Card, RANKS, SUITS
from poker.hand import best_hand


SYSTEM_PROMPT = """你是德州扑克高手 AI，采用 GTO 启发式决策。
严格从 legal_actions 中选择行动，并结合 strategy_metrics 中的蒙特卡洛胜率、
底池赔率、SPR、最小防守频率、位置、对手数量和建议下注尺度。
使用混合策略：相似局面可以按 mixed_strategy_roll 在过牌、跟注、下注、加注间分配频率；
价值下注与诈唬需要保持合理比例，多人底池减少纯诈唬，短 SPR 时适当扩大价值全下范围。
amount_to 必须从合法范围或 suggested_bet_sizes_to 中选择。
不要解释原因，不输出隐藏思考，只输出 JSON：
{"action":"fold/check/call/bet/raise/all_in","amount_to":整数}。"""


def estimate_equity(game, player_index: int, samples: int = 96, rng=None) -> float:
    """只用己方牌和公共牌抽样未知牌，不读取对手真实手牌。"""
    random_source = rng or random
    hero = game.players[player_index]
    known_cards = set(hero.hole_cards + game.community_cards)
    available = [
        Card(rank, suit)
        for suit in SUITS
        for rank in RANKS
        if Card(rank, suit) not in known_cards
    ]
    opponent_count = sum(
        1
        for index, player in enumerate(game.players)
        if index != player_index and player.hole_cards and not player.folded
    )
    missing_board = 5 - len(game.community_cards)
    cards_needed = missing_board + opponent_count * 2
    if opponent_count == 0 or cards_needed > len(available):
        return 1.0

    equity_total = 0.0
    for _ in range(samples):
        drawn = random_source.sample(available, cards_needed)
        board = game.community_cards + drawn[:missing_board]
        cursor = missing_board
        hero_score = best_hand(hero.hole_cards + board)[0]
        opponent_scores = []
        for _ in range(opponent_count):
            opponent_hole = drawn[cursor : cursor + 2]
            cursor += 2
            opponent_scores.append(best_hand(opponent_hole + board)[0])
        best_score = max([hero_score, *opponent_scores])
        if hero_score == best_score:
            tied_winners = 1 + sum(score == hero_score for score in opponent_scores)
            equity_total += 1 / tied_winners
    return round(equity_total / samples, 3)


def _position_name(game, player_index: int) -> str:
    if player_index == game.dealer_index:
        return "dealer"
    distance_after_dealer = (player_index - game.dealer_index) % len(game.players)
    return "early" if distance_after_dealer <= len(game.players) // 2 else "late"


def _suggested_bet_sizes(game, player_index: int) -> list[int]:
    legal = legal_actions_for(game, player_index)
    if not ({"bet", "raise"} & set(legal["actions"])):
        return []
    minimum = (
        legal["minimum_bet_to"]
        if "bet" in legal["actions"]
        else legal["minimum_raise_to"]
    )
    maximum = legal["maximum_to"]
    base = game.players[player_index].street_bet if "bet" in legal["actions"] else game.current_bet
    sizes = {minimum}
    for fraction in (0.33, 0.5, 0.75, 1.0):
        increment = max(game.big_blind, round(game.pot * fraction / game.big_blind) * game.big_blind)
        sizes.add(max(minimum, min(maximum, base + increment)))
    return sorted(size for size in sizes if minimum <= size <= maximum)


def build_strategy_metrics(game, player_index: int, samples: int = 96, rng=None) -> dict:
    player = game.players[player_index]
    required = game.amount_to_call(player_index)
    live_opponent_stacks = [
        opponent.chips
        for index, opponent in enumerate(game.players)
        if index != player_index and opponent.hole_cards and not opponent.folded
    ]
    effective_stack = min(
        player.chips,
        max(live_opponent_stacks, default=player.chips),
    )
    pot_odds = required / max(game.pot + required, 1) if required else 0.0
    minimum_defense_frequency = game.pot / max(game.pot + required, 1) if required else 1.0
    random_source = rng or random
    return {
        "estimated_equity": estimate_equity(game, player_index, samples=samples, rng=random_source),
        "pot_odds": round(pot_odds, 3),
        "stack_to_pot_ratio": round(effective_stack / max(game.pot, 1), 2),
        "minimum_defense_frequency": round(minimum_defense_frequency, 3),
        "position": _position_name(game, player_index),
        "live_opponents": len(live_opponent_stacks),
        "suggested_bet_sizes_to": _suggested_bet_sizes(game, player_index),
        "mixed_strategy_roll": round(random_source.random(), 3),
    }


def choose_decision(game, player_index: int, client=None) -> tuple[str, int, str]:
    try:
        metrics = build_strategy_metrics(game, player_index)
        context = build_decision_context(
            game,
            player_index,
            strategy_metrics=metrics,
        )
        active_client = client or DeepSeekClient.from_environment()
        raw_decision = active_client.complete_json(
            SYSTEM_PROMPT,
            "请根据以下 JSON 牌局状态作出行动：\n"
            + json.dumps(context, ensure_ascii=False),
        )
        action, amount = validate_decision(raw_decision, game, player_index)
        return action, amount, "高手 AI"
    except (DeepSeekError, ValueError, TypeError, KeyError):
        action, amount = choose_fallback_action(game, player_index)
        return action, amount, "默认 AI 已接管"
