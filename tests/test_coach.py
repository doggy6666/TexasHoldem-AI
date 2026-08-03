import json
import random
from copy import deepcopy

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

    def complete_json(self, system_prompt, user_prompt, **options):
        self.calls.append((system_prompt, user_prompt, options))
        if self.error:
            raise self.error
        return self.result


class SequenceFakeClient(FakeClient):
    def __init__(self, results):
        super().__init__()
        self.results = list(results)

    def complete_json(self, system_prompt, user_prompt, **options):
        self.calls.append((system_prompt, user_prompt, options))
        return self.results[min(len(self.calls) - 1, len(self.results) - 1)]


def repeated_completed_records(record: dict, count: int = 5) -> list[dict]:
    records = []
    for index in range(1, count + 1):
        copied = deepcopy(record)
        copied["hand_number"] = index
        records.append(copied)
    return records


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
    assert '"probability_model"' in serialized_prompt
    assert '"your_two_cards_same_suit": true' in serialized_prompt
    assert 0 <= result["probability_model"]["opponent_stronger_probability"] <= 1
    assert 0 <= result["probability_model"]["average_pot_share"] <= 1
    assert (
        0
        <= result["probability_model"]["action_adjusted_win_probability"]
        <= 1
    )
    assert "estimated_equity" not in result["probability_model"]
    assert result["probability_model"]["samples"] == 1500
    assert client.calls[0][2]["max_tokens"] == 240


def test_tip_payload_separates_forced_blinds_from_voluntary_actions():
    game = PokerGame(total_players=4)
    game.dealer_index = 0
    game.start_hand()
    assert game.turn_is_human

    payload = build_tip_payload(game, probability_samples=20)

    assert payload["recent_public_actions"] == []
    facts = payload["authoritative_facts"]
    assert (
        facts["blind_posts"]["small_blind_seat"]
        == game.small_blind_index
    )
    assert (
        facts["blind_posts"]["big_blind_seat"]
        == game.big_blind_index
    )
    assert facts["opponent_voluntary_aggression_count"] == 0
    assert facts["opponent_voluntary_aggressive_actions"] == []


def test_realtime_tip_repairs_same_suit_factual_error_once():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human.hole_cards = [Card(4, "♦"), Card(9, "♦")]
    client = SequenceFakeClient(
        [
            {
                "action": "fold",
                "amount_to": None,
                "reason": "你的4和9不同花色，牌力较弱。",
                "risk": "继续可能损失更多筹码。",
            },
            {
                "action": "fold",
                "amount_to": None,
                "reason": "你的4和9同一花色，但整体胜率仍然较低。",
                "risk": "跟注后仍可能处于落后位置。",
            },
        ]
    )

    tip = generate_realtime_tip(game, client=client)

    assert len(client.calls) == 2
    assert "同一花色" in tip["reason"]
    assert "不同花色" not in tip["reason"]
    assert "上一次回答存在事实错误" in client.calls[1][1]


def test_realtime_tip_repairs_blinds_mislabeled_as_raises():
    game = PokerGame(total_players=4)
    game.dealer_index = 0
    game.start_hand()
    assert game.turn_is_human
    small_blind_name = game.players[1].name
    big_blind_name = game.players[2].name
    client = SequenceFakeClient(
        [
            {
                "action": "fold",
                "amount_to": None,
                "reason": (
                    f"{small_blind_name}和{big_blind_name}已经加注，"
                    "建议谨慎弃牌。"
                ),
                "risk": "继续可能面对更大压力。",
            },
            {
                "action": "fold",
                "amount_to": None,
                "reason": "目前只有强制盲注，尚无对手主动加注。",
                "risk": "这手牌面对三名对手时胜率有限。",
            },
        ]
    )

    tip = generate_realtime_tip(game, client=client)

    assert len(client.calls) == 2
    assert "只有强制盲注" in tip["reason"]
    assert "已经加注" not in tip["reason"]


def test_realtime_tip_blocks_repeated_factual_error():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human.hole_cards = [Card(4, "♦"), Card(9, "♦")]
    wrong_result = {
        "action": "fold",
        "amount_to": None,
        "reason": "两张牌不同花色。",
        "risk": "无。",
    }
    client = SequenceFakeClient([wrong_result, wrong_result])

    with pytest.raises(CoachError, match="事实冲突"):
        generate_realtime_tip(game, client=client)

    assert len(client.calls) == 2


def test_realtime_tip_repairs_wrong_current_hand_category():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human.hole_cards = [Card(9, "♠"), Card(14, "♥")]
    game.community_cards = [
        Card(10, "♥"),
        Card(13, "♥"),
        Card(8, "♦"),
        Card(9, "♦"),
        Card(5, "♠"),
    ]
    client = SequenceFakeClient(
        [
            {
                "action": "call",
                "amount_to": None,
                "reason": "你的牌是两对（9和A），可以跟注。",
                "risk": "对手仍可能持有更强牌。",
            },
            {
                "action": "call",
                "amount_to": None,
                "reason": "你目前是一对9，A只是未成对的高张。",
                "risk": "对手仍可能持有更强牌。",
            },
        ]
    )

    payload = build_tip_payload(game, probability_samples=20)
    facts = payload["authoritative_facts"]
    tip = generate_realtime_tip(game, client=client)

    assert facts["your_current_best_hand"] == "一对 9"
    assert facts["your_current_hand_category"] == "一对"
    assert facts["your_current_hand_score"][:2] == [1, 9]
    assert len(client.calls) == 2
    assert "一对9" in tip["reason"]
    assert "两对" not in tip["reason"]
    assert "本地牌型引擎确认" in client.calls[1][1]


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
            "confidence": "较低，当前只有5局样本。",
            "strengths": ["及时控制了后续投入。"],
            "improvements": ["可以结合起手牌范围判断。"],
            "evidence": ["第1局翻前面对盲注时选择弃牌。"],
            "next_focus": "关注位置与起手牌范围。",
        }
    )

    records = repeated_completed_records(game.current_hand_record)
    result = generate_deep_review(records, client=client)
    payload = json.loads(client.calls[0][1].split("\n", 1)[1])

    assert result["summary"]
    assert result["confidence"].startswith("较低")
    assert result["evidence"] == ["第1局翻前面对盲注时选择弃牌。"]
    assert payload["hand_count"] == 5
    assert payload["hands"][0]["completed"] is True
    assert payload["hands"][-1]["session_hand_number"] == 5
    assert payload["session_metrics"]["hands"] == 5
    assert review_cache_key(records)
    assert len(client.calls) == 1
    assert client.calls[0][2]["max_tokens"] == 1200


def test_coaching_requires_correct_game_moment():
    game = PokerGame(total_players=2)
    with pytest.raises(CoachError):
        build_tip_payload(game)
    with pytest.raises(CoachError, match="至少完成 5 局"):
        build_review_payload([])


def test_deep_review_requires_five_completed_hands():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("fold")
    records = repeated_completed_records(game.current_hand_record, 4)

    with pytest.raises(CoachError, match="至少完成 5 局"):
        build_review_payload(records)


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


def test_coaching_output_replaces_unfriendly_poker_jargon():
    game = PokerGame(total_players=2)
    game.start_hand()
    client = FakeClient(
        {
            "action": "call",
            "amount_to": None,
            "reason": "这手牌长期 EV 为负，equity 不足，对手 range 很强。",
            "risk": "pot odds 不够，注意 variance。",
        }
    )

    tip = generate_realtime_tip(game, client=client)

    combined_tip = tip["reason"] + tip["risk"]
    assert "EV" not in combined_tip
    assert "equity" not in combined_tip
    assert "range" not in combined_tip
    assert "pot odds" not in combined_tip
    assert "variance" not in combined_tip
    assert "长期平均结果" in combined_tip
    assert "综合获胜机会" in combined_tip
    assert "可能持有的牌" in combined_tip


def test_deep_review_also_replaces_unfriendly_poker_jargon():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("fold")
    client = FakeClient(
        {
            "summary": "这个选择是负 EV。",
            "strengths": ["有考虑 pot odds。"],
            "improvements": ["还要判断对手 range。"],
            "next_focus": "接受短期 variance。",
        }
    )

    records = repeated_completed_records(game.current_hand_record)
    review = generate_deep_review(records, client=client)

    combined_review = " ".join(
        [
            review["summary"],
            *review["strengths"],
            *review["improvements"],
            review["next_focus"],
        ]
    )
    assert "EV" not in combined_review
    assert "pot odds" not in combined_review
    assert "range" not in combined_review
    assert "variance" not in combined_review
    assert "长期平均收益" in combined_review
    assert "跟注成本与可能回报的比例" in combined_review


def test_folded_player_review_accepts_common_deepseek_format_variations():
    random.seed(11)
    game = PokerGame(total_players=4)
    game.start_hand()
    game._apply_action(3, "call")
    game.human_action("fold")
    game.fast_forward_after_human_fold()
    client = FakeClient(
        {
            "本局总结": "你在翻前选择了弃牌。",
            "strengths": [],
            "improvements": "可以比较跟注成本和起手牌潜力。",
            "next_focus": [
                "下一局先确认两张手牌是否同一花色。",
                "再观察自己所处的位置。",
            ],
        }
    )

    records = repeated_completed_records(game.current_hand_record)
    review = generate_deep_review(records, client=client)
    payload = json.loads(client.calls[0][1].split("\n", 1)[1])

    assert review["summary"] == "你在翻前选择了弃牌。"
    assert review["strengths"] == [
        "当前样本尚未形成明确、重复出现的优势模式。"
    ]
    assert review["improvements"] == [
        "可以比较跟注成本和起手牌潜力。"
    ]
    assert "同一花色" in review["next_focus"]
    assert "位置" in review["next_focus"]
    assert payload["hand_count"] == 5
    assert any(
        action["seat"] == 0 and action["action"] == "fold"
        for action in payload["hands"][0]["actions"]
    )


def test_deep_review_still_rejects_response_without_any_summary():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("fold")
    client = FakeClient(
        {
            "strengths": ["及时止损。"],
            "improvements": ["继续观察。"],
            "next_focus": "关注位置。",
        }
    )

    records = repeated_completed_records(game.current_hand_record)
    with pytest.raises(CoachError, match="缺少总结"):
        generate_deep_review(records, client=client)
