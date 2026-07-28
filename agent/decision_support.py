"""所有人格共用的公开牌局上下文、合法行动和决策校验。"""

from __future__ import annotations


def legal_actions_for(game, player_index: int) -> dict:
    player = game.players[player_index]
    required = game.amount_to_call(player_index)
    maximum = player.street_bet + player.chips
    actions = ["fold"]

    if required == 0:
        actions.append("check")
        if game.current_bet == 0 and maximum >= game.big_blind:
            actions.append("bet")
        elif game.current_bet > 0 and game.can_raise(player_index):
            actions.append("raise")
    elif player.chips >= required:
        actions.append("call")
        if game.can_raise(player_index):
            actions.append("raise")
    if player.chips > 0:
        actions.append("all_in")

    return {
        "actions": actions,
        "amount_to_call": required,
        "current_bet": game.current_bet,
        "minimum_bet_to": game.big_blind,
        "minimum_raise_to": game.minimum_raise_to,
        "maximum_to": maximum,
    }


def build_decision_context(
    game,
    player_index: int,
    behavior_hint: str | None = None,
    strategy_metrics: dict | None = None,
) -> dict:
    """只包含该 AI 的私有信息和其他玩家的公开信息。"""
    player = game.players[player_index]
    opponents = []
    for index, opponent in enumerate(game.players):
        if index == player_index:
            continue
        opponents.append(
            {
                "name": opponent.name,
                "seat": index,
                "chips": opponent.chips,
                "street_bet": opponent.street_bet,
                "hand_contribution": opponent.hand_contribution,
                "folded": opponent.folded,
                "all_in": opponent.all_in,
            }
        )
    context = {
        "street": game.street_name,
        "dealer_seat": game.dealer_index,
        "your_seat": player_index,
        "your_hole_cards": [str(card) for card in player.hole_cards],
        "community_cards": [str(card) for card in game.community_cards],
        "pot": game.pot,
        "your_chips": player.chips,
        "your_street_bet": player.street_bet,
        "your_hand_contribution": player.hand_contribution,
        "opponents": opponents,
        "recent_public_actions": game.log[-16:],
        "legal_actions": legal_actions_for(game, player_index),
    }
    if behavior_hint:
        context["behavior_hint_this_turn"] = behavior_hint
    if strategy_metrics:
        context["strategy_metrics"] = strategy_metrics
    return context


def validate_decision(decision: dict, game, player_index: int) -> tuple[str, int]:
    legal = legal_actions_for(game, player_index)
    action = decision.get("action")
    if action not in legal["actions"]:
        raise ValueError("AI 返回了非法行动。")

    if action in {"fold", "check", "call", "all_in"}:
        return action, 0

    amount = decision.get("amount_to")
    if isinstance(amount, bool) or not isinstance(amount, int):
        raise ValueError("AI 下注金额不是整数。")
    minimum = legal["minimum_bet_to"] if action == "bet" else legal["minimum_raise_to"]
    if not minimum <= amount <= legal["maximum_to"]:
        raise ValueError("AI 下注金额超出合法范围。")
    return action, amount
