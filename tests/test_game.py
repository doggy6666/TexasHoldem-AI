import random

import pytest

from poker.cards import Card
from poker.game import AVATAR_NICKNAMES, PokerGame
from poker.pots import build_pots
from agent.default_agent import choose_action


def test_three_player_blinds_and_preflop_action_order():
    game = PokerGame(total_players=3)
    game.start_hand()
    assert game.dealer_index == 0
    assert game.small_blind_index == 1
    assert game.big_blind_index == 2
    assert game.turn_index == 0
    assert game.pot == 30


def test_dealer_rotates_for_four_player_table():
    game = PokerGame(total_players=4)
    game.start_hand()
    assert game.dealer_index == 0
    game.status = "已结束"
    game.start_hand()
    assert game.dealer_index == 1


def test_multiple_all_ins_create_main_and_side_pot():
    game = PokerGame(total_players=3)
    contributions = [100, 200, 200]
    for player, amount in zip(game.players, contributions):
        player.hand_contribution = amount
        player.folded = False
    pots = build_pots(game.players)
    assert [pot.amount for pot in pots] == [300, 200]
    assert pots[0].eligible_seats == {0, 1, 2}
    assert pots[1].eligible_seats == {1, 2}


def test_folded_contribution_levels_with_same_eligible_players_are_one_pot():
    game = PokerGame(total_players=4)
    for player, amount in zip(game.players, [80, 20, 50, 80]):
        player.hand_contribution = amount
    game.players[1].folded = True
    game.players[2].folded = True

    pots = build_pots(game.players)

    assert len(pots) == 1
    assert pots[0].amount == 230
    assert pots[0].eligible_seats == {0, 3}


def test_main_and_side_pots_are_awarded_to_eligible_winners():
    game = PokerGame(total_players=3)
    for player, amount in zip(game.players, [100, 200, 200]):
        player.hand_contribution = amount
    game.pot = 500
    game.community_cards = [Card(2, "♠"), Card(7, "♥"), Card(9, "♦"), Card(11, "♣"), Card(3, "♠")]
    game.players[0].hole_cards = [Card(14, "♠"), Card(14, "♥")]  # 主池最强：一对 A
    game.players[1].hole_cards = [Card(13, "♠"), Card(13, "♥")]  # 边池最强：一对 K
    game.players[2].hole_cards = [Card(12, "♠"), Card(12, "♥")]
    game._showdown()
    assert game.players[0].chips == 1300
    assert game.players[1].chips == 1200
    assert game.players[2].chips == 1000


def test_tied_side_pot_result_lists_each_winners_payout():
    game = PokerGame(total_players=4)
    for player, amount in zip(game.players, [100, 200, 200, 200]):
        player.hand_contribution = amount
    game.pot = 700
    game.community_cards = [
        Card(2, "♠"), Card(7, "♥"), Card(9, "♦"), Card(11, "♣"), Card(3, "♠")
    ]
    game.players[0].hole_cards = [Card(14, "♠"), Card(14, "♥")]
    game.players[1].hole_cards = [Card(13, "♠"), Card(13, "♥")]
    game.players[2].hole_cards = [Card(13, "♣"), Card(13, "♦")]
    game.players[3].hole_cards = [Card(12, "♠"), Card(12, "♥")]

    game._showdown()

    assert "赢得主池 400 筹码" in game.result
    assert "平分第 1 边池 300 筹码" in game.result
    assert f"{game.players[1].name}获得 150 筹码" in game.result
    assert f"{game.players[2].name}获得 150 筹码" in game.result


def test_standard_identical_best_five_splits_pot():
    game = PokerGame()
    game.human.hole_cards = [Card(13, "♠"), Card(2, "♥")]
    game.players[1].hole_cards = [Card(12, "♠"), Card(3, "♥")]
    game.community_cards = [Card(14, "♣"), Card(13, "♦"), Card(12, "♣"), Card(11, "♦"), Card(10, "♣")]
    game.players[0].hand_contribution = game.players[1].hand_contribution = 50
    game.pot = 100
    game._showdown()
    assert game.human.chips == 1050
    assert game.players[1].chips == 1050
    assert "平分主池 100 筹码" in game.result
    assert "你获得 50 筹码" in game.result
    assert f"{game.players[1].name}获得 50 筹码" in game.result


def test_split_pot_result_lists_each_winners_actual_payout_with_remainder():
    game = PokerGame(total_players=3)
    game.dealer_index = -1
    game.community_cards = [
        Card(14, "♣"), Card(13, "♦"), Card(12, "♣"), Card(11, "♦"), Card(2, "♣")
    ]
    game.players[0].hole_cards = [Card(10, "♠"), Card(3, "♥")]
    game.players[1].hole_cards = [Card(10, "♥"), Card(4, "♠")]
    game.players[2].hole_cards = [Card(9, "♠"), Card(8, "♥")]
    for player in game.players:
        player.hand_contribution = 101
    game.pot = 303

    game._showdown()

    assert game.players[0].chips == 1152
    assert game.players[1].chips == 1151
    assert game.players[2].chips == 1000
    assert "平分主池 303 筹码" in game.result
    assert "你获得 152 筹码" in game.result
    assert f"{game.players[1].name}获得 151 筹码" in game.result


def test_short_stack_all_in_runs_out_by_streets():
    game = PokerGame(total_players=2, starting_chips=30)
    game.start_hand()
    game.human_action("all_in")
    while game.status == "进行中" and game.turn_index is not None and game.turn_index != 0:
        game.play_next_ai_turn()
    # AI may fold; otherwise a fully all-in hand runs out one street at a time.
    if game.all_in_runout_pending:
        game.deal_next_all_in_street()
        assert len(game.community_cards) == 3
        game.deal_next_all_in_street()
        assert len(game.community_cards) == 4
        game.deal_next_all_in_street()
        assert len(game.community_cards) == 5


def test_river_all_in_goes_directly_to_showdown_without_sixth_card():
    game = PokerGame(total_players=4)
    game.start_hand()
    game.community_cards = game.deck.deal(5)
    game.street_index = 2
    for player in game.players:
        player.all_in = True
    game._schedule_all_in_runout()
    assert game.status == "已结束"
    assert not game.all_in_runout_pending
    assert len(game.community_cards) == 5


def test_ai_raise_gives_human_another_raise_decision():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("call")
    game._apply_action(1, "raise", 40)
    assert game.turn_index == 0
    assert game.amount_to_call(0) == 20
    game.human_action("raise", 80)
    assert game.turn_index == 1


def test_showdown_lists_every_players_hand_description():
    game = PokerGame(total_players=3)
    game.start_hand()
    game.community_cards = game.deck.deal(5)
    for player in game.players:
        player.hand_contribution = 20
    game.pot = 60
    game._showdown()
    assert len(game.showdown_details) == 3
    assert all("手牌：" in detail for detail in game.showdown_details)


def test_latest_ai_action_is_available_near_seat_display():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("call")
    game._apply_action(1, "raise", 40)
    assert game.last_actions[1] == "加注（raise）至 40"


def test_actions_are_current_street_only_and_blinds_are_not_actions():
    game = PokerGame(total_players=3)
    game.start_hand()
    assert game.last_actions == {}
    game.last_actions = {1: "跟注（call）20"}
    game._advance_street()
    assert game.last_actions == {}


def test_avatar_nicknames_are_fixed_and_unique():
    game = PokerGame(total_players=4)
    ai_players = game.players[1:]
    assert len({player.name for player in ai_players}) == 3
    assert all(player.name == AVATAR_NICKNAMES[player.avatar_id] for player in ai_players)


def test_busted_ai_is_marked_out_after_hand():
    game = PokerGame(total_players=3)
    game.players[1].chips = 0
    game.status = "已结束"
    assert game.is_out(1)


def test_last_action_remains_visible_until_street_transition_continues():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("call")
    game._apply_action(1, "check")
    assert game.pending_street_advance
    assert game.street_index == -1
    assert game.last_actions[1] == "过牌（check）"
    game.continue_after_action()
    assert game.street_index == 0
    assert game.last_actions == {}


def test_uncalled_excess_is_refunded_instead_of_creating_single_player_side_pot():
    game = PokerGame(total_players=3)
    for player, amount in zip(game.players, [200, 100, 50]):
        player.hand_contribution = amount
    game.players[0].street_bet = 200
    game.players[0].chips = 800
    game.pot = 350
    game._return_uncalled_excess()
    assert game.players[0].hand_contribution == 100
    assert game.players[0].chips == 900
    assert game.pot == 250
    assert [pot.amount for pot in build_pots(game.players)] == [150, 100]


def test_folded_ai_hand_is_never_in_showdown_details():
    game = PokerGame(total_players=3)
    game.start_hand()
    game.community_cards = game.deck.deal(5)
    game.players[1].folded = True
    game._build_showdown_details()
    folded_detail = next(detail for detail in game.showdown_details if game.players[1].name in detail)
    assert "手牌未公开" in folded_detail
    assert str(game.players[1].hole_cards[0]) not in folded_detail


def test_winner_hand_stays_hidden_when_everyone_else_folds():
    game = PokerGame(total_players=3)
    game.start_hand()
    winner = game.players[2]
    winner_cards = [str(card) for card in winner.hole_cards]

    game.human_action("fold")
    game._apply_action(1, "fold")

    assert game.status == "已结束"
    assert game.ended_without_showdown is True
    winner_detail = next(
        detail for detail in game.showdown_details
        if detail.startswith(f"{winner.name}｜")
    )
    assert "其他玩家均已弃牌，手牌未公开" in winner_detail
    assert all(card not in winner_detail for card in winner_cards)


def test_call_action_reports_target_total_not_increment():
    game = PokerGame(total_players=2)
    game.start_hand()
    game.human_action("call")
    assert game.last_actions[0] == "跟注（call）至 20"


def test_balanced_ai_folds_weak_hand_to_large_all_in_but_calls_with_aces():
    weak_game = PokerGame(total_players=2)
    weak_game.start_hand()
    weak_game.human_action("all_in")
    weak_game.players[1].hole_cards = [Card(2, "♠"), Card(3, "♥")]
    assert choose_action(weak_game, 1)[0] == "fold"

    strong_game = PokerGame(total_players=2)
    strong_game.start_hand()
    strong_game.human_action("all_in")
    strong_game.players[1].hole_cards = [Card(14, "♠"), Card(14, "♥")]
    assert choose_action(strong_game, 1)[0] == "all_in"


def test_showdown_rebuilds_stale_pots_after_refunding_unique_excess():
    game = PokerGame(total_players=4)
    for player, amount in zip(game.players, [1300, 900, 900, 900]):
        player.hand_contribution = amount
        player.chips = 0
        player.all_in = True
    game.pot = 4000
    game.community_cards = [
        Card(6, "♥"), Card(11, "♠"), Card(14, "♦"), Card(6, "♣"), Card(5, "♥")
    ]
    game.players[0].hole_cards = [Card(4, "♥"), Card(14, "♣")]
    game.players[1].hole_cards = [Card(10, "♥"), Card(7, "♦")]
    game.players[2].hole_cards = [Card(7, "♥"), Card(5, "♠")]
    game.players[3].hole_cards = [Card(6, "♠"), Card(6, "♦")]
    game.pots = build_pots(game.players)
    assert len(game.pots) == 2  # 模拟全下阶段曾提前生成的旧结构。

    game._showdown()

    assert game.pot == 3600
    assert len(game.pots) == 1
    assert game.players[0].chips == 400
    assert game.players[3].chips == 3600
    assert all(player.hand_contribution == 900 for player in game.players)
    assert "边池" not in game.result


def test_human_can_skip_remaining_ai_play_after_folding():
    random.seed(7)
    game = PokerGame(total_players=4)
    game.start_hand()
    starting_total = sum(player.chips for player in game.players) + game.pot
    game._apply_action(3, "call")
    assert game.turn_is_human
    game.human_action("fold")

    assert game.status == "进行中"
    game.fast_forward_after_human_fold()

    assert game.status == "已结束"
    assert game.skipped_to_result is True
    assert len(game.community_cards) == 5
    assert sum(game.fast_forward_chip_changes.values()) == 0
    assert sum(player.chips for player in game.players) == starting_total
    for player in game.players[1:]:
        detail = next(
            item for item in game.showdown_details
            if item.startswith(f"{player.name}｜")
        )
        if player.folded:
            assert "手牌未公开" in detail
            assert str(player.hole_cards[0]) not in detail
        else:
            assert "手牌：" in detail
            assert str(player.hole_cards[0]) in detail


def test_skip_is_rejected_before_human_folds():
    game = PokerGame(total_players=4)
    game.start_hand()

    with pytest.raises(ValueError, match="真人已弃牌"):
        game.fast_forward_after_human_fold()
