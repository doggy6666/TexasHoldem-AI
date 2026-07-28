"""TexasHoldem AI：2–4 人桌、四种模式与 DeepSeek AI。"""

import base64
import os
import time
from pathlib import Path

import streamlit as st

from agent.coach import (
    CoachError,
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


st.set_page_config(page_title="TexasHoldem AI", page_icon="🂡", layout="wide")
st.markdown("""<style>
[data-testid="stAppViewBlockContainer"] {padding-top:1.25rem !important;}
[data-testid="stHeader"] {height:2rem;}
.poker-card {display:inline-block; min-width:42px; margin:2px; padding:7px 9px;
border:1px solid #cbd5e1; border-radius:7px; background:#fff; font-size:1.35rem;
font-weight:700; text-align:center; box-shadow:0 1px 2px #cbd5e1;}
.poker-card.red {color:#dc2626;} .poker-card.black {color:#111827;}
.poker-card.back {min-width:42px; height:48px; padding:0;
border:3px solid #f8fafc; outline:1px solid #1d4ed8;
background:
  repeating-linear-gradient(45deg, transparent 0 4px, rgba(255,255,255,.28) 4px 6px),
  repeating-linear-gradient(-45deg, transparent 0 4px, rgba(255,255,255,.18) 4px 6px),
  #2563eb;}
.poker-card.new-card {animation:card-back-arrive .35s cubic-bezier(.2,1.3,.4,1);}
.poker-card.dealt {animation:card-flip .55s cubic-bezier(.2,.8,.3,1);}
.community-board {height:64px; display:flex; align-items:center; gap:4px; box-sizing:border-box;}
.hand-slot {height:64px; display:flex; align-items:center; gap:4px; box-sizing:border-box;}
.player-seat {width:100%;}
.seat-header {height:155px; display:grid; grid-template-columns:minmax(0, 1fr) 144px;
align-items:start; box-sizing:border-box;}
.seat-name {margin:0 0 14px; font-size:1.5rem; line-height:1.4; font-weight:700; color:#262730;}
.ai-level {display:inline-block; margin-left:8px; padding:2px 7px; border-radius:999px;
background:#e0f2fe; color:#075985; font-size:.75rem; font-weight:700; vertical-align:middle;}
.seat-label {margin-bottom:2px; font-size:.875rem; color:#4b5563;}
.seat-chips {font-size:1.75rem; line-height:1.4; color:#31333f;}
.seat-avatar {width:144px; height:144px;}
.seat-avatar img {display:block; width:144px; height:144px; object-fit:cover; border-radius:8px;}
.seat-contribution {height:32px; box-sizing:border-box; font-size:.875rem; color:#808495;}
.action-card {height:44px; box-sizing:border-box; margin-top:8px; padding:10px 12px;
border:2px solid #93c5fd; border-radius:10px; background:#eff6ff; color:#1e3a8a;
font-weight:700; animation:action-snap .48s cubic-bezier(.2,1.4,.4,1);}
.action-card.waiting {border-color:#cbd5e1; background:#f8fafc; color:#64748b;}
.action-card.danger {border-color:#fca5a5; background:#fef2f2; color:#b91c1c;}
.action-card.acting {border-color:#f59e0b; background:#fffbeb; color:#92400e;
animation:action-pulse .8s ease-in-out infinite alternate;}
.action-card.human-turn {
animation:action-wiggle .7s ease-in-out infinite, action-pulse .8s ease-in-out infinite alternate;}
@keyframes action-snap {
  0% {transform:translateY(-12px) scale(.94) rotate(-1deg);}
  65% {transform:translateY(3px) scale(1.03) rotate(.4deg);}
  100% {transform:translateY(0) scale(1) rotate(0);}
}
@keyframes action-pulse {
  from {box-shadow:0 0 0 0 rgba(245,158,11,.15);}
  to {box-shadow:0 0 0 4px rgba(245,158,11,.32);}
}
@keyframes action-wiggle {
  0%, 100% {transform:translateX(0) rotate(0);}
  25% {transform:translateX(-4px) rotate(-.45deg);}
  75% {transform:translateX(4px) rotate(.45deg);}
}
@keyframes card-back-arrive {
  from {transform:translateX(-18px) scale(.9);}
  to {transform:translateX(0) scale(1);}
}
@keyframes card-flip {
  0% {transform:rotateY(90deg) scale(.92);}
  65% {transform:rotateY(-8deg) scale(1.04);}
  100% {transform:rotateY(0) scale(1);}
}
</style>""", unsafe_allow_html=True)
st.title("TexasHoldem AI｜德州扑克智能对战")
st.caption("第四阶段：多人 AI 对战、实时策略提示、深度复盘与陪练记录")

if "game" not in st.session_state:
    st.session_state.game = PokerGame()
game: PokerGame = st.session_state.game
if "selected_mode_key" not in st.session_state:
    st.session_state.selected_mode_key = "simple"
if "active_mode_key" not in st.session_state:
    st.session_state.active_mode_key = "simple"
if "shown_community_count" not in st.session_state:
    st.session_state.shown_community_count = len(game.community_cards)
if "community_flip_from" not in st.session_state:
    st.session_state.community_flip_from = None
if "strategy_tips" not in st.session_state:
    st.session_state.strategy_tips = {}
if "deep_reviews" not in st.session_state:
    st.session_state.deep_reviews = {}
AVATAR_DIR = Path(__file__).parent / "assets" / "avatars"
COMMUNITY_CARD_BACK_SECONDS = 1.0
AI_ACTION_DELAY_SECONDS = 2.0
ALL_IN_DEAL_DELAY_SECONDS = 2.0
STREET_TRANSITION_DELAY_SECONDS = 2.0

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


def cards_html(cards, empty="尚未发牌", animate_from=None):
    if not cards:
        return empty
    rendered = []
    for index, card in enumerate(cards):
        animation_class = " dealt" if animate_from is not None and index >= animate_from else ""
        color_class = "red" if card.suit in {"♥", "♦"} else "black"
        rendered.append(f'<span class="poker-card {color_class}{animation_class}">{card}</span>')
    return "".join(rendered)


def card_backs_html(count=2, extra_class=""):
    return "".join(
        f'<span class="poker-card back {extra_class}" aria-label="隐藏的牌"></span>'
        for _ in range(count)
    )


def community_stage_name(card_count):
    return {3: "翻牌（flop）", 4: "转牌（turn）", 5: "河牌（river）"}.get(card_count, "公共牌")


@st.cache_data(show_spinner=False)
def avatar_data_uri(path: str):
    image_bytes = Path(path).read_bytes()
    return f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}"


selected_mode = GAME_MODES[st.session_state.selected_mode_key]
if game.status != "进行中":
    st.subheader("选择游戏模式")
    mode_columns = st.columns(len(GAME_MODES))
    for mode_column, mode in zip(mode_columns, GAME_MODES.values()):
        with mode_column:
            st.markdown(f"#### {mode.label}")
            st.write(mode.ai_label)
            if st.button(
                f"选择{mode.label}",
                key=f"select_mode_{mode.key}",
                disabled=st.session_state.selected_mode_key == mode.key,
                use_container_width=True,
            ):
                st.session_state.selected_mode_key = mode.key
                st.rerun()
    selected_mode = GAME_MODES[st.session_state.selected_mode_key]
    st.info(f"当前模式：{selected_mode.label}｜AI 对手：{selected_mode.ai_label}")


custom_ai_labels = []
with st.sidebar:
    st.subheader(f"{selected_mode.label}设置")
    st.caption(f"AI 对手：{selected_mode.ai_label}")
    selected_count = st.selectbox("总人数（players）", [2, 3, 4], index=game.total_players - 2, disabled=game.status == "进行中")
    if selected_mode.key == "custom":
        for seat in range(1, selected_count):
            custom_ai_labels.append(
                st.selectbox(
                    f"AI 座位 {seat}",
                    ["新手 AI", "进阶 AI", "高手 AI"],
                    key=f"custom_ai_{seat}",
                    disabled=game.status == "进行中",
                )
            )
    if st.button(
        "开始新对局（new match）",
        disabled=not selected_mode.enabled,
        use_container_width=True,
    ):
        new_game = PokerGame(total_players=selected_count)
        assigned_personas = personas_for_mode(
            selected_mode.key,
            selected_count - 1,
            custom_labels=custom_ai_labels if selected_mode.key == "custom" else None,
        )
        for seat, persona in enumerate(assigned_personas, start=1):
            new_game.players[seat].ai_persona = persona
        new_game.start_hand()
        st.session_state.game = new_game
        st.session_state.active_mode_key = selected_mode.key
        st.session_state.shown_community_count = 0
        st.session_state.community_flip_from = None
        st.rerun()
    if game.status != "等待开始":
        eligible_for_next = game.status == "已结束" and game.human.chips > 0 and len([p for p in game.players if p.chips > 0]) >= 2
        if st.button("再来一局（next hand）", disabled=not eligible_for_next, use_container_width=True):
            game.start_hand()
            st.session_state.shown_community_count = 0
            st.session_state.community_flip_from = None
            st.rerun()
    api_configured = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    if selected_mode.key == "offline":
        st.caption("线下对战：仅使用默认 AI，不调用 API，不消耗 Token")
    else:
        st.caption(f"DeepSeek API：{'已配置' if api_configured else '未配置，将使用本地兜底'}")
    st.caption("盲注：小盲 10｜大盲 20")

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
st.info(f"状态：{game.status}｜{game.street_name}｜庄家（dealer）：{dealer_name}｜底池（pot）：{game.pot}")

columns = st.columns(game.total_players)
for index, player in enumerate(game.players):
    with columns[index]:
        marker = " 👑庄家" if index == game.dealer_index else ""
        public_name = (
            player.name
            if index == 0
            else (
                f'{player.name}<span class="ai-level">'
                f'{"默认 AI" if getattr(game, "last_ai_sources", {}).get(index) == "默认 AI 已接管" else public_label_for_persona(getattr(player, "ai_persona", NOVICE))}'
                "</span>"
            )
        )
        is_out = game.is_out(index)
        if index == 0:
            visible_cards = cards_html(player.hole_cards) if player.hole_cards else card_backs_html()
            avatar_html = ""
        elif game.status == "已结束" and not player.folded and not board_reveal_pending:
            visible_cards = cards_html(player.hole_cards)
            avatar_id = getattr(player, "avatar_id", None) or ((index - 1) % 6 + 1)
            avatar_src = avatar_data_uri(str(AVATAR_DIR / f"ai_{avatar_id}.png"))
            avatar_html = f'<img src="{avatar_src}" alt="{player.name}的头像">'
        else:
            visible_cards = card_backs_html()
            avatar_id = getattr(player, "avatar_id", None) or ((index - 1) % 6 + 1)
            avatar_src = avatar_data_uri(str(AVATAR_DIR / f"ai_{avatar_id}.png"))
            avatar_html = f'<img src="{avatar_src}" alt="{player.name}的头像">'
        last_actions = getattr(game, "last_actions", {})
        if is_out:
            action_text, action_style = "已离场（out）", "danger"
        elif player.folded:
            action_text, action_style = "已弃牌（folded）", "danger"
        elif player.all_in:
            action_text = last_actions.get(index, "全下（all in）")
            action_style = ""
        elif game.turn_index == index:
            if index == 0:
                action_text, action_style = "👉 轮到你行动（your turn）！", "acting human-turn"
            else:
                action_text, action_style = "🂡 正在思考（thinking）…", "acting"
        elif index in last_actions:
            action_text = f"最近行动：{last_actions[index]}"
            action_style = ""
        elif game.status == "进行中" and player.hole_cards:
            action_text, action_style = "未行动（not acted）", "waiting"
        else:
            action_text, action_style = "等待开局", "waiting"
        st.markdown(
            f"""<div class="player-seat">
  <div class="seat-header">
    <div>
      <div class="seat-name">{public_name}{marker}</div>
      <div class="seat-label">筹码（chips）</div>
      <div class="seat-chips">{player.chips}</div>
    </div>
    <div class="seat-avatar">{avatar_html}</div>
  </div>
  <div class="seat-contribution">本局投入：{player.hand_contribution}｜本轮下注：{player.street_bet}</div>
  <div class="hand-slot"><span>手牌：</span>{visible_cards}</div>
  <div class="action-card {action_style}">{action_text}</div>
</div>""",
            unsafe_allow_html=True,
        )

st.subheader("公共牌（community cards）")
if board_reveal_pending:
    new_card_count = len(game.community_cards) - shown_community_count
    visible_board = (
        cards_html(game.community_cards[:shown_community_count], empty="")
        + card_backs_html(new_card_count, "new-card")
    )
    stage_being_dealt = community_stage_name(len(game.community_cards))
    st.info(f"正在发出{stage_being_dealt}：牌背展示后翻开…")
elif game.community_cards:
    visible_board = cards_html(game.community_cards, animate_from=community_flip_from)
else:
    visible_board = "尚未发出公共牌"
st.markdown(f'<div class="community-board">{visible_board}</div>', unsafe_allow_html=True)

if game.pots:
    st.caption(
        "｜".join(
            f"{'主池' if i == 0 else f'第 {i} 边池'}：{pot.amount} 筹码"
            for i, pot in enumerate(game.pots)
        )
    )

if game.status == "进行中" and game.turn_is_human and not board_reveal_pending:
    st.divider()
    st.subheader("你的行动（your action）")
    coaching_is_online = st.session_state.active_mode_key != "offline"
    if coaching_is_online:
        tip_key = decision_cache_key(game)
        if st.button("实时策略提示", key=f"strategy_tip_{tip_key}"):
            if tip_key not in st.session_state.strategy_tips:
                try:
                    with st.spinner("正在分析当前决策…"):
                        st.session_state.strategy_tips[tip_key] = generate_realtime_tip(game)
                except CoachError as error:
                    st.error(f"实时策略提示暂不可用：{error}")
        current_tip = st.session_state.strategy_tips.get(tip_key)
        if current_tip:
            amount_text = (
                f"，建议总额至 {current_tip['amount_to']}"
                if current_tip["amount_to"] is not None
                else ""
            )
            st.info(
                f"建议：{current_tip['recommended_action']}{amount_text}\n\n"
                f"依据：{current_tip['reason']}\n\n"
                f"风险：{current_tip['risk']}"
            )
    else:
        st.caption("线下对战不启用联网实时策略提示。")
    to_call = game.amount_to_call(0)
    if to_call == 0:
        is_opening_bet = game.current_bet == 0
        action_name = "bet" if is_opening_bet else "raise"
        action_label = "下注（bet）" if is_opening_bet else "加注（raise）"
        minimum = game.big_blind if is_opening_bet else game.minimum_raise_to
        st.caption("你可以过牌（check），或继续下注施压。")
    else:
        action_name, action_label, minimum = "raise", "加注（raise）", game.minimum_raise_to
        st.warning(f"当前需跟注（call）{to_call}。")
    max_total = game.human.street_bet + game.human.chips
    can_size_bet = max_total >= minimum
    amount = st.number_input(f"{action_label}总额（to）", min_value=minimum, max_value=max(minimum, max_total), value=minimum, step=game.big_blind, disabled=not can_size_bet)
    buttons = st.columns(4)
    if buttons[0].button("弃牌（fold）", use_container_width=True):
        game.human_action("fold")
        st.rerun()
    if to_call == 0:
        if buttons[1].button("过牌（check）", use_container_width=True):
            game.human_action("check")
            st.rerun()
    elif game.human.chips >= to_call:
        if buttons[1].button(f"跟注（call）至 {game.current_bet}", use_container_width=True):
            game.human_action("call")
            st.rerun()
    else:
        buttons[1].button("跟注不足，请全下", disabled=True, use_container_width=True)
    if buttons[2].button(action_label, disabled=not can_size_bet, use_container_width=True):
        game.human_action(action_name, int(amount))
        st.rerun()
    if buttons[3].button(
        f"全下（all in）{game.human.chips}",
        type="primary",
        disabled=game.human.chips == 0,
        use_container_width=True,
    ):
        game.human_action("all_in")
        st.rerun()

if game.all_in_runout_pending and not board_reveal_pending:
    next_street = "翻牌（flop）" if not game.community_cards else ("转牌（turn）" if len(game.community_cards) == 3 else "河牌（river）")
    st.info(f"全下后自动发牌：即将发出{next_street}…")
    time.sleep(ALL_IN_DEAL_DELAY_SECONDS)
    game.deal_next_all_in_street()
    st.rerun()

if game.result and not board_reveal_pending:
    if "你获胜" in game.result:
        st.success(game.result)
    else:
        st.error(game.result)
    if game.human.chips <= 0:
        st.error("你已输光（out of chips），本场对战结束。")

if game.showdown_details and not board_reveal_pending:
    st.subheader("所有玩家牌型（showdown hands）")
    for detail in game.showdown_details:
        st.info(detail)

if game.result and not board_reveal_pending:
    st.subheader("AI深度复盘")
    if st.session_state.active_mode_key == "offline":
        st.caption("线下对战不启用联网 AI 深度复盘。")
    else:
        deep_review_key = review_cache_key(game)
        if st.button("AI深度复盘", key=f"deep_review_{deep_review_key}"):
            if deep_review_key not in st.session_state.deep_reviews:
                try:
                    with st.spinner("正在生成本局复盘…"):
                        st.session_state.deep_reviews[deep_review_key] = generate_deep_review(game)
                except CoachError as error:
                    st.error(f"AI深度复盘暂不可用：{error}")
        current_review = st.session_state.deep_reviews.get(deep_review_key)
        if current_review:
            st.markdown(f"**本局总结：** {current_review['summary']}")
            st.markdown("**做得好的地方：**")
            for item in current_review["strengths"]:
                st.write(f"- {item}")
            st.markdown("**可以改进的地方：**")
            for item in current_review["improvements"]:
                st.write(f"- {item}")
            st.markdown(f"**下一局训练重点：** {current_review['next_focus']}")

with st.expander("行动记录（action history）", expanded=True):
    for entry in reversed(game.log):
        st.write(f"- {entry}")

if game.current_hand_record:
    with st.expander("结构化牌局记录", expanded=False):
        st.json(record_for_display(game.current_hand_record))

training_summary = build_training_summary(game.completed_hand_records)
with st.expander("陪练面板", expanded=bool(training_summary["hands"])):
    metric_columns = st.columns(3)
    metric_columns[0].metric("已完成牌局", training_summary["hands"])
    metric_columns[1].metric("累计筹码变化", training_summary["chip_change"])
    metric_columns[2].metric("玩家决策次数", training_summary["total_decisions"])
    st.write("行动统计")
    st.write(
        "｜".join(
            f"{name} {count}"
            for name, count in training_summary["action_counts"].items()
        )
    )
    st.write("行为观察")
    for observation in training_summary["observations"]:
        st.write(f"- {observation}")

if board_reveal_pending:
    time.sleep(COMMUNITY_CARD_BACK_SECONDS)
    st.session_state.shown_community_count = len(game.community_cards)
    st.session_state.community_flip_from = shown_community_count
    st.rerun()

# 最后一个动作先展示，再进入下一街，避免被流程切换覆盖。
if getattr(game, "pending_street_advance", False) and not board_reveal_pending:
    st.markdown(
        '<div class="action-card acting">本阶段行动完成，准备进入下一阶段…</div>',
        unsafe_allow_html=True,
    )
    time.sleep(STREET_TRANSITION_DELAY_SECONDS)
    game.continue_after_action()
    st.rerun()

# 每次刷新只执行一个 AI 行动，玩家可以逐条观察行动记录并及时响应加注。
if (
    game.status == "进行中"
    and game.turn_index not in {None, 0}
    and not game.all_in_runout_pending
    and not board_reveal_pending
):
    time.sleep(AI_ACTION_DELAY_SECONDS)
    game.play_next_ai_turn(choose_persona_decision)
    st.rerun()
