"""牌组、发牌与中文牌面显示。"""

from __future__ import annotations

from dataclasses import dataclass
import random


SUITS = ("♠", "♥", "♦", "♣")
RANKS = tuple(range(2, 15))
RANK_LABELS = {11: "J", 12: "Q", 13: "K", 14: "A"}


@dataclass(frozen=True, order=True)
class Card:
    rank: int
    suit: str

    def __str__(self) -> str:
        return f"{RANK_LABELS.get(self.rank, self.rank)}{self.suit}"


class Deck:
    def __init__(self) -> None:
        self.cards = [Card(rank, suit) for suit in SUITS for rank in RANKS]
        random.shuffle(self.cards)

    def deal(self, count: int = 1) -> list[Card]:
        if len(self.cards) < count:
            raise ValueError("牌组中的牌不足。")
        return [self.cards.pop() for _ in range(count)]
