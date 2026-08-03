"""牌桌 HTML 生成器：仅负责表现，不接触游戏规则。"""

from __future__ import annotations

from dataclasses import dataclass
from html import escape


SEAT_POSITIONS = {
    1: ("bottom",),
    2: ("bottom", "top"),
    3: ("bottom", "top-left", "top-right"),
    # Seat indices progress clockwise from the player at the bottom.
    4: ("bottom", "left", "top", "right"),
}


@dataclass(frozen=True)
class PlayerView:
    name: str
    chips: int
    status: str
    status_class: str = ""
    avatar_src: str = ""
    style_label: str = ""
    is_dealer: bool = False
    is_human: bool = False
    hole_cards_html: str = ""
    hole_cards_exiting: bool = False


def cards_html(
    cards,
    *,
    animate_from: int | None = None,
    animation_class: str = "",
    order_offset: int = 0,
) -> str:
    if not cards:
        return ""
    rendered = []
    for index, card in enumerate(cards):
        card_text = str(card)
        rank, suit = card_text[:-1], card_text[-1]
        color_class = "red" if suit in {"♥", "♦"} else "black"
        reveal_class = (
            " face-reveal"
            if animate_from is not None and index >= animate_from
            else ""
        )
        extra_animation_class = f" {animation_class}" if animation_class else ""
        rendered.append(
            f'<span class="poker-card {color_class}{reveal_class}{extra_animation_class}" '
            f'style="--card-order:{order_offset + index}">'
            f'<span class="card-corner"><span>{escape(rank)}</span>'
            f'<span>{escape(suit)}</span></span>'
            f'<span class="card-suit-main">{escape(suit)}</span>'
            "</span>"
        )
    return "".join(rendered)


def card_backs_html(
    count: int = 2,
    *,
    animation_class: str = "",
    order_offset: int = 0,
) -> str:
    return "".join(
        f'<span class="poker-card back {animation_class}" '
        f'style="--card-order:{order_offset + index}"></span>'
        for index in range(count)
    )


def build_header_html(*, mode_label: str, chips: int) -> str:
    return f"""
<div class="app-shell-header">
  <div class="brand-lockup">
    <div class="brand-mark">♠</div>
    <div class="brand-title">TexasHoldem AI</div>
  </div>
  <div class="header-meta">
    <div class="header-pill mode">{escape(mode_label)}</div>
    <div class="header-pill">● {chips:,} 筹码</div>
  </div>
</div>
"""


def _seat_html(player: PlayerView, position: str) -> str:
    avatar_markup = (
        f'<div class="seat-avatar"><img src="{player.avatar_src}"></div>'
        if player.avatar_src and not player.is_human
        else ""
    )
    dealer = '<span class="dealer-marker">庄家</span>' if player.is_dealer else ""
    style = (
        f'<span class="ai-level">{escape(player.style_label)}</span>'
        if player.style_label
        else ""
    )
    human_class = " is-human" if player.is_human else ""
    status_class = f" {escape(player.status_class)}" if player.status_class else ""
    # 保持为连续 HTML，避免空的风格标签被 Markdown 解析为代码块。
    return (
        f'<div class="player-seat seat-{position}{human_class}">'
        f'{avatar_markup}'
        '<div class="seat-copy">'
        f'<div class="seat-line"><span class="seat-name">'
        f'{escape(player.name)}</span>{dealer}</div>'
        f'{style}<div class="seat-chips">{player.chips:,} 筹码</div>'
        '</div>'
        f'<div class="seat-status{status_class}">{escape(player.status)}</div>'
        '</div>'
    )


def build_table_html(
    *,
    players: list[PlayerView],
    pot: int,
    board_html: str,
    board_is_empty: bool,
) -> str:
    positions = SEAT_POSITIONS[len(players)]
    seats = []
    hole_cards = []
    for player, position in zip(players, positions):
        seats.append(_seat_html(player, position))
        if player.hole_cards_html:
            exit_class = " fold-out" if player.hole_cards_exiting else ""
            hole_cards.append(
                f'<div class="hole-cards hole-{position}{exit_class}">'
                f"{player.hole_cards_html}</div>"
            )
    board = (
        '<span class="community-empty">尚未发出公共牌</span>'
        if board_is_empty
        else board_html
    )
    return f"""
<div class="table-stage player-count-{len(players)}">
  <div class="table-surface"></div>
  <div class="pot-hud">
    <div class="pot-hud-label">当前底池</div>
    <div class="pot-hud-value">{pot:,}</div>
  </div>
  <div class="board-caption">公共牌（community cards）</div>
  <div class="community-zone">{board}</div>
  {''.join(hole_cards)}
  {''.join(seats)}
</div>
"""
