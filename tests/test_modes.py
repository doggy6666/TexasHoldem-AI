import random

import pytest

from agent.modes import (
    ADVANCED_AGGRESSIVE,
    ADVANCED_CONSERVATIVE,
    EXPERT,
    GAME_MODES,
    NOVICE,
    OFFLINE,
    personas_for_mode,
    public_label_for_persona,
)


def test_all_third_stage_modes_are_enabled():
    assert all(mode.enabled for mode in GAME_MODES.values())


def test_fixed_modes_assign_expected_personas():
    assert personas_for_mode("offline", 3) == [OFFLINE, OFFLINE, OFFLINE]
    assert personas_for_mode("simple", 3) == [NOVICE, NOVICE, NOVICE]
    assert personas_for_mode("hard", 3) == [EXPERT, EXPERT, EXPERT]


def test_advanced_mode_contains_both_internal_styles_at_multi_ai_table():
    personas = personas_for_mode("advanced", 3, rng=random.Random(7))

    assert len(personas) == 3
    assert ADVANCED_CONSERVATIVE in personas
    assert ADVANCED_AGGRESSIVE in personas
    assert {public_label_for_persona(persona) for persona in personas} == {"进阶 AI"}


def test_custom_mode_assigns_each_seat_and_hides_internal_advanced_style():
    personas = personas_for_mode(
        "custom",
        3,
        custom_labels=["新手 AI", "进阶 AI", "高手 AI"],
        rng=random.Random(3),
    )

    assert personas[0] == NOVICE
    assert personas[1] in {ADVANCED_CONSERVATIVE, ADVANCED_AGGRESSIVE}
    assert personas[2] == EXPERT
    assert [public_label_for_persona(persona) for persona in personas] == [
        "新手 AI",
        "进阶 AI",
        "高手 AI",
    ]


def test_custom_mode_requires_one_choice_per_ai_seat():
    with pytest.raises(ValueError):
        personas_for_mode("custom", 2, custom_labels=["新手 AI"])
