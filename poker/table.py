"""多人牌桌的位置与顺时针座位工具。"""

from __future__ import annotations

from poker.player import Player


def next_active_seat(players: list[Player], start: int) -> int:
    """从 start 的下一个座位起，寻找仍有筹码的玩家。"""
    for offset in range(1, len(players) + 1):
        index = (start + offset) % len(players)
        if players[index].chips > 0:
            return index
    raise ValueError("牌桌上没有可继续游戏的玩家。")


def clockwise_from(players: list[Player], start: int) -> list[int]:
    return [(start + offset) % len(players) for offset in range(1, len(players) + 1)]
