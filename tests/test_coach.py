import json

import pytest

from agent.coach import (
    CoachError,
    build_review_payload,
    build_tip_payload,
    decision_cache_key,
    generate_deep_review,
    generate_realtime_tip,
    review_cache_key,
)
from agent.deepseek_client import DeepSeekError
from poker.cards import Card
from poker.game import PokerGame


class FakeClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def complete_json(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        if self.error:
            raise self.error
        return self.result


def test_realtime_tip_uses_only_player_visible_information():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human.hole_cards = [Card(14, "♠"), Card(13, "♠")]
    game.players[1].hole_cards = [Card(2, "♣"), Card(3, "♦")]
    client = FakeClient(
        {
            "action": "call",
            "amount_to": None,
            "reason": "价格较低，可以继续观察。",
            "risk": "翻牌后仍需根据牌面调整。",
        }
    )

    result = generate_realtime_tip(game, client=client)
    serialized_prompt = client.calls[0][1]

    assert result["recommended_action"] == "跟注（call）"
    assert len(client.calls) == 1
    assert "A♠" in serialized_prompt
    assert "2♣" not in serialized_prompt
    assert "3♦" not in serialized_prompt
    assert '"deck"' not in serialized_prompt


def test_tip_cache_key_changes_after_player_decision():
    game = PokerGame(total_players=2)
    game.start_hand()
    before = decision_cache_key(game)
    game.human_action("call")

    assert decision_cache_key(game) != before


def test_deep_review_uses_completed_structured_record():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("fold")
    client = FakeClient(
        {
            "summary": "翻前面对盲注选择弃牌。",
            "strengths": ["及时控制了后续投入。"],
            "improvements": ["可以结合起手牌范围判断。"],
            "next_focus": "关注位置与起手牌范围。",
        }
    )

    result = generate_deep_review(game, client=client)
    payload = json.loads(client.calls[0][1].split("\n", 1)[1])

    assert result["summary"]
    assert payload["completed"] is True
    assert review_cache_key(game)
    assert len(client.calls) == 1


def test_coaching_requires_correct_game_moment():
    game = PokerGame(total_players=2)
    with pytest.raises(CoachError):
        build_tip_payload(game)
    with pytest.raises(CoachError):
        build_review_payload(game)


def test_api_failure_has_no_local_strategy_fallback():
    game = PokerGame(total_players=2)
    game.start_hand()
    client = FakeClient(error=DeepSeekError("模拟 API 不可用"))

    with pytest.raises(CoachError, match="模拟 API 不可用"):
        generate_realtime_tip(game, client=client)


def test_realtime_tip_rejects_illegal_ai_recommendation():
    game = PokerGame(total_players=2)
    game.start_hand()
    client = FakeClient(
        {
            "action": "check",
            "amount_to": None,
            "reason": "模拟非法建议。",
            "risk": "无。",
        }
    )

    with pytest.raises(CoachError, match="不可执行"):
        generate_realtime_tip(game, client=client)
