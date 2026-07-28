"""陪练画像：基于跨牌局行为指标形成可解释的会话级玩家画像。"""

from __future__ import annotations

from collections import Counter


ACTION_LABELS = {
    "fold": "弃牌",
    "check": "过牌",
    "call": "跟注",
    "bet": "下注",
    "raise": "加注",
    "all_in": "全下",
}
PROFILE_HAND_THRESHOLD = 8
HIGH_CONFIDENCE_HAND_THRESHOLD = 20


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def build_training_summary(completed_records: list[dict]) -> dict:
    human_actions = [
        action
        for record in completed_records
        for action in record.get("actions", [])
        if action.get("seat") == 0
    ]
    counts = Counter(action.get("action") for action in human_actions)
    hands = len(completed_records)
    chip_change = sum(
        record.get("ending_chips", {}).get(0, 0)
        - record.get("starting_chips", {}).get(0, 0)
        for record in completed_records
    )

    voluntary_preflop_hands = 0
    preflop_raise_hands = 0
    all_in_hands = 0
    showdown_hands = 0
    for record in completed_records:
        player_actions = [
            action
            for action in record.get("actions", [])
            if action.get("seat") == 0
        ]
        preflop_actions = [
            action for action in player_actions
            if str(action.get("street", "")).startswith("翻前")
        ]
        if any(
            action.get("action") in {"call", "bet", "raise", "all_in"}
            for action in preflop_actions
        ):
            voluntary_preflop_hands += 1
        if any(
            action.get("action") in {"raise", "all_in"}
            for action in preflop_actions
        ):
            preflop_raise_hands += 1
        if any(action.get("action") == "all_in" for action in player_actions):
            all_in_hands += 1
        folded = any(action.get("action") == "fold" for action in player_actions)
        if not folded and len(record.get("final_community_cards", [])) == 5:
            showdown_hands += 1

    postflop_actions = [
        action
        for action in human_actions
        if not str(action.get("street", "")).startswith("翻前")
    ]
    aggressive_postflop = sum(
        action.get("action") in {"bet", "raise", "all_in"}
        for action in postflop_actions
    )
    responsive_postflop = sum(
        action.get("action") in {"bet", "raise", "all_in", "call"}
        for action in postflop_actions
    )
    pressure_actions = [
        action
        for action in human_actions
        if action.get("amount_to_call_before", 0) > 0
    ]
    pressure_folds = sum(
        action.get("action") == "fold" for action in pressure_actions
    )

    metrics = {
        "vpip": _rate(voluntary_preflop_hands, hands),
        "preflop_raise_rate": _rate(preflop_raise_hands, hands),
        "postflop_aggression_rate": _rate(
            aggressive_postflop,
            responsive_postflop,
        ),
        "fold_to_pressure_rate": _rate(pressure_folds, len(pressure_actions)),
        "all_in_hand_rate": _rate(all_in_hands, hands),
        "showdown_rate": _rate(showdown_hands, hands),
        "postflop_decisions": len(postflop_actions),
        "pressure_decisions": len(pressure_actions),
    }

    if hands >= PROFILE_HAND_THRESHOLD:
        profile_stage = "会话级稳定画像"
    elif hands >= 4:
        profile_stage = "初步画像"
    else:
        profile_stage = "数据收集中"
    if hands >= HIGH_CONFIDENCE_HAND_THRESHOLD:
        profile_confidence = "较高"
    elif hands >= PROFILE_HAND_THRESHOLD:
        profile_confidence = "中等"
    else:
        profile_confidence = "较低"

    participation = (
        "宽松"
        if metrics["vpip"] >= 0.65
        else "谨慎" if metrics["vpip"] <= 0.35 else "选择性"
    )
    aggressive_signal = max(
        metrics["preflop_raise_rate"],
        metrics["postflop_aggression_rate"],
    )
    initiative = (
        "主动"
        if aggressive_signal >= 0.35
        else "被动" if aggressive_signal <= 0.15 else "均衡"
    )
    profile_name = (
        "等待更多数据"
        if hands < 4
        else f"{participation}{initiative}型"
    )

    observations = [
        f"自愿入池率 {metrics['vpip']:.0%}，当前起手牌参与倾向为{participation}。",
        f"翻前加注率 {metrics['preflop_raise_rate']:.0%}，"
        f"翻后主动进攻率 {metrics['postflop_aggression_rate']:.0%}。",
        f"面对需要跟注的场景共 {len(pressure_actions)} 次，"
        f"弃牌率为 {metrics['fold_to_pressure_rate']:.0%}。",
    ]
    training_focus = []
    if hands < PROFILE_HAND_THRESHOLD:
        training_focus.append(
            f"再完成 {PROFILE_HAND_THRESHOLD - hands} 局，形成会话级稳定画像。"
        )
    if metrics["vpip"] >= 0.65:
        training_focus.append("减少边缘起手牌的跟注，优先形成明确的加注或弃牌选择。")
    elif hands >= 4 and metrics["vpip"] <= 0.30:
        training_focus.append("在庄家位等有利位置适度扩大可玩起手牌范围。")
    if (
        metrics["vpip"] >= 0.40
        and metrics["preflop_raise_rate"] <= 0.12
    ):
        training_focus.append("翻前跟注明显多于加注，可减少被动入池。")
    if (
        metrics["postflop_decisions"] >= 6
        and metrics["postflop_aggression_rate"] <= 0.15
    ):
        training_focus.append("翻后主动进攻偏少，拿到优势牌时可更重视价值下注。")
    if (
        metrics["pressure_decisions"] >= 5
        and metrics["fold_to_pressure_rate"] <= 0.20
    ):
        training_focus.append("面对下注时很少弃牌，建议重点复核底池赔率与边缘跟注。")
    elif (
        metrics["pressure_decisions"] >= 5
        and metrics["fold_to_pressure_rate"] >= 0.65
    ):
        training_focus.append("面对下注时弃牌较多，可检查是否放弃了部分有赔率的继续范围。")
    if metrics["all_in_hand_rate"] >= 0.25:
        training_focus.append("全下使用较频繁，下一轮可重点控制非强牌的大底池风险。")
    if not training_focus:
        training_focus.append("当前数据未出现明显单一倾向，继续关注转牌和河牌决策质量。")

    return {
        "hands": hands,
        "chip_change": chip_change,
        "total_decisions": len(human_actions),
        "action_counts": {
            ACTION_LABELS[action]: counts[action] for action in ACTION_LABELS
        },
        "metrics": metrics,
        "profile_stage": profile_stage,
        "profile_confidence": profile_confidence,
        "profile_name": profile_name,
        "profile_progress": min(hands / PROFILE_HAND_THRESHOLD, 1.0),
        "profile_basis": (
            f"至少 {PROFILE_HAND_THRESHOLD} 局形成会话级稳定画像；"
            f"达到 {HIGH_CONFIDENCE_HAND_THRESHOLD} 局后置信度提升。"
            "画像只反映当前浏览器会话，不代表长期牌风定论。"
        ),
        "observations": observations,
        "training_focus": training_focus,
    }
