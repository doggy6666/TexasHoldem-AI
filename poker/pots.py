"""多人全下时的主池、边池拆分与分配。"""

from __future__ import annotations

from dataclasses import dataclass

from poker.player import Player


@dataclass
class Pot:
    amount: int
    eligible_seats: set[int]


def build_pots(players: list[Player]) -> list[Pot]:
    """按每位玩家的总投入拆出主池和边池；弃牌筹码仍留在池中。"""
    levels = sorted({player.hand_contribution for player in players if player.hand_contribution > 0})
    pots: list[Pot] = []
    previous = 0
    for level in levels:
        contributors = [player for player in players if player.hand_contribution >= level]
        amount = (level - previous) * len(contributors)
        eligible = {player.seat for player in contributors if not player.folded}
        if amount:
            # 弃牌玩家在不同额度投入会形成数学分层；若相邻分层的获胜资格
            # 完全相同，它们仍属于同一个池，不应在界面伪装成多个边池。
            if pots and pots[-1].eligible_seats == eligible:
                pots[-1].amount += amount
            else:
                pots.append(Pot(amount, eligible))
        previous = level
    return pots
