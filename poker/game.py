"""2–4 人无限注德州扑克流程：位置、下注、全下与边池。"""

from __future__ import annotations

import random
from copy import deepcopy
from dataclasses import dataclass, field

from agent.default_agent import choose_action
from poker.cards import Card, Deck
from poker.hand import best_hand, describe_score
from poker.history import (
    capture_action_before,
    complete_action_record,
    finalize_hand_record,
    start_hand_record,
)
from poker.player import Player
from poker.pots import Pot, build_pots
from poker.table import next_active_seat


STREETS = ("翻牌圈（flop）", "转牌圈（turn）", "河牌圈（river）")
AVATAR_NICKNAMES = {
    1: "桃桃",
    2: "凛音",
    3: "橙夏",
    4: "夜璃",
    5: "青禾",
    6: "白雪",
}


@dataclass
class PokerGame:
    total_players: int = 2
    starting_chips: int = 1000
    small_blind: int = 10
    big_blind: int = 20
    players: list[Player] = field(init=False)
    deck: Deck = field(init=False)
    community_cards: list[Card] = field(default_factory=list)
    pot: int = 0
    pots: list[Pot] = field(default_factory=list)
    current_bet: int = 0
    last_raise_size: int = 20
    street_index: int = -1
    status: str = "等待开始"
    dealer_index: int = -1
    small_blind_index: int | None = None
    big_blind_index: int | None = None
    turn_index: int | None = None
    acted: set[int] = field(default_factory=set)
    log: list[str] = field(default_factory=list)
    result: str | None = None
    reveal_id: int = 0
    all_in_runout_pending: bool = False
    hand_number: int = 0
    showdown_details: list[str] = field(default_factory=list)
    last_actions: dict[int, str] = field(default_factory=dict)
    last_ai_sources: dict[int, str] = field(default_factory=dict)
    current_hand_record: dict = field(default_factory=dict)
    completed_hand_records: list[dict] = field(default_factory=list)
    skipped_to_result: bool = False
    fast_forward_chip_changes: dict[int, int] = field(default_factory=dict)
    pending_street_advance: bool = False
    tutorial_mode: bool = False
    all_in_showdown_revealed: bool = False

    def __post_init__(self) -> None:
        if not 2 <= self.total_players <= 4:
            raise ValueError("总人数必须为 2 至 4 人。")
        self.players = [Player("你", self.starting_chips, seat=0)]
        avatar_ids = random.sample(range(1, 7), self.total_players - 1)
        self.players.extend(
            Player(
                AVATAR_NICKNAMES[avatar_ids[index - 1]],
                self.starting_chips,
                seat=index,
                avatar_id=avatar_ids[index - 1],
            )
            for index in range(1, self.total_players)
        )

    @property
    def human(self) -> Player:
        return self.players[0]

    @property
    def street_name(self) -> str:
        return "翻前圈（pre-flop）" if self.street_index < 0 else STREETS[self.street_index]

    @property
    def turn_is_human(self) -> bool:
        return self.turn_index == 0

    @property
    def ended_without_showdown(self) -> bool:
        return bool(
            self.result
            and "因其他玩家全部弃牌" in self.result
        )

    @property
    def minimum_raise_to(self) -> int:
        return max(self.current_bet * 2, self.current_bet + self.last_raise_size)

    def amount_to_call(self, player_index: int) -> int:
        return max(0, self.current_bet - self.players[player_index].street_bet)

    def can_raise(self, player_index: int) -> bool:
        player = self.players[player_index]
        return player.street_bet + player.chips >= self.minimum_raise_to

    def is_out(self, player_index: int) -> bool:
        player = self.players[player_index]
        return player.chips <= 0 and (self.status == "已结束" or not player.hole_cards)

    def start_hand(self) -> None:
        active = self._funded_indices()
        if len(active) < 2:
            raise ValueError("至少两名玩家有筹码才能继续。")
        starting_chips = {
            index: player.chips for index, player in enumerate(self.players)
        }
        self.dealer_index = self._next_funded(self.dealer_index)
        self.small_blind_index = self._next_funded(self.dealer_index)
        self.big_blind_index = self._next_funded(self.small_blind_index)
        if len(active) == 2:  # 单挑例外：庄家同时是小盲。
            self.small_blind_index = self.dealer_index
            self.big_blind_index = self._next_funded(self.dealer_index)
        self.deck = Deck()
        self.community_cards = []
        self.pot = 0
        self.pots = []
        self.current_bet = 0
        self.last_raise_size = self.big_blind
        self.street_index = -1
        self.result = None
        self.showdown_details = []
        self.last_actions = {}
        self.last_ai_sources = {}
        self.skipped_to_result = False
        self.fast_forward_chip_changes = {}
        self.pending_street_advance = False
        self.log = []
        self.acted = set()
        self.all_in_runout_pending = False
        self.all_in_showdown_revealed = False
        self.hand_number += 1
        for player in self.players:
            player.reset_for_hand()
            if player.chips > 0:
                player.hole_cards = self.deck.deal(2)
        self._post_blind(self.small_blind_index, self.small_blind, "小盲注（small blind）")
        self._post_blind(self.big_blind_index, self.big_blind, "大盲注（big blind）")
        self.current_bet = self.players[self.big_blind_index].street_bet
        self.status = "进行中"
        self.turn_index = self._next_in_hand(self.big_blind_index)
        self.log.append(f"第 {self.hand_number} 局开始，庄家是{self.players[self.dealer_index].name}。")
        self.current_hand_record = start_hand_record(self, starting_chips)
        self.reveal_id += 1

    def human_action(self, action: str, amount: int = 0) -> None:
        if self.status != "进行中" or not self.turn_is_human:
            raise ValueError("当前不是你的行动回合。")
        self._apply_action(0, action, amount)

    def play_next_ai_turn(self, decision_provider=None) -> None:
        """只执行一个 AI 行动，让界面能逐条展示行动过程。"""
        if self.status != "进行中" or self.turn_index in {None, 0}:
            return
        provider = decision_provider or choose_action
        decision = provider(self, self.turn_index)
        if len(decision) == 3:
            action, amount, source = decision
        else:
            action, amount = decision
            source = "默认 AI 已接管"
        if not hasattr(self, "last_ai_sources"):
            self.last_ai_sources = {}
        self.last_ai_sources[self.turn_index] = source
        self._apply_action(self.turn_index, action, amount)

    def continue_after_action(self) -> None:
        """在界面留出动作展示时间后，再进入下一街或摊牌。"""
        if not self.pending_street_advance:
            return
        self.pending_street_advance = False
        self._advance_street()

    def fast_forward_after_human_fold(
        self,
        max_steps: int = 300,
        decision_provider=None,
    ) -> None:
        """真人弃牌后用本地 AI 快速完成牌局，并补全展示所需公共牌。"""
        if self.status != "进行中" or not self.human.folded:
            raise ValueError("只有真人已弃牌且牌局仍在进行时才能跳过。")
        self.log.append("你选择跳过剩余过程，AI 对局将快速结算。")
        for _ in range(max_steps):
            if self.status == "已结束":
                break
            if self.all_in_runout_pending:
                self.deal_next_all_in_street()
            elif self.pending_street_advance:
                self.continue_after_action()
            elif self.turn_index not in {None, 0}:
                # 默认使用本地 AI；教程可以注入只跟注或过牌的固定策略。
                self.play_next_ai_turn(decision_provider)
            else:
                raise RuntimeError("跳过结算遇到无法继续的牌局状态。")
        else:
            raise RuntimeError("跳过结算超过最大行动次数。")

        self._complete_board_for_skipped_display()
        starting_chips = self.current_hand_record.get("starting_chips", {})
        self.fast_forward_chip_changes = {
            index: player.chips - starting_chips.get(index, player.chips)
            for index, player in enumerate(self.players)
        }
        self.skipped_to_result = True

    def _complete_board_for_skipped_display(self) -> None:
        """牌局已结算后补全五张公共牌，仅用于跳过结果展示。"""
        dealt_extra_cards = False
        while len(self.community_cards) < 5:
            count = 3 if not self.community_cards else 1
            self.community_cards.extend(
                self.deck.deal(min(count, 5 - len(self.community_cards)))
            )
            dealt_extra_cards = True
        self.street_index = 2
        if dealt_extra_cards:
            self.reveal_id += 1
            self.log.append("已补全五张公共牌用于展示，不改变已经完成的结算。")
        self._build_showdown_details()
        if self.current_hand_record:
            self.current_hand_record["final_community_cards"] = [
                str(card) for card in self.community_cards
            ]
            self.current_hand_record["showdown"] = list(self.showdown_details)
            if (
                self.completed_hand_records
                and self.completed_hand_records[-1].get("hand_number")
                == self.hand_number
            ):
                self.completed_hand_records[-1] = deepcopy(
                    self.current_hand_record
                )

    def _apply_action(self, index: int, action: str, amount: int = 0) -> None:
        player = self.players[index]
        required = self.amount_to_call(index)
        action_record = capture_action_before(self, index, action, amount)
        if action == "fold":
            player.folded = True
            self._record_action(index, "弃牌（fold）")
        elif action == "check":
            if required:
                raise ValueError("当前已有下注，不能过牌。")
            self.acted.add(index)
            self._record_action(index, "过牌（check）")
        elif action == "call":
            if required == 0:
                raise ValueError("当前无需跟注，请选择过牌或加注。")
            if player.chips < required:
                raise ValueError("筹码不足以跟注，请选择全下。")
            self._contribute(index, required)
            self.acted.add(index)
            self._record_action(index, f"跟注（call）至 {self.current_bet}")
        elif action in {"bet", "raise"}:
            if action == "bet" and self.current_bet:
                raise ValueError("已有下注时请选择加注。")
            if action == "raise" and not self.current_bet:
                raise ValueError("尚未下注时请选择下注。")
            target = self._validate_target(index, action, amount)
            previous = self.current_bet
            self._contribute(index, target - player.street_bet)
            self.current_bet = player.street_bet
            self.last_raise_size = self.current_bet if previous == 0 else self.current_bet - previous
            self.acted = {index}
            label = "下注（bet）" if action == "bet" else "加注（raise）"
            self._record_action(index, f"{label}至 {target}")
        elif action == "all_in":
            if player.chips <= 0:
                raise ValueError("该玩家已无可投入筹码。")
            target = player.street_bet + player.chips
            previous = self.current_bet
            self._contribute(index, player.chips)
            if target > previous:
                self.current_bet = target
                self.last_raise_size = target if previous == 0 else target - previous
                self.acted = {index}
            else:
                self.acted.add(index)
            self._record_action(index, f"全下（all in）至 {target}")
        else:
            raise ValueError("不支持的行动。")
        complete_action_record(self, index, action_record)
        self._after_action(index)

    def _after_action(self, last_index: int) -> None:
        live = self._live_indices()
        if len(live) == 1:
            winner = self.players[live[0]]
            winner.chips += self.pot
            self.result = f"{winner.name}因其他玩家全部弃牌，赢得底池 {self.pot}。"
            self._build_showdown_details()
            self.status = "已结束"
            self.turn_index = None
            self.log.append(self.result)
            finalize_hand_record(self)
            return
        actionable = self._actionable_indices()
        if not actionable:
            self._return_uncalled_excess()
            self._schedule_all_in_runout()
            return
        if len(actionable) == 1 and any(self.players[index].all_in for index in live):
            remaining_index = actionable[0]
            remaining_has_responded = (
                remaining_index in self.acted
                and self.players[remaining_index].street_bet == self.current_bet
            )
            if remaining_has_responded:
                self._return_uncalled_excess()
                self._schedule_all_in_runout()
                return
        if self._round_is_complete(actionable):
            self._return_uncalled_excess()
            self.pending_street_advance = True
            self.turn_index = None
            return
        self.turn_index = self._next_actionable(last_index)

    def _round_is_complete(self, actionable: list[int]) -> bool:
        return all(index in self.acted and self.players[index].street_bet == self.current_bet for index in actionable)

    def _advance_street(self) -> None:
        if self.street_index == 2:
            self._showdown()
            return
        self.street_index += 1
        self.community_cards.extend(self.deck.deal(3 if self.street_index == 0 else 1))
        self.current_bet = 0
        self.last_raise_size = self.big_blind
        self.acted = set()
        self.last_actions = {}
        self.last_ai_sources = {}
        for player in self.players:
            player.street_bet = 0
        self.turn_index = self._next_in_hand(self.dealer_index)
        self.log.append(f"进入{self.street_name}。")
        self.reveal_id += 1

    def _schedule_all_in_runout(self) -> None:
        self.pots = build_pots(self.players)
        self.all_in_showdown_revealed = True
        if len(self.community_cards) >= 5:
            self._showdown()
            return
        self.all_in_runout_pending = True
        self.turn_index = None
        self.log.append("所有未弃牌玩家均已全下，剩余公共牌将逐街发出。")

    def deal_next_all_in_street(self) -> None:
        if not self.all_in_runout_pending:
            return
        if len(self.community_cards) >= 5:
            self.all_in_runout_pending = False
            self._showdown()
            return
        count = 3 if not self.community_cards else 1
        self.community_cards.extend(self.deck.deal(count))
        self.street_index = 0 if len(self.community_cards) == 3 else len(self.community_cards) - 3
        self.reveal_id += 1
        self.log.append(f"全下发出{self.street_name}。")
        if len(self.community_cards) == 5:
            self.all_in_runout_pending = False
            self._showdown()

    def best_score_for(self, index: int):
        return best_hand(self.players[index].hole_cards + self.community_cards)

    def _showdown(self) -> None:
        self._return_uncalled_excess()
        # 投入额可能在全下跑牌期间因退还未跟注筹码而变化，摊牌时必须重建。
        self.pots = build_pots(self.players)
        summaries: list[str] = []
        for number, pot in enumerate(self.pots, start=1):
            candidates = list(pot.eligible_seats)
            scores = {index: self.best_score_for(index)[0] for index in candidates}
            winning_score = max(scores.values())
            winners = [index for index in candidates if scores[index] == winning_score]
            share, remainder = divmod(pot.amount, len(winners))
            payouts = {index: share for index in winners}
            remainder_winners = self._remainder_order(winners)[:remainder]
            for index in remainder_winners:
                payouts[index] += 1
            for index in winners:
                self.players[index].chips += payouts[index]
            winner_names = "、".join(self.players[index].name for index in winners)
            pot_name = "主池" if number == 1 else f"第 {number - 1} 边池"
            winning_hand = describe_score(winning_score)
            if len(winners) == 1:
                summaries.append(
                    f"{winner_names}获胜（{winning_hand}），赢得{pot_name} {pot.amount} 筹码。"
                )
            else:
                payout_text = "、".join(
                    f"{self.players[index].name}获得 {payouts[index]} 筹码"
                    for index in winners
                )
                summaries.append(
                    f"{winner_names}并列获胜（{winning_hand}），平分{pot_name} "
                    f"{pot.amount} 筹码：{payout_text}。"
                )
        self.result = " ".join(summaries)
        self._build_showdown_details()
        self.status = "已结束"
        self.turn_index = None
        self.log.append(self.result)
        finalize_hand_record(self)

    def _build_showdown_details(self) -> None:
        """对局结束后为所有入局玩家生成清晰的手牌与牌型说明。"""
        details: list[str] = []
        for player in self.players:
            if not player.hole_cards:
                continue
            if player.folded:
                details.append(f"{player.name}｜已弃牌")
                continue
            if self.ended_without_showdown:
                details.append(
                    f"{player.name}｜其他玩家均已弃牌，手牌未公开"
                )
                continue
            cards = "、".join(str(card) for card in player.hole_cards)
            if len(player.hole_cards) + len(self.community_cards) >= 5:
                score, _ = best_hand(player.hole_cards + self.community_cards)
                description = describe_score(score)
            else:
                description = "未进入摊牌，公共牌不足以组成五张牌"
            state = "，已弃牌" if player.folded else ""
            details.append(f"{player.name}｜手牌：{cards}｜{description}{state}")
        self.showdown_details = details

    def _return_uncalled_excess(self) -> None:
        """退还唯一最高投入者未被任何其他玩家匹配的部分。"""
        contributors = [player for player in self.players if player.hand_contribution > 0]
        if len(contributors) < 2:
            return
        ordered = sorted(contributors, key=lambda player: player.hand_contribution, reverse=True)
        highest, second_highest = ordered[0], ordered[1].hand_contribution
        if highest.hand_contribution <= second_highest:
            return
        refund = highest.hand_contribution - second_highest
        highest.hand_contribution -= refund
        highest.street_bet = max(0, highest.street_bet - refund)
        highest.chips += refund
        highest.all_in = highest.chips == 0
        self.pot -= refund
        self.current_bet = max((player.street_bet for player in self.players if not player.folded), default=0)
        self.log.append(f"{highest.name}未被跟注的筹码 {refund} 已退还。")

    def _validate_target(self, index: int, action: str, target: int) -> int:
        player = self.players[index]
        minimum = self.big_blind if action == "bet" else self.minimum_raise_to
        maximum = player.street_bet + player.chips
        if maximum < minimum:
            raise ValueError("筹码不足以完成最小下注/加注，请选择全下。")
        if target < minimum:
            raise ValueError(f"最小金额为 {minimum}。")
        if target > maximum:
            raise ValueError("下注金额不能超过现有筹码。")
        return target

    def _post_blind(self, index: int, amount: int, label: str) -> None:
        self._contribute(index, amount)
        # 盲注是强制投入，不算玩家在当前下注轮中的主动行动。
        self.log.append(f"{self.players[index].name}投入{label} {self.players[index].street_bet}。")

    def _record_action(self, index: int, action_text: str) -> None:
        if not hasattr(self, "last_actions"):
            self.last_actions = {}
        self.last_actions[index] = action_text
        self.log.append(f"{self.players[index].name}{action_text}。")

    def _contribute(self, index: int, amount: int) -> None:
        player = self.players[index]
        actual = min(amount, player.chips)
        player.chips -= actual
        player.street_bet += actual
        player.hand_contribution += actual
        player.all_in = player.chips == 0
        self.pot += actual

    def _funded_indices(self) -> list[int]:
        return [index for index, player in enumerate(self.players) if player.chips > 0]

    def _live_indices(self) -> list[int]:
        return [index for index, player in enumerate(self.players) if player.hole_cards and not player.folded]

    def _actionable_indices(self) -> list[int]:
        return [index for index in self._live_indices() if not self.players[index].all_in]

    def _next_funded(self, start: int) -> int:
        return next_active_seat(self.players, start)

    def _next_in_hand(self, start: int) -> int:
        for offset in range(1, len(self.players) + 1):
            index = (start + offset) % len(self.players)
            player = self.players[index]
            if player.hole_cards and not player.folded and not player.all_in:
                return index
        raise ValueError("没有可行动的玩家。")

    def _next_actionable(self, start: int) -> int:
        return self._next_in_hand(start)

    def _remainder_order(self, winners: list[int]) -> list[int]:
        ordered = [(self.dealer_index + offset) % len(self.players) for offset in range(1, len(self.players) + 1)]
        return [index for index in ordered if index in winners]
