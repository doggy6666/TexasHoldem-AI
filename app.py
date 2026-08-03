"""TexasHoldem AI：2–4 人桌、四种模式与 DeepSeek AI。"""

import base64
from html import escape
import importlib
import inspect
import os
import random
import re
import time
from pathlib import Path

import streamlit as st

from agent.coach import (
    CoachError,
    MIN_DEEP_REVIEW_HANDS,
    decision_cache_key,
    generate_deep_review,
    generate_realtime_tip,
    review_cache_key,
)
from agent.modes import GAME_MODES, NOVICE, personas_for_mode, public_label_for_persona
from agent.router import choose_persona_decision
from agent.training import build_training_summary
from poker.game import AVATAR_NICKNAMES, PokerGame
from poker.history import record_for_display
from poker.tutorial import (
    choose_tutorial_action,
    create_tutorial_game,
    tutorial_strategy_tip,
)
from ui_table import (
    PlayerView,
    build_header_html,
    build_table_html,
    card_backs_html,
    cards_html,
)
from ui_theme import APP_CSS
import audio_manager

# Streamlit can rerun this file while keeping an earlier dependency module cached.
# Reload only when that cached module exposes the old audio-player interface.
if "track_names" not in inspect.signature(audio_manager.render_audio).parameters:
    audio_manager = importlib.reload(audio_manager)


st.set_page_config(
    page_title="TexasHoldem AI",
    page_icon="🂡",
    layout="wide",
    initial_sidebar_state="collapsed",
)
st.markdown(APP_CSS, unsafe_allow_html=True)
MATCH_BGM_TRACKS = tuple(
    name for name in audio_manager.BGM_TRACKS if name != "Experience"
)

if "game" not in st.session_state:
    st.session_state.game = PokerGame()
game: PokerGame = st.session_state.game
if "active_mode_key" not in st.session_state:
    st.session_state.active_mode_key = "simple"
if "match_settings" not in st.session_state:
    st.session_state.match_settings = {
        "mode_key": "simple",
        "player_count": game.total_players,
        "custom_labels": {},
    }
if "shown_community_count" not in st.session_state:
    st.session_state.shown_community_count = len(game.community_cards)
if "community_flip_from" not in st.session_state:
    st.session_state.community_flip_from = None
if "strategy_tips" not in st.session_state:
    st.session_state.strategy_tips = {}
if "deep_reviews" not in st.session_state:
    st.session_state.deep_reviews = {}
if "training_records" not in st.session_state:
    st.session_state.training_records = []
if "custom_ai_randomized" not in st.session_state:
    st.session_state.custom_ai_randomized = False
if "custom_ai_randomized_count" not in st.session_state:
    st.session_state.custom_ai_randomized_count = None
if "hide_active_ai_styles" not in st.session_state:
    st.session_state.hide_active_ai_styles = False
if "flow_transition_kind" not in st.session_state:
    st.session_state.flow_transition_kind = None
if "flow_transition_key" not in st.session_state:
    st.session_state.flow_transition_key = None
if "flow_transition_deadline" not in st.session_state:
    st.session_state.flow_transition_deadline = 0.0
if "hole_deal_animation_deadline" not in st.session_state:
    st.session_state.hole_deal_animation_deadline = 0.0
if "fold_animation_deadlines" not in st.session_state:
    st.session_state.fold_animation_deadlines = {}
if "previously_folded_seats" not in st.session_state:
    st.session_state.previously_folded_seats = set()
if "strategy_panel_open" not in st.session_state:
    st.session_state.strategy_panel_open = False
if "audio_match_playlist" not in st.session_state:
    st.session_state.audio_match_playlist = False
if "audio_playlist_id" not in st.session_state:
    st.session_state.audio_playlist_id = ""
if "audio_muted" not in st.session_state:
    st.session_state.audio_muted = False
if "audio_volume_percent" not in st.session_state:
    st.session_state.audio_volume_percent = 35
elif st.session_state.audio_volume_percent < 35:
    st.session_state.audio_volume_percent = 35
if "user_nickname" not in st.session_state:
    st.session_state.user_nickname = None


def normalize_nickname(value: str) -> str:
    """Keep the player label compact enough for every seat layout."""
    compact = " ".join(value.replace("\n", " ").split())
    return compact[:12] or "创作者Zikky"


if not st.session_state.user_nickname:
    st.markdown(
        '<div class="nickname-gate-title">TexasHoldem AI</div>',
        unsafe_allow_html=True,
    )
    nickname_input = st.text_input(
        "请输入您的昵称",
        value="",
        placeholder="创作者Zikky",
        max_chars=12,
        key="nickname_input",
    )
    if st.button("进入牌局", key="nickname_submit", use_container_width=True):
        st.session_state.user_nickname = normalize_nickname(nickname_input)
        st.session_state.audio_match_playlist = False
        st.session_state.audio_playlist_id = ""
        st.rerun()
    st.stop()

AVATAR_DIR = Path(__file__).parent / "assets" / "avatars"
COMMUNITY_CARD_BACK_SECONDS = 0.7
AI_ACTION_DELAY_SECONDS = 1.25
ALL_IN_DEAL_DELAY_SECONDS = 0.6
STREET_TRANSITION_DELAY_SECONDS = 0.75
HOLE_DEAL_ANIMATION_SECONDS = 0.95
FOLD_CARD_EXIT_SECONDS = 0.42
GAME_RULES_MARKDOWN = """
#### 1. 游戏目标

每位玩家获得两张只有自己能看到的起手牌，桌面最多发出五张公共牌。
从这七张牌中选出任意五张组成最强牌型；不要求两张起手牌都被使用。
你可以在摊牌时凭最强五张牌获胜，也可以通过下注使其他玩家全部弃牌。

#### 2. 庄家、盲注与行动顺序

- 庄家标记每局顺时针轮换。
- 发牌前，庄家左侧两名仍在场的玩家依次支付小盲注 10 和大盲注 20。
- 翻牌前从大盲注左侧第一位仍在场的玩家开始，按顺时针行动。
- 翻牌后各轮从庄家左侧第一位仍在场的玩家开始，按顺时针行动。
- 双人局中，庄家支付小盲注并在翻牌前先行动；大盲注在翻牌后先行动。

#### 3. 一局牌的四个下注阶段

1. **翻牌前（pre-flop）**：每人拿到两张起手牌后进行第一轮下注。
2. **翻牌圈（flop）**：同时发出三张公共牌，再进行一轮下注。
3. **转牌圈（turn）**：发出第四张公共牌，再进行一轮下注。
4. **河牌圈（river）**：发出第五张公共牌，进行最后一轮下注。

当一轮中所有仍可行动的玩家投入相同筹码，或只剩全下玩家不能继续行动时，
该轮结束并进入下一阶段。

#### 4. 可以选择的行动

- **过牌（check）**：本轮无人下注且你不需补筹码时，将行动权交给下一位。
- **下注（bet）**：本轮无人下注时，率先投入筹码。
- **跟注（call）**：补足到本轮当前最高下注额；筹码不足时只能全下。
- **加注（raise）**：在当前最高下注额上继续提高总下注。页面会给出允许的最低总额。
- **弃牌（fold）**：放弃本局，已经投入底池的筹码不能收回，也不再有资格赢取底池。
- **全下（all in）**：投入自己剩余的全部筹码。全下后不能继续下注，但仍参与后续发牌和结算。

#### 5. 底池、退还筹码与边池

- 所有玩家都能匹配的部分组成主池。
- 当全下玩家投入金额不同时，超过较小投入层级的筹码会形成边池；
  玩家只能赢取自己有投入资格的池。
- 如果某位玩家的下注超过所有其他仍有资格玩家能够匹配的总额，
  无人匹配的多余筹码会直接退还，不会形成只有自己能赢的边池。
- 多人平分同一底池时按相同份额分配；无法整除的零头按牌桌行动顺序分配。

#### 6. 牌局如何结束

- 若只剩一名玩家没有弃牌，该玩家立即赢得当前底池；胜者和弃牌者都不公开手牌。
- 若河牌圈下注结束后仍有两人或以上未弃牌，则进入摊牌，公开这些玩家的手牌并比较。
- 已弃牌玩家的手牌始终隐藏。
- 比牌只看最强的五张牌。若牌型相同，依次比较该牌型的关键点数和踢脚牌。
- 若双方最强五张牌的点数完全相同，则平分对应底池；花色不分大小。

#### 7. 牌型大小（从强到弱）

1. **皇家同花顺**：同一花色的 10、J、Q、K、A。
2. **同花顺**：同一花色的五张连续牌，比较最高牌。
3. **四条**：四张同点数牌，再比较第五张踢脚牌。
4. **葫芦**：三条加一对，先比较三条，再比较对子。
5. **同花**：五张同花色牌，从最高牌开始逐张比较。
6. **顺子**：五张连续牌，比较最高牌；A 可组成 A、2、3、4、5，此时按 5 高顺子计算。
7. **三条**：三张同点数牌，依次比较两张踢脚牌。
8. **两对**：先比较较大对子，再比较较小对子，最后比较踢脚牌。
9. **一对**：比较对子，再依次比较三张踢脚牌。
10. **高牌**：没有以上组合时，从最高牌开始逐张比较。

#### 8. 连续对战

一局结束后，只要真人玩家和至少一名 AI 仍有筹码，就可以继续下一局；
庄家会轮换。筹码为 0 的玩家离场且不再参与发牌。点击“开始新对局”会重新选择
人数和 AI 难度，并把所有人的初始筹码恢复为 1000。
"""


def completed_training_records(records):
    """教程数据不计入玩家画像或累计深度复盘。"""
    return [record for record in records if not record.get("tutorial")]


def action_label_for_seat(action_text: str) -> str:
    """Keep seat HUD actions concise by removing English parentheticals."""
    return re.sub(r"（[^（）]*[A-Za-z][^（）]*）", "", action_text).strip()


# 兼容热更新前已存在的旧会话，同时确保头像与昵称固定对应。
for player_index, existing_player in enumerate(game.players):
    if player_index == 0:
        continue
    avatar_id = getattr(existing_player, "avatar_id", None) or ((player_index - 1) % 6 + 1)
    existing_player.avatar_id = avatar_id
    existing_player.name = AVATAR_NICKNAMES[avatar_id]
    if not hasattr(existing_player, "ai_persona"):
        existing_player.ai_persona = NOVICE
if not hasattr(game, "current_hand_record"):
    game.current_hand_record = {}
if not hasattr(game, "completed_hand_records"):
    game.completed_hand_records = []
if not hasattr(game, "skipped_to_result"):
    game.skipped_to_result = False
if not hasattr(game, "fast_forward_chip_changes"):
    game.fast_forward_chip_changes = {}
if not hasattr(game, "all_in_showdown_revealed"):
    game.all_in_showdown_revealed = False


def readable_action_rows(record, human_only=True):
    rows = []
    for action in record.get("actions", []):
        if human_only and action["seat"] != 0:
            continue
        rows.append(
            {
                "序号": action["sequence"],
                "阶段": action["street"],
                "玩家": action["player_name"],
                "行动": action["action_text"],
                "行动前底池": action["pot_before"],
                "当时需跟注": action["amount_to_call_before"],
                "行动后底池": action["pot_after"],
                "行动后筹码": action["chips_after"],
                "公共牌": "、".join(action["community_cards"]) or "翻牌前",
            }
        )
    return rows


@st.cache_data(show_spinner=False)
def avatar_data_uri(path: str):
    image_bytes = Path(path).read_bytes()
    return f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"


def begin_hole_deal_animation():
    """短时间内为新一局的手牌启用从桌面中央发出的动画。"""
    st.session_state.hole_deal_animation_deadline = (
        time.monotonic() + HOLE_DEAL_ANIMATION_SECONDS
    )


def ensure_match_bgm():
    """Start the post-entry playlist once, then keep it across UI reruns."""
    if st.session_state.audio_match_playlist:
        return
    st.session_state.audio_match_playlist = True
    st.session_state.audio_playlist_id = str(time.time_ns())


def launch_new_match(
    selected_mode,
    selected_count,
    custom_labels=None,
    random_start=False,
):
    st.session_state.match_settings = {
        "mode_key": selected_mode.key,
        "player_count": selected_count,
        "custom_labels": (
            {
                seat: label
                for seat, label in enumerate(custom_labels or [], start=1)
            }
            if selected_mode.key == "custom"
            else {}
        ),
    }
    current_game = st.session_state.game
    st.session_state.training_records.extend(
        completed_training_records(
            getattr(current_game, "completed_hand_records", [])
        )
    )
    new_game = PokerGame(total_players=selected_count)
    assigned_personas = personas_for_mode(
        selected_mode.key,
        selected_count - 1,
        custom_labels=custom_labels if selected_mode.key == "custom" else None,
    )
    for seat, persona in enumerate(assigned_personas, start=1):
        new_game.players[seat].ai_persona = persona
    new_game.start_hand()
    st.session_state.game = new_game
    st.session_state.active_mode_key = selected_mode.key
    st.session_state.hide_active_ai_styles = random_start
    st.session_state.custom_ai_randomized = bool(
        random_start and selected_mode.key == "custom"
    )
    st.session_state.custom_ai_randomized_count = (
        selected_count if st.session_state.custom_ai_randomized else None
    )
    st.session_state.shown_community_count = 0
    st.session_state.community_flip_from = None
    st.session_state.strategy_panel_open = False
    st.session_state.settings_dialog_open = False
    st.session_state.rules_dialog_open = False
    ensure_match_bgm()
    begin_hole_deal_animation()
    st.rerun()


def launch_quick_match():
    """Use the current settings and immediately start a fresh match."""
    settings = st.session_state.match_settings
    selected_mode = GAME_MODES.get(settings["mode_key"], mode_options[0])
    selected_count = int(settings["player_count"])
    custom_labels = []
    if selected_mode.key == "custom":
        custom_labels = [
            settings["custom_labels"].get(seat, "菜鸟")
            for seat in range(1, selected_count)
        ]
    launch_new_match(
        selected_mode,
        selected_count,
        custom_labels=custom_labels,
    )


def launch_tutorial_match():
    current_game = st.session_state.game
    st.session_state.training_records.extend(
        completed_training_records(
            getattr(current_game, "completed_hand_records", [])
        )
    )
    st.session_state.game = create_tutorial_game()
    st.session_state.active_mode_key = "tutorial"
    st.session_state.hide_active_ai_styles = False
    st.session_state.shown_community_count = 0
    st.session_state.community_flip_from = None
    st.session_state.strategy_panel_open = False
    st.session_state.settings_dialog_open = False
    st.session_state.rules_dialog_open = False
    ensure_match_bgm()
    begin_hole_deal_animation()
    st.rerun()


mode_options = list(GAME_MODES.values())
saved_mode = GAME_MODES.get(
    st.session_state.match_settings["mode_key"],
    mode_options[0],
)
st.session_state.setdefault("settings_dialog_open", False)
st.session_state.setdefault("rules_dialog_open", False)


def close_settings_dialog():
    st.session_state.settings_dialog_open = False


@st.dialog("游戏设置", width="large", on_dismiss=close_settings_dialog)
def settings_dialog():
    settings = st.session_state.match_settings
    dialog_mode_label = st.radio(
        "游戏模式",
        [mode.label for mode in mode_options],
        index=[
            mode.label for mode in mode_options
        ].index(saved_mode.label),
        key="settings_mode_label",
    )
    selected_mode = next(
        mode for mode in mode_options if mode.label == dialog_mode_label
    )
    st.subheader(f"{selected_mode.label}设置")
    st.caption(f"AI 对手：{selected_mode.ai_label}")
    selected_count = st.selectbox(
        "总人数（players）",
        [2, 3, 4],
        index=settings["player_count"] - 2,
        key="settings_player_count",
    )
    custom_labels = []
    if selected_mode.key == "custom":
        secret_random_match = bool(
            st.session_state.active_mode_key == "custom"
            and st.session_state.hide_active_ai_styles
        )
        if secret_random_match:
            st.caption("当前为随机 AI 对局，所有 AI 风格全程保密。")
        else:
            for seat in range(1, selected_count):
                custom_labels.append(
                    st.selectbox(
                        f"AI 座位 {seat}",
                        ["菜鸟", "进阶", "高手"],
                        index=["菜鸟", "进阶", "高手"].index(
                            settings["custom_labels"].get(seat, "菜鸟")
                        ),
                        key=f"settings_custom_ai_{seat}",
                    )
                )
    st.session_state.match_settings = {
        "mode_key": selected_mode.key,
        "player_count": selected_count,
        "custom_labels": (
            {
                seat: label
                for seat, label in enumerate(custom_labels, start=1)
            }
            if selected_mode.key == "custom"
            else {}
        ),
    }
    if st.button(
        "开始新对局",
        key="dialog_start_match",
        use_container_width=True,
    ):
        launch_new_match(
            selected_mode,
            selected_count,
            custom_labels=custom_labels,
        )
    if selected_mode.key == "custom" and st.button(
        "以随机 AI 开始新对局",
        key="dialog_random_match",
        use_container_width=True,
        help="按当前人数秘密随机分配菜鸟、进阶或高手，并立即开始新对局。",
    ):
        random_labels = [
            random.choice(["菜鸟", "进阶", "高手"])
            for _ in range(selected_count - 1)
        ]
        launch_new_match(
            selected_mode,
            selected_count,
            custom_labels=random_labels,
            random_start=True,
        )
    api_configured = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    st.caption(
        "线下对战"
        if selected_mode.key == "offline"
        else (
            "DeepSeek API：已配置"
            if api_configured
            else "未配置，使用兜底方案"
        )
    )
    st.caption("盲注：小盲 10｜大盲 20")


@st.dialog("游戏规则", width="large")
def rules_dialog():
    st.markdown(GAME_RULES_MARKDOWN)


if st.session_state.settings_dialog_open:
    settings_dialog()
elif st.session_state.rules_dialog_open:
    # Rules have no interactive controls, so render the dialog once only.
    # This prevents unrelated game-action reruns from reopening it.
    st.session_state.rules_dialog_open = False
    rules_dialog()

if st.session_state.shown_community_count > len(game.community_cards):
    st.session_state.shown_community_count = 0
shown_community_count = st.session_state.shown_community_count
board_reveal_pending = len(game.community_cards) > shown_community_count
community_flip_from = st.session_state.community_flip_from
st.session_state.community_flip_from = None

if game.dealer_index >= 0:
    dealer_name = game.players[game.dealer_index].name
else:
    dealer_name = "尚未确定"

ended_without_showdown = getattr(
    game,
    "ended_without_showdown",
    bool(game.result and "因其他玩家全部弃牌" in game.result),
)
hole_deal_animation_active = (
    time.monotonic() < st.session_state.hole_deal_animation_deadline
)
fold_animation_now = time.monotonic()
folded_seats = {
    index for index, player in enumerate(game.players) if player.folded
}
newly_folded_seats = folded_seats - st.session_state.previously_folded_seats
for seat in newly_folded_seats:
    st.session_state.fold_animation_deadlines[seat] = (
        fold_animation_now + FOLD_CARD_EXIT_SECONDS
    )
st.session_state.previously_folded_seats = folded_seats
folding_card_seats = {
    seat
    for seat, deadline in st.session_state.fold_animation_deadlines.items()
    if seat in folded_seats and deadline > fold_animation_now
}

if board_reveal_pending:
    new_card_count = len(game.community_cards) - shown_community_count
    board_html = (
        cards_html(game.community_cards[:shown_community_count])
        + card_backs_html(
            new_card_count,
            animation_class="new-card",
            order_offset=shown_community_count,
        )
    )
elif game.community_cards:
    board_html = cards_html(
        game.community_cards,
        animate_from=community_flip_from,
    )
else:
    board_html = ""

player_views = []
for index, player in enumerate(game.players):
    # All-in players stay visible until settlement; only eliminated AI leave.
    if index > 0 and game.is_out(index):
        continue
    if index == 0 or st.session_state.hide_active_ai_styles:
        style_label = ""
    elif getattr(game, "tutorial_mode", False):
        style_label = "教程"
    elif getattr(game, "last_ai_sources", {}).get(index) == "默认 AI 已接管":
        style_label = "默认"
    else:
        style_label = public_label_for_persona(
            getattr(player, "ai_persona", NOVICE)
        )

    show_ai_cards = (
        (
            game.status == "已结束"
            and not board_reveal_pending
            and not ended_without_showdown
        )
        or getattr(game, "all_in_showdown_revealed", False)
    )
    animation_class = "deal-in" if hole_deal_animation_active else ""
    order_offset = index * 2
    hole_cards_exiting = index in folding_card_seats
    if player.folded and not hole_cards_exiting:
        visible_cards = ""
    elif index == 0:
        visible_cards = (
            cards_html(
                player.hole_cards,
                animation_class=animation_class,
                order_offset=order_offset,
            )
            if player.hole_cards
            else ""
        )
    elif show_ai_cards and not player.folded:
        visible_cards = cards_html(player.hole_cards)
    elif player.hole_cards:
        visible_cards = card_backs_html(
            2,
            animation_class=animation_class,
            order_offset=order_offset,
        )
    else:
        visible_cards = ""

    is_out = game.is_out(index)
    last_actions = getattr(game, "last_actions", {})
    if is_out:
        action_text, action_style = "已离场", "danger"
    elif player.folded:
        action_text, action_style = "已弃牌", "danger"
    elif player.all_in:
        action_text = last_actions.get(index, "全下")
        action_style = ""
    elif game.turn_index == index:
        if index == 0:
            action_text, action_style = "👉 轮到你行动！", "acting"
        else:
            action_text, action_style = "🂡 正在思考…", "acting"
    elif index in last_actions:
        action_text = f"最近行动：{last_actions[index]}"
        action_style = ""
    elif game.status == "进行中" and player.hole_cards:
        action_text, action_style = "未行动", ""
    else:
        action_text, action_style = "等待开局", ""

    if player.hand_contribution:
        action_text = f"{action_text} · 本局投入：{player.hand_contribution}"
    action_text = action_label_for_seat(action_text)

    avatar_src = ""
    if index > 0:
        avatar_id = getattr(player, "avatar_id", None) or (
            (index - 1) % 6 + 1
        )
        avatar_src = avatar_data_uri(
            str(AVATAR_DIR / f"ai_{avatar_id}.png")
        )
    player_views.append(
        PlayerView(
            name=(
                st.session_state.user_nickname
                if index == 0
                else player.name
            ),
            chips=player.chips,
            status=action_text,
            status_class=action_style,
            avatar_src=avatar_src,
            style_label=style_label,
            is_dealer=index == game.dealer_index,
            is_human=index == 0,
            hole_cards_html=visible_cards,
            hole_cards_exiting=hole_cards_exiting,
        )
    )

active_mode = GAME_MODES.get(st.session_state.active_mode_key)
active_mode_label = (
    "示例对局"
    if getattr(game, "tutorial_mode", False)
    else (active_mode.label if active_mode else saved_mode.label)
)
st.markdown(
    build_header_html(
        mode_label=active_mode_label,
        chips=game.human.chips,
    ),
    unsafe_allow_html=True,
)

with st.container(key="top_toolbar"):
    toolbar_columns = st.columns([1.35, 1.1, 1.0, 1.0, 2.4], gap="small")
    with toolbar_columns[0]:
        if st.button(
            "开始新对局",
            key="top_open_match",
            use_container_width=True,
        ):
            launch_quick_match()
    with toolbar_columns[1]:
        if st.button(
            "游戏设置",
            key="top_open_settings",
            use_container_width=True,
        ):
            st.session_state.rules_dialog_open = False
            st.session_state.settings_dialog_open = True
            st.rerun()
    with toolbar_columns[2]:
        if st.button(
            "游戏规则",
            key="top_open_rules",
            use_container_width=True,
        ):
            st.session_state.settings_dialog_open = False
            st.session_state.rules_dialog_open = True
            st.rerun()
    with toolbar_columns[3]:
        if st.button(
            "示例对局",
            key="top_tutorial",
            use_container_width=True,
        ):
            launch_tutorial_match()

with st.container(key="audio_controls"):
    audio_manager.render_audio(
        track_names=(
            MATCH_BGM_TRACKS
            if st.session_state.audio_match_playlist
            else ("Experience",)
        ),
        cycle_tracks=st.session_state.audio_match_playlist,
        playlist_id=st.session_state.audio_playlist_id,
        volume=st.session_state.audio_volume_percent / 100,
        muted=st.session_state.audio_muted,
    )

status_text = (
    f"状态：{game.status}｜{game.street_name}｜"
    f"庄家（dealer）：{dealer_name}｜底池（pot）：{game.pot}"
)
table_markup = build_table_html(
    players=player_views,
    pot=game.pot,
    board_html=board_html,
    board_is_empty=not game.community_cards and not board_reveal_pending,
)

session_records = completed_training_records(
    st.session_state.training_records
    + game.completed_hand_records
)
training_summary = build_training_summary(session_records)
training_hands = training_summary.get("hands", 0)
training_summary.setdefault(
    "profile_stage",
    "会话级稳定画像" if training_hands >= 8 else (
        "初步画像" if training_hands >= 4 else "数据收集中"
    ),
)
training_summary.setdefault("profile_name", "等待更多数据")
training_summary.setdefault("profile_progress", min(training_hands / 8, 1.0))
training_summary.setdefault(
    "profile_confidence",
    "中等" if training_hands >= 8 else "较低",
)
training_summary.setdefault(
    "profile_basis",
    "至少 8 局形成会话级稳定画像；达到 20 局后置信度提升。",
)
training_summary.setdefault(
    "metrics",
    {
        "vpip": 0.0,
        "preflop_raise_rate": 0.0,
        "postflop_aggression_rate": 0.0,
        "fold_to_pressure_rate": 0.0,
        "all_in_hand_rate": 0.0,
        "showdown_rate": 0.0,
    },
)
training_summary.setdefault(
    "training_focus",
    ["继续完成牌局以形成训练重点。"],
)

table_column, coach_column = st.columns([3.15, 1.18], gap="medium")

with table_column:
    st.markdown(
        f'<div class="game-status-bar">{escape(status_text)}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(table_markup, unsafe_allow_html=True)
    if game.pots:
        st.caption(
            "｜".join(
                f"{'主池' if index == 0 else f'第 {index} 边池'}："
                f"{pot.amount} 筹码"
                for index, pot in enumerate(game.pots)
            )
        )

    if (
        game.status == "进行中"
        and game.human.folded
        and not board_reveal_pending
    ):
        _, skip_column, _ = st.columns([1, 1.25, 1])
        with skip_column:
            if st.button(
                "跳过",
                type="primary",
                use_container_width=True,
            ):
                try:
                    if getattr(game, "tutorial_mode", False):
                        game.fast_forward_after_human_fold(
                            decision_provider=choose_tutorial_action
                        )
                    else:
                        game.fast_forward_after_human_fold()
                except (RuntimeError, ValueError) as error:
                    st.error(f"暂时无法快速结算：{error}")
                else:
                    st.session_state.shown_community_count = len(
                        game.community_cards
                    )
                    st.session_state.community_flip_from = 0
                    st.rerun()

    if (
        game.status == "进行中"
        and game.turn_is_human
        and not board_reveal_pending
    ):
        with st.container(key="action_area"):
            st.subheader("你的行动（your action）")
            if getattr(game, "tutorial_mode", False):
                st.warning("先查看实时策略提示，再选择本轮行动。")
            to_call = game.amount_to_call(0)
            if to_call == 0:
                is_opening_bet = game.current_bet == 0
                action_name = "bet" if is_opening_bet else "raise"
                action_label = (
                    "下注（bet）" if is_opening_bet else "加注（raise）"
                )
                minimum = (
                    game.big_blind
                    if is_opening_bet
                    else game.minimum_raise_to
                )
            else:
                action_name = "raise"
                action_label = "加注（raise）"
                minimum = game.minimum_raise_to
                st.warning(f"当前需跟注（call）{to_call}。")

            max_total = game.human.street_bet + game.human.chips
            can_size_bet = max_total >= minimum
            amount = minimum
            if can_size_bet:
                amount = st.slider(
                    f"{action_label}总额（to）",
                    min_value=minimum,
                    max_value=max_total,
                    value=minimum,
                    step=game.big_blind,
                )
            buttons = st.columns(4)
            with buttons[0]:
                with st.container(key="fold_action"):
                    fold_clicked = st.button(
                        "弃牌（fold）",
                        key="fold_action_button",
                        use_container_width=True,
                    )
            if fold_clicked:
                game.human_action("fold")
                st.session_state.strategy_panel_open = False
                st.rerun()
            if to_call == 0:
                with buttons[1]:
                    with st.container(key="call_action"):
                        call_clicked = st.button(
                            "过牌（check）",
                            key="call_action_button",
                            use_container_width=True,
                        )
                if call_clicked:
                    game.human_action("check")
                    st.session_state.strategy_panel_open = False
                    st.rerun()
            elif game.human.chips >= to_call:
                with buttons[1]:
                    with st.container(key="call_action"):
                        call_clicked = st.button(
                            f"跟注（call）至 {game.current_bet}",
                            key="call_action_button",
                            use_container_width=True,
                        )
                if call_clicked:
                    game.human_action("call")
                    st.session_state.strategy_panel_open = False
                    st.rerun()
            else:
                with buttons[1]:
                    with st.container(key="call_action"):
                        st.button(
                            "跟注不足，请全下",
                            key="call_action_button",
                            disabled=True,
                            use_container_width=True,
                        )
            with buttons[2]:
                with st.container(key="raise_action"):
                    raise_clicked = st.button(
                        action_label,
                        key="raise_action_button",
                        disabled=not can_size_bet,
                        use_container_width=True,
                    )
            if raise_clicked:
                game.human_action(action_name, int(amount))
                st.session_state.strategy_panel_open = False
                st.rerun()
            with buttons[3]:
                with st.container(key="all_in_action"):
                    all_in_clicked = st.button(
                        f"全下（all in）{game.human.chips}",
                        key="all_in_action_button",
                        type="primary",
                        disabled=game.human.chips == 0,
                        use_container_width=True,
                    )
            if all_in_clicked:
                game.human_action("all_in")
                st.session_state.strategy_panel_open = False
                st.rerun()

    if game.result and not board_reveal_pending:
        with st.container(key="result_area"):
            if "你获胜" in game.result:
                st.success(game.result)
            else:
                st.error(game.result)
            if getattr(game, "skipped_to_result", False):
                chip_change_text = "｜".join(
                    (
                        f"{player.name} "
                        f"{getattr(game, 'fast_forward_chip_changes', {}).get(index, 0):+d}"
                    )
                    for index, player in enumerate(game.players)
                )
                st.caption(f"本局筹码变化：{chip_change_text}")
            if game.human.chips <= 0:
                st.error("请开始新对局")

            eligible_for_next = (
                game.human.chips > 0
                and len(
                    [
                        player
                        for player in game.players
                        if player.chips > 0
                    ]
                )
                >= 2
            )
            if getattr(game, "tutorial_mode", False):
                st.success(
                    "示例对局已完成。现在请在侧边栏选择游戏模式、"
                    "总人数和 AI 难度，再点击“开始新对局”进入正式对战。"
                )
            else:
                st.markdown("#### 继续本场对战")
                if st.button(
                    "再来一局",
                    disabled=not eligible_for_next,
                    use_container_width=True,
                ):
                    game.start_hand()
                    begin_hole_deal_animation()
                    st.session_state.strategy_panel_open = False
                    st.session_state.shown_community_count = 0
                    st.session_state.community_flip_from = None
                    st.rerun()
                if not eligible_for_next:
                    if game.human.chips <= 0:
                        st.caption("请开始新对局")
                    else:
                        st.caption(
                            "AI 对手已输光筹码，可从侧边栏开始新对局。"
                        )

with coach_column:
    with st.container(key="coach_panel"):
        st.markdown(
            '<div class="cyber-panel-title">实时策略提示</div>',
            unsafe_allow_html=True,
        )
        if getattr(game, "tutorial_mode", False):
            st.info(
                "示例对局：你固定持有 A♠、K♠。轮到你时先点击"
                "“实时策略提示”，再根据提示完成翻牌前、翻牌圈、"
                "转牌圈和河牌圈；教程对手只会跟注或过牌。"
            )

        current_tip = None
        current_tip_is_tutorial = getattr(game, "tutorial_mode", False)
        can_request_tip = (
            game.status == "进行中"
            and game.turn_is_human
            and not board_reveal_pending
        )
        if can_request_tip and current_tip_is_tutorial:
            tutorial_tip_key = f"tutorial|{decision_cache_key(game)}"
            if st.button(
                "实时策略提示",
                key=f"strategy_tip_{tutorial_tip_key}",
                use_container_width=True,
            ):
                st.session_state.strategy_panel_open = True
                st.session_state.strategy_tips[tutorial_tip_key] = (
                    tutorial_strategy_tip(game)
                )
            current_tip = st.session_state.strategy_tips.get(
                tutorial_tip_key
            )
        elif (
            can_request_tip
            and st.session_state.active_mode_key != "offline"
        ):
            tip_key = decision_cache_key(game)
            if st.button(
                "实时策略提示",
                key=f"strategy_tip_{tip_key}",
                use_container_width=True,
            ):
                st.session_state.strategy_panel_open = True
                if tip_key not in st.session_state.strategy_tips:
                    try:
                        with st.spinner("正在分析当前决策…"):
                            st.session_state.strategy_tips[tip_key] = (
                                generate_realtime_tip(game)
                            )
                    except CoachError as error:
                        st.error(f"实时策略提示暂不可用：{error}")
            current_tip = st.session_state.strategy_tips.get(tip_key)

        if current_tip and st.session_state.strategy_panel_open:
            probability_model = current_tip.get("probability_model", {})
            if probability_model:
                probability_items = (
                    (
                        "基础牌面胜率",
                        probability_model.get("win_probability", 0),
                    ),
                    (
                        "结合行动参考胜率",
                        probability_model.get(
                            "action_adjusted_win_probability",
                            0,
                        ),
                    ),
                    (
                        "对手牌力更强概率",
                        probability_model.get(
                            "opponent_stronger_probability",
                            0,
                        ),
                    ),
                    (
                        "平局概率",
                        probability_model.get("tie_probability", 0),
                    ),
                    (
                        "综合获胜机会",
                        probability_model.get("average_pot_share", 0),
                    ),
                )
                for item_index in range(0, len(probability_items), 2):
                    probability_columns = st.columns(2)
                    for column, item in zip(
                        probability_columns,
                        probability_items[item_index:item_index + 2],
                    ):
                        column.metric(item[0], f"{item[1]:.1%}")

            amount_text = (
                f"至 {current_tip['amount_to']}"
                if current_tip["amount_to"] is not None
                else ""
            )
            risk_label = "注意" if current_tip_is_tutorial else "风险"
            st.markdown(
                f"""
<div class="strategy-block">
  <div class="strategy-label">建议</div>
  <div class="strategy-action">{escape(current_tip['recommended_action'])} {escape(amount_text)}</div>
  <div class="strategy-label">依据</div>
  <div class="strategy-copy">{escape(current_tip['reason'])}</div>
  <div class="strategy-copy risk"><span class="strategy-label">{risk_label}</span><br>{escape(current_tip['risk'])}</div>
</div>
""",
                unsafe_allow_html=True,
            )

        with st.expander("AI深度复盘", expanded=False):
            if st.session_state.active_mode_key in {
                "offline",
                "tutorial",
            }:
                st.caption("线下对战和示例对局不启用联网 AI 深度复盘。")
            elif len(session_records) < MIN_DEEP_REVIEW_HANDS:
                st.info(
                    f"当前已完成 {len(session_records)} 局；"
                    f"至少完成 {MIN_DEEP_REVIEW_HANDS} 局后，"
                    "才能进行有依据的累计深度复盘。"
                )
            elif game.result and not board_reveal_pending:
                    deep_review_key = review_cache_key(session_records)
                    if st.button(
                        "AI深度复盘",
                        key=f"deep_review_{deep_review_key}",
                        use_container_width=True,
                    ):
                        if (
                            deep_review_key
                            not in st.session_state.deep_reviews
                        ):
                            try:
                                with st.spinner(
                                    "正在综合分析当前会话的 "
                                    f"{len(session_records)} 局牌…"
                                ):
                                    st.session_state.deep_reviews[
                                        deep_review_key
                                    ] = generate_deep_review(
                                        session_records
                                    )
                            except CoachError as error:
                                st.error(
                                    f"AI深度复盘暂不可用：{error}"
                                )
                    current_review = st.session_state.deep_reviews.get(
                        deep_review_key
                    )
                    if current_review:
                        st.caption(
                            "分析范围：当前会话第 1 局至第 "
                            f"{len(session_records)} 局｜"
                            "结论可信度："
                            f"{current_review['confidence']}"
                        )
                        st.markdown(
                            "**整体打法画像：** "
                            f"{current_review['summary']}"
                        )
                        st.markdown("**反复出现的优势：**")
                        for item in current_review["strengths"]:
                            st.write(f"- {item}")
                        st.markdown("**应优先改进的问题：**")
                        for item in current_review["improvements"]:
                            st.write(f"- {item}")
                        st.markdown("**查看分析依据**")
                        for item in current_review["evidence"]:
                            st.write(f"- {item}")
                        st.markdown(
                            "**接下来 3～5 局训练计划：** "
                            f"{current_review['next_focus']}"
                        )

        with st.container(key="data_panel_area"):
            with st.expander("数据面板", expanded=False):
                metric_columns = st.columns(3)
                metric_columns[0].metric(
                    "已完成牌局",
                    training_summary["hands"],
                )
                metric_columns[1].metric(
                    "累计筹码变化",
                    training_summary["chip_change"],
                )
                metric_columns[2].metric(
                    "玩家决策次数",
                    training_summary["total_decisions"],
                )
                st.markdown(
                    f"#### {training_summary['profile_stage']}："
                    f"{training_summary['profile_name']}"
                )
                st.progress(training_summary["profile_progress"])
                st.caption(
                    "画像置信度："
                    f"{training_summary['profile_confidence']}｜"
                    f"{training_summary['profile_basis']}"
                )
                behavior_metrics = training_summary["metrics"]
                behavior_columns = st.columns(2)
                behavior_columns[0].metric(
                    "主动参与翻前牌局",
                    f"{behavior_metrics['vpip']:.0%}",
                )
                behavior_columns[1].metric(
                    "翻前主动加注",
                    f"{behavior_metrics['preflop_raise_rate']:.0%}",
                )
                behavior_columns = st.columns(2)
                behavior_columns[0].metric(
                    "受压弃牌率",
                    f"{behavior_metrics['fold_to_pressure_rate']:.0%}",
                )
                behavior_columns[1].metric(
                    "翻后主动进攻率",
                    f"{behavior_metrics['postflop_aggression_rate']:.0%}",
                )
                behavior_columns = st.columns(2)
                behavior_columns[0].metric(
                    "全下牌局率",
                    f"{behavior_metrics['all_in_hand_rate']:.0%}",
                )
                behavior_columns[1].metric(
                    "摊牌率",
                    f"{behavior_metrics['showdown_rate']:.0%}",
                )
                st.write("行动统计")
                st.write(
                    "｜".join(
                        f"{name} {count}"
                        for name, count in training_summary[
                            "action_counts"
                        ].items()
                    )
                )
                st.write("行为观察")
                for observation in training_summary["observations"]:
                    st.write(f"- {observation}")
                st.write("下一轮训练重点")
                for focus in training_summary["training_focus"]:
                    st.write(f"- {focus}")

        with st.expander(
            "行动记录",
            expanded=False,
        ):
            for entry in reversed(game.log):
                st.write(f"- {entry}")

        if game.current_hand_record:
            with st.expander(
                "高级信息｜牌局决策记录",
                expanded=False,
            ):
                st.caption(
                    "面向希望检查详细决策数据的玩家。记录用于还原"
                    "每次决策时的底池、跟注压力和公共牌，也是累计 "
                    "AI 深度复盘的事实依据。"
                )
                human_only = st.checkbox(
                    "只看我的决策",
                    value=True,
                    key=f"human_record_only_{game.hand_number}",
                )
                record_rows = readable_action_rows(
                    record_for_display(game.current_hand_record),
                    human_only=human_only,
                )
                if record_rows:
                    st.dataframe(
                        record_rows,
                        hide_index=True,
                        use_container_width=True,
                    )
                else:
                    st.info("本局还没有可展示的玩家决策。")
                if game.current_hand_record.get("result"):
                    st.caption(
                        "本局结果："
                        f"{game.current_hand_record['result']}"
                    )

with coach_column:
    if game.showdown_details and not board_reveal_pending:
        with st.container(key="showdown_area"):
            st.subheader("所有玩家牌型")
            for detail in game.showdown_details:
                st.info(detail)


def schedule_flow_transition(kind, key, delay_seconds):
    """记录截止时间后立即结束本轮渲染，避免 sleep 让整页控件变灰。"""
    if (
        st.session_state.flow_transition_kind != kind
        or st.session_state.flow_transition_key != key
    ):
        st.session_state.flow_transition_kind = kind
        st.session_state.flow_transition_key = key
        st.session_state.flow_transition_deadline = (
            time.monotonic() + delay_seconds
        )


scheduled_transition = None
if board_reveal_pending:
    scheduled_transition = (
        "reveal_board",
        (
            game.hand_number,
            game.reveal_id,
            shown_community_count,
            len(game.community_cards),
        ),
        COMMUNITY_CARD_BACK_SECONDS,
    )
elif game.all_in_runout_pending:
    scheduled_transition = (
        "deal_all_in_street",
        (game.hand_number, game.reveal_id, len(game.community_cards)),
        ALL_IN_DEAL_DELAY_SECONDS,
    )
elif getattr(game, "pending_street_advance", False):
    scheduled_transition = (
        "advance_street",
        (
            game.hand_number,
            game.street_index,
            len(game.current_hand_record.get("actions", [])),
        ),
        STREET_TRANSITION_DELAY_SECONDS,
    )
elif (
    game.status == "进行中"
    and game.turn_index not in {None, 0}
):
    scheduled_transition = (
        "ai_action",
        (
            game.hand_number,
            game.street_index,
            game.turn_index,
            len(game.current_hand_record.get("actions", [])),
        ),
        AI_ACTION_DELAY_SECONDS,
    )

if scheduled_transition:
    schedule_flow_transition(*scheduled_transition)
else:
    st.session_state.flow_transition_kind = None
    st.session_state.flow_transition_key = None
    st.session_state.flow_transition_deadline = 0.0


@st.fragment(run_every=0.15 if scheduled_transition else None)
def advance_game_flow():
    """在独立的无界面片段中推进流程，主页面始终保持正常亮度。"""
    transition_kind = st.session_state.flow_transition_kind
    if (
        not transition_kind
        or time.monotonic()
        < st.session_state.flow_transition_deadline
    ):
        return

    st.session_state.flow_transition_kind = None
    st.session_state.flow_transition_key = None
    st.session_state.flow_transition_deadline = 0.0
    if transition_kind == "reveal_board":
        st.session_state.shown_community_count = len(
            game.community_cards
        )
        st.session_state.community_flip_from = shown_community_count
    elif transition_kind == "deal_all_in_street":
        game.deal_next_all_in_street()
    elif transition_kind == "advance_street":
        game.continue_after_action()
    elif transition_kind == "ai_action":
        game.play_next_ai_turn(
            choose_tutorial_action
            if getattr(game, "tutorial_mode", False)
            else choose_persona_decision
        )
    st.rerun()


advance_game_flow()
