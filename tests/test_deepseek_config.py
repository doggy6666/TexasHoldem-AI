"""Keep local Streamlit secrets ahead of stale environment variables."""

from agent.deepseek_client import configured_api_key


def test_streamlit_secret_takes_precedence(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "old-key")
    monkeypatch.setattr(
        "agent.deepseek_client.st.secrets",
        {"DEEPSEEK_API_KEY": "new-key"},
    )

    assert configured_api_key() == "new-key"


def test_environment_key_is_fallback(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "environment-key")
    monkeypatch.setattr("agent.deepseek_client.st.secrets", {})

    assert configured_api_key() == "environment-key"
