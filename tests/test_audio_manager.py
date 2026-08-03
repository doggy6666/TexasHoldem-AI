from audio_manager import _audio_url, _resolve_bgm_path


def test_bgm_uses_a_static_url_instead_of_embedding_audio_data():
    path = _resolve_bgm_path("Experience")

    assert path.is_file()
    assert _audio_url(path).startswith("/app/static/audio/")
    assert "base64" not in _audio_url(path)
