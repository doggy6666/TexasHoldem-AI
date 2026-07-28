from poker.hand import best_hand
from poker.tutorial import (
    TUTORIAL_BOARD,
    TUTORIAL_HOLE_CARDS,
    choose_tutorial_action,
    create_tutorial_game,
)


def play_tutorial_to_completion(game) -> None:
    for _ in range(200):
        if game.status == "已结束":
            return
        if game.all_in_runout_pending:
            game.deal_next_all_in_street()
        elif game.pending_street_advance:
            game.continue_after_action()
        elif game.turn_index == 0:
            game.human_action(
                "call" if game.amount_to_call(0) else "check"
            )
        else:
            game.play_next_ai_turn(choose_tutorial_action)
    raise AssertionError("示例对局未能在预期行动次数内结束。")


def test_tutorial_uses_fixed_unique_cards_and_no_online_personas():
    game = create_tutorial_game()

    assert game.total_players == 4
    assert game.tutorial_mode
    assert game.current_hand_record["tutorial"] is True
    assert {
        seat: player.hole_cards
        for seat, player in enumerate(game.players)
    } == TUTORIAL_HOLE_CARDS

    all_cards = [
        card
        for player in game.players
        for card in player.hole_cards
    ] + game.deck.cards
    assert len(all_cards) == 52
    assert len(set(all_cards)) == 52

    for seat in range(1, 4):
        action, amount, source = choose_tutorial_action(game, seat)
        assert action in {"call", "check"}
        assert amount == 0
        assert source == "教程 AI"


def test_tutorial_runs_through_all_streets_and_human_wins():
    game = create_tutorial_game()

    play_tutorial_to_completion(game)

    assert game.community_cards == TUTORIAL_BOARD
    human_score = best_hand(
        game.human.hole_cards + game.community_cards
    )[0]
    opponent_scores = [
        best_hand(player.hole_cards + game.community_cards)[0]
        for player in game.players[1:]
    ]
    assert human_score == (8, 14)
    assert all(human_score > score for score in opponent_scores)
    assert "你获胜" in game.result
    assert game.completed_hand_records[-1]["tutorial"] is True


def test_all_in_showdown_stays_public_through_runout_and_resets_next_hand():
    game = create_tutorial_game()
    for player in game.players:
        player.all_in = True

    game._schedule_all_in_runout()

    assert game.all_in_showdown_revealed
    while game.all_in_runout_pending:
        game.deal_next_all_in_street()
        assert game.all_in_showdown_revealed
    assert len(game.community_cards) == 5

    game.start_hand()
    assert not game.all_in_showdown_revealed
