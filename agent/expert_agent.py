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


def _preflop_strength(hole_cards: list[Card]) -> float:
    """将两张起手牌粗略映射为 0–1，供行动加权使用。"""
    high, low = sorted((card.rank for card in hole_cards), reverse=True)
    strength = (high + low - 4) / 24
    if high == low:
        strength = 0.5 + high / 28
    else:
        if hole_cards[0].suit == hole_cards[1].suit:
            strength += 0.08
        if high - low <= 1:
            strength += 0.05
        elif high - low >= 5:
            strength -= 0.05
    return max(0.05, min(1.0, strength))


def _sampled_hand_strength(
    hole_cards: list[Card],
    public_board: list[Card],
) -> float:
    if len(public_board) < 3:
        return _preflop_strength(hole_cards)
    score = best_hand(hole_cards + public_board)[0]
    category_strength = score[0] / 8
    high_card_strength = score[1] / 14 if len(score) > 1 else 0
    return max(
        0.05,
        min(1.0, category_strength * 0.88 + high_card_strength * 0.12),
    )


def _action_likelihood(
    action: str,
    hand_strength: float,
    pressure: float,
) -> float:
    """给公开行动分配柔和权重；所有牌始终保留非零可能性。"""
    if action == "check":
        return 1.05 - 0.2 * hand_strength
    if action == "call":
        return 0.65 + 0.75 * hand_strength
    if action == "bet":
        return 0.45 + (0.8 + 0.25 * pressure) * hand_strength
    if action == "raise":
        return 0.3 + (1.2 + 0.35 * pressure) * hand_strength
    if action == "all_in":
        return 0.2 + (1.5 + 0.4 * pressure) * hand_strength
    return 1.0


def _action_evidence(game, opponent_indices: list[int]) -> tuple[list[dict], float]:
    relevant_actions = [
        action
        for action in game.current_hand_record.get("actions", [])
        if action.get("seat") in opponent_indices
        and action.get("action") in {"check", "call", "bet", "raise", "all_in"}
    ]
    evidence_score = 0.0
    evidence_values = {
        "check": 0.05,
        "call": 0.15,
        "bet": 0.35,
        "raise": 0.5,
        "all_in": 0.65,
    }
    for action in relevant_actions:
        street_factor = (
            0.6
            if action.get("street") == "翻前圈（pre-flop）"
            else 1.0
        )
        evidence_score += evidence_values[action["action"]] * street_factor
    # 公开行动只作为辅助证据，最高影响 60%。
    confidence = min(0.6, evidence_score / (evidence_score + 2.0))
    return relevant_actions, confidence


def _sample_action_weight(
    game,
    sampled_holes: dict[int, list[Card]],
    relevant_actions: list[dict],
) -> float:
    weight = 1.0
    for action in relevant_actions:
        seat = action["seat"]
        board_count = len(action.get("community_cards", []))
        public_board = game.community_cards[:board_count]
        hand_strength = _sampled_hand_strength(
            sampled_holes[seat],
            public_board,
        )
        contribution = max(
            0,
            action.get("pot_after", 0) - action.get("pot_before", 0),
        )
        pressure = min(
            2.0,
            contribution / max(action.get("pot_before", 0), game.big_blind),
        )
        weight *= _action_likelihood(
            action["action"],
            hand_strength,
            pressure,
        )
    return max(0.15, min(6.0, weight))


def estimate_outcome_probabilities(
    game,
    player_index: int,
    samples: int = 96,
    rng=None,
) -> dict:
    """估算胜、平、负与权益；只抽样未知牌，不读取对手真实手牌。"""
    if samples <= 0:
        raise ValueError("抽样次数必须大于 0。")
    random_source = rng or random
    hero = game.players[player_index]
    known_cards = set(hero.hole_cards + game.community_cards)
    available = [
        Card(rank, suit)
        for suit in SUITS
        for rank in RANKS
        if Card(rank, suit) not in known_cards
    ]
    opponent_indices = [
        index
        for index, player in enumerate(game.players)
        if index != player_index and player.hole_cards and not player.folded
    ]
    opponent_count = len(opponent_indices)
    relevant_actions, action_confidence = _action_evidence(
        game,
        opponent_indices,
    )
    missing_board = 5 - len(game.community_cards)
    cards_needed = missing_board + opponent_count * 2
    if opponent_count == 0 or cards_needed > len(available):
        return {
            "win_probability": 1.0,
            "tie_probability": 0.0,
            "opponent_stronger_probability": 0.0,
            "estimated_equity": 1.0,
            "action_adjusted_win_probability": 1.0,
            "action_adjustment_confidence": 0.0,
            "action_evidence_count": 0,
            "samples": samples,
        }

    equity_total = 0.0
    weighted_wins = 0.0
    total_weight = 0.0
    wins = 0
    ties = 0
    losses = 0
    for _ in range(samples):
        drawn = random_source.sample(available, cards_needed)
        board = game.community_cards + drawn[:missing_board]
        cursor = missing_board
        hero_score = best_hand(hero.hole_cards + board)[0]
        opponent_scores = []
        sampled_holes = {}
        for opponent_index in opponent_indices:
            opponent_hole = drawn[cursor : cursor + 2]
            cursor += 2
            sampled_holes[opponent_index] = opponent_hole
            opponent_scores.append(best_hand(opponent_hole + board)[0])
        sample_weight = _sample_action_weight(
            game,
            sampled_holes,
            relevant_actions,
        )
        total_weight += sample_weight
        strongest_opponent = max(opponent_scores)
        if hero_score > strongest_opponent:
            wins += 1
            equity_total += 1
            weighted_wins += sample_weight
        elif hero_score == strongest_opponent:
            ties += 1
            tied_winners = 1 + sum(
                score == hero_score for score in opponent_scores
            )
            equity_total += 1 / tied_winners
        else:
            losses += 1
    base_win_probability = wins / samples
    weighted_win_probability = (
        weighted_wins / total_weight
        if total_weight
        else base_win_probability
    )
    action_adjusted = (
        base_win_probability
        + action_confidence
        * (weighted_win_probability - base_win_probability)
    )
    # 防止启发式行动模型压过基础牌面概率。
    action_adjusted = max(
        base_win_probability - 0.15,
        min(base_win_probability + 0.15, action_adjusted),
    )
    return {
        "win_probability": round(base_win_probability, 4),
        "tie_probability": round(ties / samples, 4),
        "opponent_stronger_probability": round(losses / samples, 4),
        "estimated_equity": round(equity_total / samples, 4),
        "action_adjusted_win_probability": round(action_adjusted, 4),
        "action_adjustment_confidence": round(action_confidence, 3),
        "action_evidence_count": len(relevant_actions),
        "samples": samples,
    }


def estimate_equity(game, player_index: int, samples: int = 96, rng=None) -> float:
    return estimate_outcome_probabilities(
        game,
        player_index,
        samples=samples,
        rng=rng,
    )["estimated_equity"]


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
