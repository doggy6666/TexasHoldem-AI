"""第三阶段的游戏模式定义；页面只展示难度名称，不展示内部策略细节。"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class GameMode:
    key: str
    label: str
    ai_label: str
    enabled: bool


GAME_MODES = {
    "offline": GameMode("offline", "线下对战", "默认 AI", True),
    "simple": GameMode("simple", "简单模式", "新手 AI", True),
    "advanced": GameMode("advanced", "进阶模式", "进阶 AI", True),
    "hard": GameMode("hard", "困难模式", "高手 AI", True),
    "custom": GameMode("custom", "自定义模式", "自定义 AI", True),
}

OFFLINE = "offline"
NOVICE = "novice"
ADVANCED_CONSERVATIVE = "advanced_conservative"
ADVANCED_AGGRESSIVE = "advanced_aggressive"
EXPERT = "expert"

PERSONA_LABELS = {
    OFFLINE: "默认 AI",
    NOVICE: "新手 AI",
    ADVANCED_CONSERVATIVE: "进阶 AI",
    ADVANCED_AGGRESSIVE: "进阶 AI",
    EXPERT: "高手 AI",
}


def mode_from_label(label: str) -> GameMode:
    for mode in GAME_MODES.values():
        if mode.label == label:
            return mode
    raise ValueError(f"未知游戏模式：{label}")


def public_label_for_persona(persona: str) -> str:
    return PERSONA_LABELS.get(persona, "默认 AI")


def personas_for_mode(
    mode_key: str,
    ai_count: int,
    custom_labels: list[str] | None = None,
    rng=None,
) -> list[str]:
    """为每个 AI 座位分配内部人格，页面只显示公开难度名称。"""
    if ai_count < 1:
        return []
    random_source = rng or random
    if mode_key == "offline":
        return [OFFLINE] * ai_count
    if mode_key == "simple":
        return [NOVICE] * ai_count
    if mode_key == "hard":
        return [EXPERT] * ai_count
    if mode_key == "advanced":
        if ai_count == 1:
            return [random_source.choice([ADVANCED_CONSERVATIVE, ADVANCED_AGGRESSIVE])]
        personas = [ADVANCED_CONSERVATIVE, ADVANCED_AGGRESSIVE]
        personas.extend(
            random_source.choice([ADVANCED_CONSERVATIVE, ADVANCED_AGGRESSIVE])
            for _ in range(ai_count - 2)
        )
        random_source.shuffle(personas)
        return personas
    if mode_key == "custom":
        labels = custom_labels or []
        if len(labels) != ai_count:
            raise ValueError("自定义模式必须为每个 AI 座位选择难度。")
        label_to_persona = {
            "新手 AI": NOVICE,
            "高手 AI": EXPERT,
        }
        personas = []
        for label in labels:
            if label == "进阶 AI":
                personas.append(
                    random_source.choice(
                        [ADVANCED_CONSERVATIVE, ADVANCED_AGGRESSIVE]
                    )
                )
            elif label in label_to_persona:
                personas.append(label_to_persona[label])
            else:
                raise ValueError(f"未知 AI 难度：{label}")
        return personas
    raise ValueError(f"未知游戏模式：{mode_key}")
