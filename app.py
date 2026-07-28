"""TexasHoldem AI：2–4 人桌、四种模式与 DeepSeek AI。"""

import base64
import os
import random
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
AVATAR_DIR = Path(__file__).parent / "assets" / "avatars"
COMMUNITY_CARD_BACK_SECONDS = 0.7
AI_ACTION_DELAY_SECONDS = 1.25
ALL_IN_DEAL_DELAY_SECONDS = 0.6
STREET_TRANSITION_DELAY_SECONDS = 0.75
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


def mark_custom_ai_as_manual():
    """玩家手动改动任一座位后，不再视作随机隐藏配置。"""
    st.session_state.custom_ai_randomized = False
    st.session_state.custom_ai_randomized_count = None

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


custom_ai_labels = []
with st.sidebar:
    mode_options = list(GAME_MODES.values())
    selected_mode_index = next(
        (
            index
            for index, mode in enumerate(mode_options)
            if mode.key == st.session_state.selected_mode_key
        ),
        0,
    )
    selected_mode_label = st.radio(
        "游戏模式",
        [mode.label for mode in mode_options],
        index=selected_mode_index,
        disabled=game.status == "进行中",
    )
    selected_mode = next(
        mode for mode in mode_options if mode.label == selected_mode_label
    )
    st.session_state.selected_mode_key = selected_mode.key
    st.subheader(f"{selected_mode.label}设置")
    st.caption(f"AI 对手：{selected_mode.ai_label}")
    selected_count = st.selectbox("总人数（players）", [2, 3, 4], index=game.total_players - 2, disabled=game.status == "进行中")
    random_start_requested = False
    manual_start_available = True
    if selected_mode.key == "custom":
        secret_random_match = bool(
            st.session_state.active_mode_key == "custom"
            and st.session_state.hide_active_ai_styles
        )
        if secret_random_match:
            manual_start_available = False
            st.caption("当前为随机 AI 对局，所有 AI 风格全程保密。")
        else:
            for seat in range(1, selected_count):
                custom_ai_labels.append(
                    st.selectbox(
                        f"AI 座位 {seat}",
                        ["新手 AI", "进阶 AI", "高手 AI"],
                        key=f"custom_ai_{seat}",
                        disabled=game.status == "进行中",
                        on_change=mark_custom_ai_as_manual,
                    )
                )
    manual_start_requested = False
    if manual_start_available:
        manual_start_requested = st.button(
            "开始新对局（new match）",
            disabled=not selected_mode.enabled,
            use_container_width=True,
        )
    if selected_mode.key == "custom":
        random_start_requested = st.button(
            "以随机 AI 开始新对局",
            use_container_width=True,
            help=(
                "按当前人数秘密随机分配新手、进阶或高手 AI，"
                "并立即开始新对局。"
            ),
        )
        if random_start_requested:
            custom_ai_labels = [
                random.choice(["新手 AI", "进阶 AI", "高手 AI"])
                for _ in range(selected_count - 1)
            ]
            st.session_state.custom_ai_randomized = True
            st.session_state.custom_ai_randomized_count = selected_count
        if (
            secret_random_match
            and game.status != "进行中"
            and st.button(
                "返回手动自定义",
                use_container_width=True,
            )
        ):
            st.session_state.training_records.extend(
                completed_training_records(
                    getattr(game, "completed_hand_records", [])
                )
            )
            mark_custom_ai_as_manual()
            st.session_state.game = PokerGame(
                total_players=selected_count
            )
            st.session_state.hide_active_ai_styles = False
            st.session_state.shown_community_count = 0
            st.session_state.community_flip_from = None
            st.rerun()
    if random_start_requested or manual_start_requested:
        if not random_start_requested:
            mark_custom_ai_as_manual()
        st.session_state.training_records.extend(
            completed_training_records(
                getattr(game, "completed_hand_records", [])
            )
        )
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
        st.session_state.hide_active_ai_styles = random_start_requested
        st.session_state.shown_community_count = 0
        st.session_state.community_flip_from = None
        st.rerun()
    api_configured = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    if selected_mode.key == "offline":
        st.caption("线下对战：仅使用默认 AI，不调用 API，不消耗 Token")
    else:
        st.caption(f"DeepSeek API：{'已配置' if api_configured else '未配置，将使用本地兜底'}")
    st.caption("盲注：小盲 10｜大盲 20")
    with st.expander("游戏规则", expanded=False):
        st.markdown(GAME_RULES_MARKDOWN)
    if getattr(game, "tutorial_mode", False):
        st.caption("当前牌桌：固定四人示例对局（不调用联网 AI）")
    if st.button(
        "示例对局",
        disabled=game.status == "进行中",
        use_container_width=True,
        help="进入固定四人教学牌局，不调用 DeepSeek。",
    ):
        st.session_state.training_records.extend(
            completed_training_records(
                getattr(game, "completed_hand_records", [])
            )
        )
        st.session_state.game = create_tutorial_game()
        st.session_state.active_mode_key = "tutorial"
        st.session_state.hide_active_ai_styles = False
        st.session_state.shown_community_count = 0
        st.session_state.community_flip_from = None
        st.rerun()

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
if getattr(game, "tutorial_mode", False):
    st.info(
        "示例对局：你固定持有 A♠、K♠。轮到你时先点击“实时策略提示”，"
        "再根据提示完成翻牌前、翻牌圈、转牌圈和河牌圈；教程 AI 只会跟注或过牌。"
    )

columns = st.columns(game.total_players)
ended_without_showdown = getattr(
    game,
    "ended_without_showdown",
    bool(game.result and "因其他玩家全部弃牌" in game.result),
)
for index, player in enumerate(game.players):
    with columns[index]:
        marker = " 👑庄家" if index == game.dealer_index else ""
        if index == 0 or st.session_state.hide_active_ai_styles:
            public_name = player.name
        else:
            public_name = (
                f'{player.name}<span class="ai-level">'
                f'{"教程 AI" if getattr(game, "tutorial_mode", False) else ("默认 AI" if getattr(game, "last_ai_sources", {}).get(index) == "默认 AI 已接管" else public_label_for_persona(getattr(player, "ai_persona", NOVICE)))}'
                "</span>"
            )
        is_out = game.is_out(index)
        if index == 0:
            visible_cards = cards_html(player.hole_cards) if player.hole_cards else card_backs_html()
            avatar_html = ""
        elif (
            (
                game.status == "已结束"
                and not board_reveal_pending
                and not ended_without_showdown
            )
            or getattr(game, "all_in_showdown_revealed", False)
        ):
            visible_cards = (
                cards_html(player.hole_cards)
                if not player.folded
                else card_backs_html()
            )
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

if (
    game.status == "进行中"
    and game.human.folded
    and not board_reveal_pending
):
    st.info("你已弃牌，正在继续观看 AI 对局；也可以直接跳过剩余过程。")
    _, skip_column, _ = st.columns([1, 1.3, 1])
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
                    # 普通牌局保持无参数调用，兼容热更新前创建的旧对象。
                    game.fast_forward_after_human_fold()
            except (RuntimeError, ValueError) as error:
                st.error(f"暂时无法快速结算：{error}")
            else:
                st.session_state.shown_community_count = len(
                    game.community_cards
                )
                st.session_state.community_flip_from = 0
                st.rerun()
    st.caption(
        "快速结算使用本地默认 AI，不额外调用联网模型；"
        "结算后会补齐五张公共牌，并公开所有未弃牌 AI 的手牌。"
    )

st.subheader("公共牌（community cards）")
if board_reveal_pending:
    new_card_count = len(game.community_cards) - shown_community_count
    visible_board = (
        cards_html(game.community_cards[:shown_community_count], empty="")
        + card_backs_html(new_card_count, "new-card")
    )
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
    tutorial_is_active = getattr(game, "tutorial_mode", False)
    coaching_is_online = st.session_state.active_mode_key != "offline"
    if tutorial_is_active:
        tutorial_tip_key = f"tutorial|{decision_cache_key(game)}"
        st.warning("教程任务：先查看实时策略提示，再选择本轮行动。")
        if st.button(
            "实时策略提示",
            key=f"strategy_tip_{tutorial_tip_key}",
        ):
            st.session_state.strategy_tips[tutorial_tip_key] = (
                tutorial_strategy_tip(game)
            )
        current_tip = st.session_state.strategy_tips.get(tutorial_tip_key)
        if current_tip:
            amount_text = (
                f"，建议总额至 {current_tip['amount_to']}"
                if current_tip["amount_to"] is not None
                else ""
            )
            st.info(
                f"建议：{current_tip['recommended_action']}{amount_text}\n\n"
                f"依据：{current_tip['reason']}\n\n"
                f"注意：{current_tip['risk']}"
            )
            st.caption("这是固定牌面的本地教学提示，不调用 DeepSeek，也不消耗 Token。")
    elif coaching_is_online:
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
            probability_model = current_tip.get("probability_model", {})
            probability_columns = st.columns(5)
            probability_columns[0].metric(
                "基础牌面胜率",
                f"{probability_model.get('win_probability', 0):.1%}",
            )
            probability_columns[1].metric(
                "结合行动参考胜率",
                f"{probability_model.get('action_adjusted_win_probability', 0):.1%}",
            )
            probability_columns[2].metric(
                "对手牌力更强概率",
                f"{probability_model.get('opponent_stronger_probability', 0):.1%}",
            )
            probability_columns[3].metric(
                "平局概率",
                f"{probability_model.get('tie_probability', 0):.1%}",
            )
            probability_columns[4].metric(
                "综合获胜机会",
                f"{probability_model.get('average_pot_share', 0):.1%}",
            )
            action_confidence = probability_model.get(
                "action_adjustment_confidence",
                0,
            )
            confidence_label = (
                "较高"
                if action_confidence >= 0.45
                else ("中等" if action_confidence >= 0.2 else "较低")
            )
            st.caption(
                f"概率模型：{probability_model.get('samples', 0)} 次蒙特卡洛抽样。"
                "基础胜率按剩余未知牌随机模拟；"
                f"参考胜率结合本局 {probability_model.get('action_evidence_count', 0)} "
                f"次对手公开行动温和调整，参考可信度为{confidence_label}，"
                "不会读取真实手牌；"
                "“综合获胜机会”表示重复相同局面时预计平均能分到的底池比例，"
                "平局只计算你能分得的部分。联网 AI 会再结合对手公开行动进行判断。"
            )
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

if game.result and not board_reveal_pending:
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
        st.error("你已输光筹码，本场对战结束。")
    eligible_for_next = (
        game.human.chips > 0
        and len([player for player in game.players if player.chips > 0]) >= 2
    )
    if getattr(game, "tutorial_mode", False):
        st.success(
            "示例对局已完成。现在请在侧边栏选择游戏模式、总人数和 AI 难度，"
            "再点击“开始新对局”进入正式对战。"
        )
    else:
        _, next_hand_column, _ = st.columns([1, 1.3, 1])
        with next_hand_column:
            with st.container(border=True):
                st.markdown("#### 继续本场对战")
                if st.button(
                    "再来一局（next hand）",
                    disabled=not eligible_for_next,
                    use_container_width=True,
                ):
                    game.start_hand()
                    st.session_state.shown_community_count = 0
                    st.session_state.community_flip_from = None
                    st.rerun()
                if not eligible_for_next:
                    if game.human.chips <= 0:
                        st.caption(
                            "你已输光筹码，可从侧边栏开始新对局。"
                        )
                    else:
                        st.caption(
                            "AI 对手已输光筹码，可从侧边栏开始新对局。"
                        )

if game.showdown_details and not board_reveal_pending:
    st.subheader("所有玩家牌型（showdown hands）")
    for detail in game.showdown_details:
        st.info(detail)

session_records = completed_training_records(
    st.session_state.training_records
    + game.completed_hand_records
)

if game.result and not board_reveal_pending:
    st.subheader("AI深度复盘")
    if st.session_state.active_mode_key in {"offline", "tutorial"}:
        st.caption("线下对战和示例对局不启用联网 AI 深度复盘。")
    elif len(session_records) < MIN_DEEP_REVIEW_HANDS:
        st.info(
            f"当前已完成 {len(session_records)} 局；"
            f"至少完成 {MIN_DEEP_REVIEW_HANDS} 局后，"
            "才能进行有依据的累计深度复盘。"
        )
    else:
        deep_review_key = review_cache_key(session_records)
        if st.button("AI深度复盘", key=f"deep_review_{deep_review_key}"):
            if deep_review_key not in st.session_state.deep_reviews:
                try:
                    with st.spinner(
                        f"正在综合分析当前会话的 {len(session_records)} 局牌…"
                    ):
                        st.session_state.deep_reviews[deep_review_key] = (
                            generate_deep_review(session_records)
                        )
                except CoachError as error:
                    st.error(f"AI深度复盘暂不可用：{error}")
        current_review = st.session_state.deep_reviews.get(deep_review_key)
        if current_review:
            st.caption(
                f"分析范围：当前会话第 1 局至第 {len(session_records)} 局｜"
                f"结论可信度：{current_review['confidence']}"
            )
            st.markdown(
                f"**整体打法画像：** {current_review['summary']}"
            )
            st.markdown("**反复出现的优势：**")
            for item in current_review["strengths"]:
                st.write(f"- {item}")
            st.markdown("**应优先改进的问题：**")
            for item in current_review["improvements"]:
                st.write(f"- {item}")
            with st.expander("查看分析依据", expanded=False):
                for item in current_review["evidence"]:
                    st.write(f"- {item}")
            st.markdown(
                f"**接下来 3～5 局训练计划：** "
                f"{current_review['next_focus']}"
            )

with st.expander("行动记录（action history）", expanded=False):
    for entry in reversed(game.log):
        st.write(f"- {entry}")

training_summary = build_training_summary(session_records)
# Streamlit 热更新可能保留旧模块对象；为旧会话补齐新版画像字段，避免页面崩溃。
training_hands = training_summary.get("hands", 0)
training_summary.setdefault(
    "profile_stage",
    "会话级稳定画像" if training_hands >= 8 else (
        "初步画像" if training_hands >= 4 else "数据收集中"
    ),
)
training_summary.setdefault("profile_name", "等待更多数据")
training_summary.setdefault(
    "profile_progress",
    min(training_hands / 8, 1.0),
)
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
training_summary.setdefault("training_focus", ["继续完成牌局以形成训练重点。"])
with st.expander("数据面板", expanded=False):
    metric_columns = st.columns(3)
    metric_columns[0].metric("已完成牌局", training_summary["hands"])
    metric_columns[1].metric("累计筹码变化", training_summary["chip_change"])
    metric_columns[2].metric("玩家决策次数", training_summary["total_decisions"])
    st.markdown(
        f"#### {training_summary['profile_stage']}："
        f"{training_summary['profile_name']}"
    )
    st.progress(training_summary["profile_progress"])
    st.caption(
        f"画像置信度：{training_summary['profile_confidence']}｜"
        f"{training_summary['profile_basis']}"
    )
    behavior_metrics = training_summary["metrics"]
    behavior_columns = st.columns(3)
    behavior_columns[0].metric("主动参与翻前牌局", f"{behavior_metrics['vpip']:.0%}")
    behavior_columns[1].metric(
        "翻前主动加注",
        f"{behavior_metrics['preflop_raise_rate']:.0%}",
    )
    behavior_columns[2].metric(
        "受压弃牌率",
        f"{behavior_metrics['fold_to_pressure_rate']:.0%}",
    )
    postflop_columns = st.columns(3)
    postflop_columns[0].metric(
        "翻后主动进攻率",
        f"{behavior_metrics['postflop_aggression_rate']:.0%}",
    )
    postflop_columns[1].metric(
        "全下牌局率",
        f"{behavior_metrics['all_in_hand_rate']:.0%}",
    )
    postflop_columns[2].metric(
        "摊牌率",
        f"{behavior_metrics['showdown_rate']:.0%}",
    )
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
    st.write("下一轮训练重点")
    for focus in training_summary["training_focus"]:
        st.write(f"- {focus}")

if game.current_hand_record:
    with st.expander(
        "高级信息｜牌局决策记录",
        expanded=False,
    ):
        st.caption(
            "面向希望检查详细决策数据的玩家。记录用于还原每次决策时的"
            "底池、跟注压力和公共牌，也是累计 AI 深度复盘的事实依据。"
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
                f"本局结果：{game.current_hand_record['result']}"
            )

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
