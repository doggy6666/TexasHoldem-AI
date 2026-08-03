"""Browser helpers for local BGM playback and volume controls."""

from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import quote

import streamlit.components.v1 as components


RUNTIME_VERSION = 3
STATIC_AUDIO_DIR = Path(__file__).parent / "static" / "audio"
AUDIO_SEARCH_DIRS = (STATIC_AUDIO_DIR,)
BGM_TRACKS = {
    "Experience": "Ludovico Einaudi - Experience.mp3",
    "Way Down We Go": "Kaleo - Way Down We Go.mp3",
    "Dangerous": "Royal Deluxe - Dangerous.mp3",
    "Run": "OneRepublic - Run.mp3",
    "Stitches": "Shawn Mendes - Stitches.mp3",
}
BGM_IDENTIFIERS = {
    "Experience": ("Ludovico Einaudi", "Experience"),
    "Way Down We Go": ("Kaleo", "Way Down We Go"),
    "Dangerous": ("Royal Deluxe", "Dangerous"),
    "Run": ("OneRepublic", "Run"),
    "Stitches": ("Shawn Mendes", "Stitches"),
}


def _normalized_filename(value: str) -> str:
    """Ignore ordering punctuation, spaces, and case in local audio names."""
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _resolve_bgm_path(track_name: str) -> Path:
    if not track_name:
        return STATIC_AUDIO_DIR / ""
    exact_path = STATIC_AUDIO_DIR / BGM_TRACKS.get(track_name, "")
    if exact_path.is_file():
        return exact_path
    artist, title = BGM_IDENTIFIERS.get(track_name, (track_name, track_name))
    artist_key = _normalized_filename(artist)
    title_key = _normalized_filename(title)
    for search_dir in AUDIO_SEARCH_DIRS:
        if not search_dir.is_dir():
            continue
        for candidate in search_dir.iterdir():
            if not candidate.is_file() or candidate.suffix.lower() not in {
                ".mp3",
                ".wav",
                ".ogg",
                ".m4a",
            }:
                continue
            filename_key = _normalized_filename(candidate.stem)
            if artist_key in filename_key and title_key in filename_key:
                return candidate
    return exact_path


def _audio_url(path: Path) -> str:
    """Use Streamlit static hosting instead of embedding audio in every rerun."""
    if not path.is_file():
        return ""
    relative_path = path.relative_to(STATIC_AUDIO_DIR).as_posix()
    return f"/app/static/audio/{quote(relative_path)}"


def render_audio(
    *,
    track_names: tuple[str, ...],
    cycle_tracks: bool,
    playlist_id: str,
    volume: float,
    muted: bool,
) -> None:
    """Render the persistent BGM player and its music controls."""
    tracks = [
        {"id": track_name, "src": _audio_url(_resolve_bgm_path(track_name))}
        for track_name in track_names
    ]
    payload = {
        "tracks": tracks,
        "cycle": cycle_tracks,
        "playlistId": playlist_id,
        "volume": max(0.0, min(1.0, volume)),
        "muted": muted,
    }
    config = json.dumps(payload, ensure_ascii=True)
    components.html(
        f"""
<style>
html,body{{margin:0;padding:0;background:transparent;overflow:hidden}}
#controls{{height:58px;display:flex;align-items:center;gap:8px;padding:0 4px;font-family:Segoe UI,sans-serif}}
#toggle{{position:relative;width:42px;height:42px;border:1px solid #00e7f0;border-radius:50%;color:#eaffff;background:#12525d;font-size:18px;cursor:pointer}}
#toggle:hover{{color:#e9ef3a;background:#1b6e77}}
#toggle.muted{{opacity:.52}}
#toggle.muted::after{{content:"/";position:absolute;inset:0;display:grid;place-items:center;color:#ff879a;font-size:30px;font-weight:700;line-height:1;pointer-events:none}}
#volume{{width:0;opacity:0;pointer-events:none;accent-color:#18d8df;cursor:pointer;transition:width .18s ease,opacity .18s ease}}
#audio-group{{display:flex;align-items:center;gap:8px}}
#audio-group:hover #volume{{width:118px;opacity:1;pointer-events:auto}}
</style>
<audio id="bgm" autoplay></audio>
<div id="controls"><div id="audio-group"><button id="toggle" title="音乐播放/静音">🎵</button><input id="volume" type="range" min="5" max="100" value="35" title="音量"></div></div>
<script>
const config = {config};
const bgm = document.getElementById('bgm');
const toggle = document.getElementById('toggle');
const volume = document.getElementById('volume');
const settingsVersion = '8';
if (window.localStorage.getItem('texas-holdem-audio-settings-version') !== settingsVersion) {{
  window.localStorage.removeItem('texas-holdem-audio-volume');
  window.localStorage.removeItem('texas-holdem-audio-user-volume');
  window.localStorage.removeItem('texas-holdem-audio-muted');
  window.localStorage.removeItem('texas-holdem-audio-track-id');
  window.localStorage.removeItem('texas-holdem-audio-position');
  window.localStorage.removeItem('texas-holdem-audio-playlist-order');
  window.localStorage.setItem('texas-holdem-audio-settings-version', settingsVersion);
}}
const savedVolumeRaw = window.localStorage.getItem('texas-holdem-audio-volume');
const savedVolume = Number(savedVolumeRaw);
const savedMuted = window.localStorage.getItem('texas-holdem-audio-muted') === 'true';
const userSetVolume = window.localStorage.getItem('texas-holdem-audio-user-volume') === 'true';
const hasSavedVolume = userSetVolume
  && savedVolumeRaw !== null
  && savedVolumeRaw.trim() !== ''
  && Number.isFinite(savedVolume);
const effectivePercent = hasSavedVolume
  ? Math.min(100, Math.max(5, savedVolume))
  : Math.max(5, config.volume * 100);
const effectiveVolume = effectivePercent / 100;
let muted = savedMuted || config.muted;
const tracks = config.tracks.filter((track) => track.src);
const trackById = new Map(tracks.map((track) => [track.id, track]));
const trackStorageKey = 'texas-holdem-audio-track-id';
const positionStorageKey = 'texas-holdem-audio-position';
const orderStorageKey = 'texas-holdem-audio-playlist-order';
const playlistIdStorageKey = 'texas-holdem-audio-playlist-id';
if (config.cycle && window.localStorage.getItem(playlistIdStorageKey) !== config.playlistId) {{
  window.localStorage.removeItem(trackStorageKey);
  window.localStorage.removeItem(positionStorageKey);
  window.localStorage.removeItem(orderStorageKey);
  window.localStorage.setItem(playlistIdStorageKey, config.playlistId);
}}
const previousTrack = window.localStorage.getItem(trackStorageKey);
const savedPosition = Number(window.localStorage.getItem(positionStorageKey));
let playlistOrder = [];
let playlistIndex = 0;
let currentTrackId = null;
volume.value = Math.round(effectivePercent);
toggle.textContent = '🎵';
toggle.classList.toggle('muted', muted);
bgm.loop = false;
bgm.volume = effectiveVolume;
bgm.muted = muted;
function shuffle(trackIds) {{
  const shuffled = [...trackIds];
  for (let index = shuffled.length - 1; index > 0; index -= 1) {{
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [shuffled[index], shuffled[swapIndex]] = [shuffled[swapIndex], shuffled[index]];
  }}
  return shuffled;
}}
function readSavedOrder() {{
  try {{
    const stored = JSON.parse(window.localStorage.getItem(orderStorageKey) || '[]');
    const valid = stored.length === tracks.length
      && stored.every((trackId) => trackById.has(trackId));
    return valid ? stored : [];
  }} catch (_) {{
    return [];
  }}
}}
function createPlaylistOrder(lastTrackId) {{
  const order = shuffle(tracks.map((track) => track.id));
  if (order.length > 1 && order[0] === lastTrackId) {{
    [order[0], order[1]] = [order[1], order[0]];
  }}
  return order;
}}
function savePlaylistState() {{
  window.localStorage.setItem(orderStorageKey, JSON.stringify(playlistOrder));
}}
function startAudio() {{
  if (currentTrackId) {{
    bgm.play().catch(() => {{}});
  }}
}}
function savePlaybackPosition() {{
  if (currentTrackId && !bgm.paused && Number.isFinite(bgm.currentTime)) {{
    window.localStorage.setItem(trackStorageKey, currentTrackId);
    window.localStorage.setItem(positionStorageKey, String(bgm.currentTime));
  }}
}}
function loadTrack(trackId, resumePosition = 0) {{
  const track = trackById.get(trackId);
  if (!track) {{ return; }}
  currentTrackId = track.id;
  window.localStorage.setItem(trackStorageKey, track.id);
  bgm.src = track.src;
  const restore = () => {{
    if (resumePosition > 0 && Number.isFinite(bgm.duration) && resumePosition < bgm.duration) {{
      bgm.currentTime = resumePosition;
    }}
    startAudio();
  }};
  if (bgm.readyState >= 1) {{
    restore();
  }} else {{
    bgm.addEventListener('loadedmetadata', restore, {{once: true}});
  }}
}}
function selectInitialTrack() {{
  if (!tracks.length) {{ return null; }}
  if (!config.cycle) {{ return tracks[0].id; }}
  playlistOrder = readSavedOrder();
  if (!playlistOrder.length || !playlistOrder.includes(previousTrack)) {{
    playlistOrder = createPlaylistOrder(previousTrack);
    playlistIndex = 0;
  }} else {{
    playlistIndex = playlistOrder.indexOf(previousTrack);
  }}
  savePlaylistState();
  return playlistOrder[playlistIndex];
}}
function playNextTrack() {{
  if (!config.cycle || !currentTrackId) {{ return; }}
  if (playlistIndex < playlistOrder.length - 1) {{
    playlistIndex += 1;
  }} else {{
    playlistOrder = createPlaylistOrder(currentTrackId);
    playlistIndex = 0;
  }}
  savePlaylistState();
  window.localStorage.setItem(positionStorageKey, '0');
  loadTrack(playlistOrder[playlistIndex]);
}}
bgm.addEventListener('ended', playNextTrack);
const playbackRetry = window.setInterval(() => {{
  if (!bgm.paused) {{
    window.clearInterval(playbackRetry);
    return;
  }}
  startAudio();
}}, 700);
toggle.addEventListener('click', () => {{
  if (bgm.paused) {{
    muted = false;
    bgm.muted = false;
    toggle.textContent = '🎵';
    toggle.classList.remove('muted');
    window.localStorage.setItem('texas-holdem-audio-muted', 'false');
    startAudio();
    return;
  }}
  muted = !muted;
  bgm.muted = muted;
  toggle.textContent = '🎵';
  toggle.classList.toggle('muted', muted);
  window.localStorage.setItem('texas-holdem-audio-muted', String(muted));
  startAudio();
}});
volume.addEventListener('input', () => {{
  bgm.volume = Number(volume.value) / 100;
  window.localStorage.setItem('texas-holdem-audio-volume', volume.value);
  window.localStorage.setItem('texas-holdem-audio-user-volume', 'true');
  if (Number(volume.value) > 0 && muted) {{
    muted = false;
    bgm.muted = false;
    toggle.textContent = '🎵';
    toggle.classList.remove('muted');
    window.localStorage.setItem('texas-holdem-audio-muted', 'false');
  }}
  startAudio();
}});
const initialTrackId = selectInitialTrack();
if (initialTrackId) {{
  const resumePosition = previousTrack === initialTrackId ? savedPosition : 0;
  loadTrack(initialTrackId, resumePosition);
  window.setInterval(savePlaybackPosition, 250);
  window.addEventListener('pagehide', savePlaybackPosition);
}}
</script>
""",
        height=64,
        scrolling=False,
    )
