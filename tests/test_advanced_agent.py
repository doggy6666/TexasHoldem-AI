import pytest

from agent.advanced_agent import choose_decision
from agent.deepseek_client import DeepSeekError
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


@pytest.mark.parametrize("style", ["conservative", "aggressive"])
def test_advanced_ai_uses_deepseek_decision_without_exposing_reason(style):
    game = heads_up_ai_turn()
    client = FakeClient({"action": "check", "amount_to": 0})

    assert choose_decision(game, 1, style, client=client) == (
        "check",
        0,
        "进阶 AI",
    )
    assert "reason" not in client.user_prompt
    assert "不要解释原因" in client.system_prompt


def test_advanced_ai_falls_back_when_api_fails(monkeypatch):
    game = heads_up_ai_turn()
    client = FakeClient(error=DeepSeekError("模拟失败"))
    monkeypatch.setattr(
        "agent.advanced_agent.choose_fallback_action",
        lambda current_game, player_index: ("check", 0),
    )

    assert choose_decision(game, 1, "conservative", client=client) == (
        "check",
        0,
        "默认 AI 已接管",
    )


def test_unknown_internal_style_is_rejected():
    with pytest.raises(ValueError):
        choose_decision(heads_up_ai_turn(), 1, "unknown")
