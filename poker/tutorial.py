"""固定四人示例对局：零联网调用，用于帮助新手理解完整流程。"""

from __future__ import annotations

from agent.modes import OFFLINE
from poker.cards import Card, RANKS, SUITS
from poker.game import PokerGame


TUTORIAL_HOLE_CARDS = {
    0: [Card(14, "♠"), Card(13, "♠")],
    1: [Card(14, "♥"), Card(14, "♦")],
    2: [Card(12, "♥"), Card(12, "♦")],
    3: [Card(9, "♥"), Card(9, "♦")],
}
TUTORIAL_BOARD = [
    Card(10, "♠"),
    Card(11, "♠"),
    Card(12, "♠"),
    Card(2, "♣"),
    Card(3, "♥"),
]


def create_tutorial_game() -> PokerGame:
    game = PokerGame(total_players=4)
    for player in game.players[1:]:
        player.ai_persona = OFFLINE
    game.start_hand()

    for seat, cards in TUTORIAL_HOLE_CARDS.items():
        game.players[seat].hole_cards = list(cards)

    used_cards = {
        card
        for cards in TUTORIAL_HOLE_CARDS.values()
        for card in cards
    } | set(TUTORIAL_BOARD)
    remaining_cards = [
        Card(rank, suit)
        for suit in SUITS
        for rank in RANKS
        if Card(rank, suit) not in used_cards
    ]
    flop = TUTORIAL_BOARD[:3]
    turn = TUTORIAL_BOARD[3]
    river = TUTORIAL_BOARD[4]
    # Deck.deal() 从列表末尾依次取牌。
    game.deck.cards = remaining_cards + [
        river,
        turn,
        flop[2],
        flop[1],
        flop[0],
    ]
    game.current_hand_record["human_hole_cards"] = [
        str(card) for card in game.human.hole_cards
    ]
    game.current_hand_record["tutorial"] = True
    game.tutorial_mode = True
    game.log.append(
        "示例对局开始：AI 只会跟注或过牌，请尝试完成四个下注阶段。"
    )
    return game


def choose_tutorial_action(
    game,
    player_index: int,
) -> tuple[str, int, str]:
    if game.amount_to_call(player_index) > 0:
        return "call", 0, "教程 AI"
    return "check", 0, "教程 AI"


def tutorial_strategy_tip(game) -> dict:
    if game.street_index < 0:
        return {
            "recommended_action": "加注（raise）",
            "amount_to": game.minimum_raise_to,
            "reason": (
                "你的 A♠、K♠ 是点数很高且同一花色的起手牌。"
                "在这个示例中可以加注，观察其他玩家跟注后进入翻牌圈。"
            ),
            "risk": "这时还没有公共牌，强起手牌也并非已经获胜。",
        }
    if game.street_index == 0:
        return {
            "recommended_action": "下注（bet）",
            "amount_to": game.big_blind,
            "reason": (
                "翻牌是 10♠、J♠、Q♠，与你的 A♠、K♠组成皇家同花顺，"
                "这是德州扑克中最强的牌型。"
            ),
            "risk": "示例 AI 只会跟注或过牌；真实对局中的对手可能弃牌或加注。",
        }
    return {
        "recommended_action": "下注（bet）",
        "amount_to": game.big_blind,
        "reason": (
            "你已经组成皇家同花顺，后续公共牌不会让任何其他五张牌超过它。"
            "可以继续下注，体验转牌圈和河牌圈。"
        ),
        "risk": "这是固定教学牌局，真实牌局不会预先知道后续公共牌。",
    }
