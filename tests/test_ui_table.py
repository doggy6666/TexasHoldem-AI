from poker.cards import Card
from ui_table import PlayerView, build_table_html, card_backs_html, cards_html


def player_views(count):
    return [
        PlayerView(
            name="你" if index == 0 else f"AI {index}",
            chips=1000,
            status="等待开局",
            is_human=index == 0,
            hole_cards_html=card_backs_html(2),
        )
        for index in range(count)
    ]


def table_markup(count):
    return build_table_html(
        players=player_views(count),
        pot=0,
        board_html="",
        board_is_empty=True,
    )


def test_table_uses_distinct_two_three_and_four_player_positions():
    one_player = table_markup(1)
    assert one_player.count('class="player-seat ') == 1
    assert 'seat-bottom' in one_player

    two_player = table_markup(2)
    assert 'seat-bottom' in two_player
    assert 'seat-top' in two_player

    three_player = table_markup(3)
    assert 'seat-bottom' in three_player
    assert 'seat-top-left' in three_player
    assert 'seat-top-right' in three_player

    four_player = table_markup(4)
    assert 'seat-bottom' in four_player
    assert 'seat-top' in four_player
    assert 'seat-left' in four_player
    assert 'seat-right' in four_player


def test_card_markup_has_one_element_per_card_and_no_hidden_text():
    faces = cards_html([Card(14, "♠"), Card(10, "♥")])
    backs = card_backs_html(2, animation_class="deal-in")

    assert faces.count('class="poker-card') == 2
    assert "A" in faces and "10" in faces
    assert backs.count('class="poker-card back deal-in"') == 2
    assert "隐藏的牌" not in backs


def test_folded_cards_can_render_with_an_exit_animation_class():
    markup = build_table_html(
        players=[
            PlayerView(
                name="你",
                chips=1000,
                status="已弃牌",
                is_human=True,
                hole_cards_html=card_backs_html(2),
                hole_cards_exiting=True,
            ),
            PlayerView(name="AI", chips=1000, status="等待开局"),
        ],
        pot=30,
        board_html="",
        board_is_empty=True,
    )

    assert 'class="hole-cards hole-bottom fold-out"' in markup
