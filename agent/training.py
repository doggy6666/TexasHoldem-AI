"""陪练面板：只做可验证的行为统计，不代替联网策略分析。"""

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


def build_training_summary(completed_records: list[dict]) -> dict:
    human_actions = [
        action
        for record in completed_records
        for action in record.get("actions", [])
        if action.get("seat") == 0
    ]
    counts = Counter(action.get("action") for action in human_actions)
    chip_change = sum(
        record.get("ending_chips", {}).get(0, 0)
        - record.get("starting_chips", {}).get(0, 0)
        for record in completed_records
    )
    observations = []
    total = len(human_actions)
    if total:
        if counts["all_in"] / total >= 0.2:
            observations.append("全下行动占比较高。")
        if (counts["bet"] + counts["raise"]) / total >= 0.35:
            observations.append("主动下注与加注较为频繁。")
        if counts["call"] / total >= 0.45:
            observations.append("跟注是当前最常用的应对方式。")
        if not observations:
            observations.append("当前行动分布较为均衡，需要更多牌局才能形成稳定画像。")
    else:
        observations.append("完成一局后将开始形成你的陪练数据。")
    return {
        "hands": len(completed_records),
        "chip_change": chip_change,
        "total_decisions": total,
        "action_counts": {
            ACTION_LABELS[action]: counts[action] for action in ACTION_LABELS
        },
        "observations": observations,
    }
