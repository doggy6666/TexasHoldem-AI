import random

from agent.deepseek_client import DeepSeekError
from agent.expert_agent import build_strategy_metrics, choose_decision, estimate_equity
from poker.cards import Card
from poker.game import PokerGame


class FakeClient:
    def __init__(self, decision=None, error=None):
        self.decision = decision
        self.error = error
        self.system_prompt = ""
        self.user_prompt = ""

    def complete_json(self, system_prompt, user_prompt):
        self.system_prompt = system_prompt
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


def test_equity_estimate_never_reads_opponents_hidden_card_values():
    game = heads_up_ai_turn()
    game.players[1].hole_cards = [Card(14, "♠"), Card(14, "♥")]
    game.players[0].hole_cards = [Card(2, "♣"), Card(3, "♦")]
    first = estimate_equity(game, 1, samples=60, rng=random.Random(17))

    game.players[0].hole_cards = [Card(13, "♣"), Card(13, "♦")]
    second = estimate_equity(game, 1, samples=60, rng=random.Random(17))

    assert first == second
    assert 0 <= first <= 1


def test_expert_metrics_are_bounded_and_offer_only_legal_sizes():
    game = heads_up_ai_turn()
    metrics = build_strategy_metrics(game, 1, samples=30, rng=random.Random(9))

    assert 0 <= metrics["estimated_equity"] <= 1
    assert 0 <= metrics["pot_odds"] <= 1
    assert 0 <= metrics["minimum_defense_frequency"] <= 1
    assert metrics["position"] in {"dealer", "early", "late"}
    assert all(
        game.minimum_raise_to
        <= amount
        <= game.players[1].street_bet + game.players[1].chips
        for amount in metrics["suggested_bet_sizes_to"]
    )


def test_expert_ai_uses_valid_deepseek_decision_without_reason():
    game = heads_up_ai_turn()
    client = FakeClient({"action": "check", "amount_to": 0})

    assert choose_decision(game, 1, client=client) == ("check", 0, "高手 AI")
    assert "reason" not in client.user_prompt
    assert "不要解释原因" in client.system_prompt


def test_expert_ai_falls_back_when_api_fails(monkeypatch):
    game = heads_up_ai_turn()
    client = FakeClient(error=DeepSeekError("模拟失败"))
    monkeypatch.setattr(
        "agent.expert_agent.choose_fallback_action",
        lambda current_game, player_index: ("check", 0),
    )

    assert choose_decision(game, 1, client=client) == (
        "check",
        0,
        "默认 AI 已接管",
    )
