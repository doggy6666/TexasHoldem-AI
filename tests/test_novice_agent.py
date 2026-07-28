import json

import pytest

from agent.deepseek_client import DeepSeekError
from agent.novice_agent import (
    NOVICE_TENDENCIES,
    build_decision_context,
    choose_action,
    choose_decision,
    choose_novice_tendency,
    legal_actions_for,
    validate_decision,
)
from poker.cards import Card
from poker.game import PokerGame


class FakeClient:
    def __init__(self, decision=None, error=None):
        self.decision = decision
        self.error = error
        self.user_prompt = ""

    def complete_json(self, system_prompt, user_prompt):
        self.user_prompt = user_prompt
        if self.error:
            raise self.error
        return self.decision


def heads_up_ai_turn():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("call")
    assert game.turn_index == 1
    return game


def test_decision_context_never_contains_opponents_hole_cards_or_deck():
    game = heads_up_ai_turn()
    game.human.hole_cards = [Card(14, "♠"), Card(14, "♥")]
    game.players[1].hole_cards = [Card(2, "♣"), Card(7, "♦")]

    context = build_decision_context(game, 1)
    serialized = json.dumps(context, ensure_ascii=False)

    assert "A♠" not in serialized
    assert "A♥" not in serialized
    assert context["your_hole_cards"] == ["2♣", "7♦"]
    assert "hole_cards" not in context["opponents"][0]
    assert "deck" not in context


def test_novice_tendency_is_randomly_selected_with_weighted_choices(monkeypatch):
    captured = {}

    def fake_choices(population, weights, k):
        captured["weights"] = weights
        captured["k"] = k
        return [population[2]]

    monkeypatch.setattr("agent.novice_agent.random.choices", fake_choices)

    assert choose_novice_tendency() == NOVICE_TENDENCIES[2]
    assert captured == {"weights": (20, 30, 32, 18), "k": 1}


def test_legal_actions_match_current_betting_state():
    game = heads_up_ai_turn()
    legal = legal_actions_for(game, 1)

    assert "check" in legal["actions"]
    assert "call" not in legal["actions"]
    assert "raise" in legal["actions"]


def test_valid_deepseek_decision_is_used_without_reason_field():
    game = heads_up_ai_turn()
    client = FakeClient({"action": "check", "amount_to": 0})

    assert choose_decision(game, 1, client=client) == ("check", 0, "新手 AI")
    assert choose_action(game, 1, client=client) == ("check", 0)
    assert "reason" not in client.user_prompt


def test_invalid_deepseek_decision_uses_local_fallback(monkeypatch):
    game = heads_up_ai_turn()
    client = FakeClient({"action": "reveal_cards", "amount_to": 0})
    monkeypatch.setattr(
        "agent.novice_agent.choose_fallback_action",
        lambda current_game, player_index: ("check", 0),
    )

    assert choose_decision(game, 1, client=client) == (
        "check",
        0,
        "默认 AI 已接管",
    )


def test_deepseek_failure_uses_local_fallback(monkeypatch):
    game = heads_up_ai_turn()
    client = FakeClient(error=DeepSeekError("模拟超时"))
    monkeypatch.setattr(
        "agent.novice_agent.choose_fallback_action",
        lambda current_game, player_index: ("check", 0),
    )

    assert choose_decision(game, 1, client=client) == (
        "check",
        0,
        "默认 AI 已接管",
    )


def test_raise_amount_must_be_within_rules():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("raise", 40)
    assert game.turn_index == 1

    assert validate_decision({"action": "raise", "amount_to": 80}, game, 1) == (
        "raise",
        80,
    )
    with pytest.raises(ValueError):
        validate_decision({"action": "raise", "amount_to": 41}, game, 1)


def test_game_uses_injected_ai_provider_without_changing_default_contract():
    game = heads_up_ai_turn()
    called = []

    def provider(current_game, player_index):
        called.append(player_index)
        return "check", 0, "新手 AI"

    game.play_next_ai_turn(provider)

    assert called == [1]
    assert game.last_actions[1] == "过牌（check）"
    assert game.last_ai_sources[1] == "新手 AI"
    assert "决策来源" not in game.log[-1]
