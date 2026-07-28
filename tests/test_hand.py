from poker.cards import Card
from poker.hand import best_hand, describe_score


def cards(values):
    return [Card(rank, suit) for rank, suit in values]


def test_wheel_straight_is_recognized():
    score, name = best_hand(cards([(14, "♠"), (2, "♥"), (3, "♦"), (4, "♣"), (5, "♠")]))
    assert score == (4, 5)
    assert name == "顺子（straight）"


def test_flush_beats_straight():
    flush, _ = best_hand(cards([(14, "♥"), (12, "♥"), (9, "♥"), (7, "♥"), (3, "♥")]))
    straight, _ = best_hand(cards([(10, "♠"), (9, "♥"), (8, "♦"), (7, "♣"), (6, "♠")]))
    assert flush > straight


def test_best_five_is_selected_from_seven_cards():
    score, name = best_hand(cards([(14, "♠"), (13, "♠"), (12, "♠"), (11, "♠"), (10, "♠"), (2, "♥"), (3, "♦")]))
    assert score == (8, 14)
    assert name == "同花顺（straight flush）"


def test_same_pair_is_decided_by_kickers_before_tie():
    # 公共牌形成一对 10；玩家 A 的 K 踢脚高于玩家 B 的 Q 踢脚，不能判平局。
    player_a, _ = best_hand(cards([
        (10, "♠"), (10, "♥"), (8, "♦"), (5, "♣"), (2, "♠"), (13, "♦"), (3, "♥")
    ]))
    player_b, _ = best_hand(cards([
        (10, "♠"), (10, "♥"), (8, "♦"), (5, "♣"), (2, "♠"), (12, "♦"), (3, "♥")
    ]))
    assert player_a > player_b


def test_identical_best_five_is_a_tie():
    player_a, _ = best_hand(cards([
        (14, "♠"), (13, "♥"), (12, "♦"), (11, "♣"), (9, "♠"), (2, "♦"), (3, "♥")
    ]))
    player_b, _ = best_hand(cards([
        (14, "♠"), (13, "♥"), (12, "♦"), (11, "♣"), (9, "♠"), (4, "♦"), (5, "♥")
    ]))
    assert player_a == player_b


def test_hand_description_uses_natural_specific_ranks():
    assert describe_score((1, 9, 14, 13, 7)) == "一对 9"
    assert describe_score((2, 14, 9, 7)) == "一对 A 和一对 9"
    assert describe_score((4, 14)) == "高牌为 A 的顺子"
    assert describe_score((8, 14)) == "皇家同花顺"
