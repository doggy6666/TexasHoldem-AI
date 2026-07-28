"""结构化牌局记录；只保存复盘所需信息，不记录对手未公开手牌。"""

from __future__ import annotations

from copy import deepcopy


def start_hand_record(game, starting_chips: dict[int, int]) -> dict:
    return {
        "hand_number": game.hand_number,
        "dealer_seat": game.dealer_index,
        "small_blind_seat": game.small_blind_index,
        "big_blind_seat": game.big_blind_index,
        "starting_chips": starting_chips,
        "human_hole_cards": [str(card) for card in game.human.hole_cards],
        "actions": [],
        "final_community_cards": [],
        "showdown": [],
        "ending_chips": {},
        "result": None,
        "completed": False,
    }


def capture_action_before(game, player_index: int, action: str, amount: int) -> dict:
    player = game.players[player_index]
    return {
        "sequence": len(game.current_hand_record.get("actions", [])) + 1,
        "street": game.street_name,
        "seat": player_index,
        "player_name": player.name,
        "action": action,
        "requested_amount_to": amount if action in {"bet", "raise"} else None,
        "pot_before": game.pot,
        "current_bet_before": game.current_bet,
        "amount_to_call_before": game.amount_to_call(player_index),
        "chips_before": player.chips,
        "street_bet_before": player.street_bet,
        "community_cards": [str(card) for card in game.community_cards],
        "opponents_public_state": [
            {
                "seat": index,
                "name": opponent.name,
                "chips": opponent.chips,
                "street_bet": opponent.street_bet,
                "folded": opponent.folded,
                "all_in": opponent.all_in,
            }
            for index, opponent in enumerate(game.players)
            if index != player_index
        ],
    }


def complete_action_record(game, player_index: int, record: dict) -> None:
    player = game.players[player_index]
    record.update(
        {
            "action_text": game.last_actions[player_index],
            "pot_after": game.pot,
            "current_bet_after": game.current_bet,
            "chips_after": player.chips,
            "street_bet_after": player.street_bet,
        }
    )
    game.current_hand_record["actions"].append(record)


def finalize_hand_record(game) -> None:
    record = game.current_hand_record
    if not record or record.get("completed"):
        return
    record.update(
        {
            "final_community_cards": [
                str(card) for card in game.community_cards
            ],
            "showdown": list(game.showdown_details),
            "ending_chips": {
                index: player.chips
                for index, player in enumerate(game.players)
            },
            "result": game.result,
            "completed": True,
        }
    )
    game.completed_hand_records.append(deepcopy(record))


def record_for_display(record: dict) -> dict:
    """返回适合玩家查看的副本；记录本身从不包含对手未公开手牌。"""
    return deepcopy(record)
