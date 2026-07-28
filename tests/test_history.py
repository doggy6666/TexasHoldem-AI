import json

from agent.training import build_training_summary
from poker.cards import Card
from poker.game import PokerGame
from poker.history import record_for_display


def test_structured_record_captures_decision_state_without_opponent_hidden_cards():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human.hole_cards = [Card(14, "♠"), Card(13, "♠")]
    game.players[1].hole_cards = [Card(2, "♣"), Card(3, "♦")]

    game.human_action("call")
    record = game.current_hand_record
    serialized = json.dumps(record_for_display(record), ensure_ascii=False)

    assert record["human_hole_cards"]
    assert len(record["actions"]) == 1
    action = record["actions"][0]
    assert action["seat"] == 0
    assert action["action"] == "call"
    assert action["pot_before"] == 30
    assert action["amount_to_call_before"] == 10
    assert "2♣" not in serialized
    assert "3♦" not in serialized
    assert "deck" not in serialized


def test_completed_records_are_archived_across_continuous_hands():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("fold")

    assert game.current_hand_record["completed"] is True
    assert len(game.completed_hand_records) == 1
    assert game.completed_hand_records[0]["result"] == game.result

    game.start_hand()

    assert game.current_hand_record["hand_number"] == 2
    assert game.current_hand_record["completed"] is False
    assert len(game.completed_hand_records) == 1


def test_training_summary_reports_behavior_without_strategy_advice():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("fold")

    summary = build_training_summary(game.completed_hand_records)

    assert summary["hands"] == 1
    assert summary["chip_change"] == -10
    assert summary["total_decisions"] == 1
    assert summary["action_counts"]["弃牌"] == 1
    assert summary["observations"]
