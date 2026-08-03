"""所有人格共用的公开牌局上下文、合法行动和决策校验。"""

from __future__ import annotations

from poker.hand import HAND_NAMES, best_hand, describe_score


def authoritative_public_facts(game, player_index: int) -> dict:
    """由本地规则生成，不让 LLM 自行猜测花色或盲注含义。"""
    player = game.players[player_index]
    hole_cards = player.hole_cards
    same_suit = (
        len(hole_cards) == 2
        and hole_cards[0].suit == hole_cards[1].suit
    )
    paired = (
        len(hole_cards) == 2
        and hole_cards[0].rank == hole_cards[1].rank
    )
    available_cards = list(hole_cards) + list(game.community_cards)
    current_best_hand = None
    current_hand_category = None
    current_hand_score = None
    if len(available_cards) >= 5:
        score, _ = best_hand(available_cards)
        current_best_hand = describe_score(score)
        current_hand_category = HAND_NAMES[score[0]].split("（", 1)[0]
        current_hand_score = list(score)
    voluntary_actions = list(
        game.current_hand_record.get("actions", [])
    )
    opponent_aggressive_actions = [
        {
            "seat": action["seat"],
            "player_name": action["player_name"],
            "street": action["street"],
            "action": action["action"],
            "action_text": action["action_text"],
        }
        for action in voluntary_actions
        if action.get("seat") != player_index
        and action.get("action") in {"bet", "raise", "all_in"}
    ]
    return {
        "your_hole_cards": [str(card) for card in hole_cards],
        "your_two_cards_same_suit": same_suit,
        "your_two_cards_are_pair": paired,
        "your_current_best_hand": current_best_hand,
        "your_current_hand_category": current_hand_category,
        "your_current_hand_score": current_hand_score,
        "current_hand_rule": (
            "当前最佳牌型由本地德州扑克牌型引擎从你的两张手牌和已发公共牌中精确计算；"
            "不得把未成对的单张起手牌当作对子。"
        ),
        "blind_posts": {
            "small_blind_seat": game.small_blind_index,
            "small_blind_amount": game.small_blind,
            "big_blind_seat": game.big_blind_index,
            "big_blind_amount": game.big_blind,
            "rule": "盲注是强制投入，不属于下注、加注或玩家主动行动。",
        },
        "opponent_voluntary_aggressive_actions": (
            opponent_aggressive_actions
        ),
        "opponent_voluntary_aggression_count": len(
            opponent_aggressive_actions
        ),
    }


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
    voluntary_actions = list(
        game.current_hand_record.get("actions", [])
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
        "recent_public_actions": [
            {
                "street": action["street"],
                "seat": action["seat"],
                "player_name": action["player_name"],
                "action": action["action"],
                "action_text": action["action_text"],
            }
            for action in voluntary_actions[-16:]
        ],
        "authoritative_facts": authoritative_public_facts(
            game,
            player_index,
        ),
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
