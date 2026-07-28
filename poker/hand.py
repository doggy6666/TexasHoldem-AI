"""德州扑克牌型判定。通过枚举七张牌中的所有五张组合确保比较正确。"""

from __future__ import annotations

from collections import Counter
from itertools import combinations

from poker.cards import Card


HAND_NAMES = {
    8: "同花顺（straight flush）",
    7: "四条（four of a kind）",
    6: "葫芦（full house）",
    5: "同花（flush）",
    4: "顺子（straight）",
    3: "三条（three of a kind）",
    2: "两对（two pair）",
    1: "一对（one pair）",
    0: "高牌（high card）",
}
RANK_TEXT = {14: "A", 13: "K", 12: "Q", 11: "J", 10: "10", 9: "9", 8: "8", 7: "7", 6: "6", 5: "5", 4: "4", 3: "3", 2: "2"}


def _straight_high(ranks: list[int]) -> int | None:
    unique = set(ranks)
    if 14 in unique:
        unique.add(1)
    for high in range(14, 4, -1):
        if all(rank in unique for rank in range(high - 4, high + 1)):
            return high
    return None


def score_five(cards: tuple[Card, ...]) -> tuple[int, ...]:
    """返回可直接比较的牌型分数，元组越大表示牌越强。"""
    ranks = sorted((card.rank for card in cards), reverse=True)
    counts = Counter(ranks)
    groups = sorted(((count, rank) for rank, count in counts.items()), reverse=True)
    is_flush = len({card.suit for card in cards}) == 1
    straight_high = _straight_high(ranks)

    if is_flush and straight_high:
        return (8, straight_high)
    if groups[0][0] == 4:
        four = groups[0][1]
        kicker = next(rank for rank in ranks if rank != four)
        return (7, four, kicker)
    if groups[0][0] == 3 and groups[1][0] == 2:
        return (6, groups[0][1], groups[1][1])
    if is_flush:
        return (5, *ranks)
    if straight_high:
        return (4, straight_high)
    if groups[0][0] == 3:
        trips = groups[0][1]
        kickers = sorted((rank for rank in ranks if rank != trips), reverse=True)
        return (3, trips, *kickers)
    pairs = sorted((rank for rank, count in counts.items() if count == 2), reverse=True)
    if len(pairs) == 2:
        kicker = next(rank for rank in ranks if rank not in pairs)
        return (2, pairs[0], pairs[1], kicker)
    if len(pairs) == 1:
        pair = pairs[0]
        kickers = sorted((rank for rank in ranks if rank != pair), reverse=True)
        return (1, pair, *kickers)
    return (0, *ranks)


def best_hand(cards: list[Card]) -> tuple[tuple[int, ...], str]:
    if len(cards) < 5:
        raise ValueError("至少需要五张牌才能判断牌型。")
    score = max(score_five(combo) for combo in combinations(cards, 5))
    return score, HAND_NAMES[score[0]]


def describe_score(score: tuple[int, ...]) -> str:
    """用自然、具体的中文描述最佳五张牌。"""
    kind, values = score[0], score[1:]
    labels = [RANK_TEXT[value] for value in values]
    if kind == 8:
        return "皇家同花顺" if values[0] == 14 else f"高牌为 {labels[0]} 的同花顺"
    if kind == 4:
        return f"高牌为 {labels[0]} 的顺子"
    if kind == 7:
        return f"四条 {labels[0]} 带一个 {labels[1]}"
    if kind == 6:
        return f"三条 {labels[0]} 带一对 {labels[1]} 的葫芦"
    if kind == 5:
        return f"高牌为 {labels[0]} 的同花"
    if kind == 3:
        return f"三条 {labels[0]}"
    if kind == 2:
        return f"一对 {labels[0]} 和一对 {labels[1]}"
    if kind == 1:
        return f"一对 {labels[0]}"
    return f"高牌为 {labels[0]}"
