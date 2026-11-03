"""Full runs against real YouTube. Opt-in: pytest -m e2e (needs internet, Node.js and ffmpeg).

These use the real repo files, including cookies.txt if present, exactly as a user would.
"""

import os
import subprocess
import sys

import pytest

from yt_audio.tools import SystemToolLocator

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
VIDEO_URL = "https://youtu.be/Y3D-c5ZJswI"  # short public track, the repo's example link
MISSING_URL = "https://www.youtube.com/watch?v=xxxxxxxxxxx"

pytestmark = pytest.mark.skipif(SystemToolLocator().node_path() is None, reason="Node.js is needed for YouTube downloads")


def run(*args, timeout=600):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([*map(str, args)], cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", env=env, timeout=timeout)


@pytest.fixture
def music_dir(tmp_path):
    return tmp_path / "e2e"


def audio_files(folder, ext):
    return [f for f in os.listdir(folder) if f.endswith(ext)]


def test_youtube_mp3_download(music_dir):
    if SystemToolLocator().ffmpeg_dir() is None:
        pytest.skip("ffmpeg is needed for mp3")

    result = run(sys.executable, "downloader.py", "download", music_dir, VIDEO_URL)

    assert result.returncode == 0, result.stdout + result.stderr
    [track] = audio_files(music_dir, ".mp3")
    assert os.path.getsize(music_dir / track) > 100_000


def test_youtube_webm_download_needs_no_ffmpeg(music_dir):
    result = run(sys.executable, "downloader.py", "download", music_dir, VIDEO_URL, "--format", "webm")

    assert result.returncode == 0, result.stdout + result.stderr
    assert len(audio_files(music_dir, ".webm")) == 1


def test_youtube_unavailable_video_exits_1(music_dir):
    result = run(sys.executable, "downloader.py", "download", music_dir, MISSING_URL)

    assert result.returncode == 1
    assert f"FAILED: {MISSING_URL}" in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="the download-music skill scripts are PowerShell on Windows")
def test_skill_download_script(music_dir):
    script = os.path.join(".claude", "skills", "download-music", "scripts", "download.ps1")

    result = run("powershell", "-ExecutionPolicy", "Bypass", "-File", script, "-Url", VIDEO_URL, "-Folder", music_dir, "-Format", "webm")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "NEW FILE:" in result.stdout
