from pathlib import Path
import time

from streamlit.testing.v1 import AppTest


def test_app_starts_with_rules_and_tutorial_entry():
    # 先缓存依赖模块，再执行 app，覆盖 Streamlit 热更新时的导入方式。
    import poker.tutorial  # noqa: F401

    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)

    assert not app.exception
    assert any(expander.label == "游戏规则" for expander in app.expander)
    tutorial_button = next(
        button for button in app.button if button.label == "示例对局"
    )

    tutorial_button.click().run(timeout=15)

    assert not app.exception
    assert app.session_state.game.tutorial_mode
    assert app.session_state.active_mode_key == "tutorial"
    assert app.session_state.game.total_players == 4
    assert app.session_state.flow_transition_kind == "ai_action"

    time.sleep(1.35)
    app.run(timeout=15)

    assert not app.exception
    assert len(app.session_state.game.current_hand_record["actions"]) == 1
    assert app.session_state.game.turn_index == 0


def test_custom_random_ai_assigns_current_seats_and_hides_style_labels(
    monkeypatch,
):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)

    mode_radio = next(
        radio for radio in app.radio if radio.label == "游戏模式"
    )
    mode_radio.set_value("自定义模式").run(timeout=15)
    player_count = next(
        selectbox
        for selectbox in app.selectbox
        if selectbox.label == "总人数（players）"
    )
    player_count.set_value(4).run(timeout=15)
    button_labels = [button.label for button in app.button]
    assert button_labels.index("开始新对局（new match）") < (
        button_labels.index("以随机 AI 开始新对局")
    )
    random_button = next(
        button
        for button in app.button
        if button.label == "以随机 AI 开始新对局"
    )
    random_button.click().run(timeout=15)

    assert not app.exception
    assert app.session_state.custom_ai_randomized
    assert app.session_state.custom_ai_randomized_count == 4
    assert app.session_state.hide_active_ai_styles
    assert app.session_state.game.total_players == 4
    assert {
        player.ai_persona
        for player in app.session_state.game.players[1:]
    } <= {
        "novice",
        "advanced_conservative",
        "advanced_aggressive",
        "expert",
    }
    visible_ai_settings = [
        selectbox.label
        for selectbox in app.selectbox
        if selectbox.label.startswith("AI 座位")
    ]
    assert visible_ai_settings == []
    seat_markup = [
        markdown.value
        for markdown in app.markdown
        if 'class="player-seat"' in markdown.value
    ]
    assert len(seat_markup) == 4
    assert all('class="ai-level"' not in markup for markup in seat_markup)


def test_manual_custom_start_keeps_selected_style_visible():
    app_path = Path(__file__).parents[1] / "app.py"
    app = AppTest.from_file(str(app_path)).run(timeout=15)
    next(
        radio for radio in app.radio if radio.label == "游戏模式"
    ).set_value("自定义模式").run(timeout=15)
    seat_selectbox = next(
        selectbox
        for selectbox in app.selectbox
        if selectbox.label == "AI 座位 1"
    )
    seat_selectbox.set_value("高手 AI").run(timeout=15)
    next(
        button
        for button in app.button
        if button.label == "开始新对局（new match）"
    ).click().run(timeout=15)

    assert not app.exception
    assert not app.session_state.custom_ai_randomized
    assert app.session_state.custom_ai_randomized_count is None
    assert not app.session_state.hide_active_ai_styles
    seat_markup = [
        markdown.value
        for markdown in app.markdown
        if 'class="player-seat"' in markdown.value
    ]
    assert any('class="ai-level"' in markup for markup in seat_markup)
