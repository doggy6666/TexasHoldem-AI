import time

import pytest

from agent.modes import (
    ADVANCED_AGGRESSIVE,
    ADVANCED_CONSERVATIVE,
    EXPERT,
    NOVICE,
    OFFLINE,
)
from agent.router import (
    AI_DECISION_TIMEOUT_SECONDS,
    choose_persona_decision,
)
from poker.game import PokerGame


@pytest.mark.parametrize(
    ("persona", "target", "expected"),
    [
        (OFFLINE, "offline", ("check", 0, "默认 AI 已接管")),
        (NOVICE, "novice", ("check", 0, "新手 AI")),
        (
            ADVANCED_CONSERVATIVE,
            "advanced_conservative",
            ("check", 0, "进阶 AI"),
        ),
        (
            ADVANCED_AGGRESSIVE,
            "advanced_aggressive",
            ("check", 0, "进阶 AI"),
        ),
        (EXPERT, "expert", ("check", 0, "高手 AI")),
    ],
)
def test_router_selects_the_seat_persona(monkeypatch, persona, target, expected):
    game = PokerGame(total_players=2)
    game.players[1].ai_persona = persona
    calls = []

    monkeypatch.setattr(
        "agent.router.choose_novice_decision",
        lambda current_game, index: calls.append(("novice", None)) or expected,
    )
    monkeypatch.setattr(
        "agent.router.choose_advanced_decision",
        lambda current_game, index, style: calls.append((f"advanced_{style}", style))
        or expected,
    )
    monkeypatch.setattr(
        "agent.router.choose_expert_decision",
        lambda current_game, index: calls.append(("expert", None)) or expected,
    )
    monkeypatch.setattr(
        "agent.router.choose_fallback_action",
        lambda current_game, index: calls.append(("offline", None)) or expected[:2],
    )

    assert choose_persona_decision(game, 1) == expected
    assert calls[0][0] == target


def test_router_uses_default_ai_for_unknown_persona(monkeypatch):
    game = PokerGame(total_players=2)
    game.players[1].ai_persona = "unknown"
    monkeypatch.setattr(
        "agent.router.choose_fallback_action",
        lambda current_game, index: ("check", 0),
    )

    assert choose_persona_decision(game, 1) == (
        "check",
        0,
        "默认 AI 已接管",
    )


def test_online_ai_has_five_second_production_timeout():
    assert AI_DECISION_TIMEOUT_SECONDS == 5.0


def test_online_ai_timeout_uses_default_ai(monkeypatch):
    game = PokerGame(total_players=2)
    game.players[1].ai_persona = EXPERT

    def slow_expert(current_game, index):
        time.sleep(0.2)
        return "raise", 100, "高手 AI"

    monkeypatch.setattr(
        "agent.router.AI_DECISION_TIMEOUT_SECONDS",
        0.03,
    )
    monkeypatch.setattr(
        "agent.router.choose_expert_decision",
        slow_expert,
    )
    monkeypatch.setattr(
        "agent.router.choose_fallback_action",
        lambda current_game, index: ("check", 0),
    )

    started_at = time.monotonic()
    result = choose_persona_decision(game, 1)
    elapsed = time.monotonic() - started_at

    assert result == ("check", 0, "默认 AI 已接管")
    assert elapsed < 0.15
