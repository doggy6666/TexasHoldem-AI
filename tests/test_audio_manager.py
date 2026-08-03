from audio_manager import PUBLIC_AUDIO_BASE_URL, _audio_url, _resolve_bgm_path


def test_bgm_uses_a_public_url_instead_of_embedding_audio_data():
    path = _resolve_bgm_path("Experience")

    assert path.is_file()
    assert _audio_url(path).startswith(f"{PUBLIC_AUDIO_BASE_URL}/")
    assert "base64" not in _audio_url(path)
