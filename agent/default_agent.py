"""稳定、无需 LLM 的默认稳健型 AI。"""

from __future__ import annotations

import random


def choose_action(game, player_index: int) -> tuple[str, int]:
    player = game.players[player_index]
    required = game.amount_to_call(player_index)
    ranks = sorted((card.rank for card in player.hole_cards), reverse=True)
    strength = (ranks[0] + ranks[1]) / 28
    if ranks[0] == ranks[1]:
        strength += 0.22
    if game.community_cards:
        score, _ = game.best_score_for(player_index)
        strength = max(strength, score[0] / 8 + 0.22)
    strength = min(strength, 1.0)

    if required:
        if player.chips <= required:
            pot_odds = required / max(game.pot + required, 1)
            call_threshold = 0.78 if pot_odds >= 0.40 else 0.62
            made_hand_rank = game.best_score_for(player_index)[0][0] if game.community_cards else 0
            has_strong_made_hand = made_hand_rank >= 4
            has_value_hand_with_good_odds = made_hand_rank >= 2 and pot_odds <= 0.33
            should_call_all_in = (
                strength >= call_threshold
                or has_strong_made_hand
                or has_value_hand_with_good_odds
            )
            return ("all_in", 0) if should_call_all_in else ("fold", 0)
        if strength < 0.28 and random.random() < 0.75:
            return "fold", 0
        if strength > 0.86 and game.can_raise(player_index):
            return "raise", game.minimum_raise_to
        return "call", 0
    if game.current_bet > 0:
        if strength > 0.86 and game.can_raise(player_index):
            return "raise", game.minimum_raise_to
        return "check", 0
    if strength > 0.76 and player.chips >= game.big_blind:
        return "bet", min(game.big_blind * 2, player.street_bet + player.chips)
    if random.random() < 0.10 and player.chips >= game.big_blind:
        return "bet", game.big_blind
    return "check", 0
