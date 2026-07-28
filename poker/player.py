"""玩家数据对象。"""

from __future__ import annotations

from dataclasses import dataclass, field

from poker.cards import Card


@dataclass
class Player:
    name: str
    chips: int
    seat: int = 0
    avatar_id: int | None = None
    ai_persona: str = "novice"
    hole_cards: list[Card] = field(default_factory=list)
    street_bet: int = 0
    hand_contribution: int = 0
    folded: bool = False
    all_in: bool = False

    def reset_for_hand(self) -> None:
        self.hole_cards = []
        self.street_bet = 0
        self.hand_contribution = 0
        self.folded = False
        self.all_in = False
