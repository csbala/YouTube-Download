import functools
import http.server
import os
import shutil
import subprocess
import sys
import threading

import pytest

import downloader

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def ffmpeg_dir():
    found = downloader.find_ffmpeg()
    if not found:
        pytest.skip("ffmpeg is not installed")
    return found


@pytest.fixture(scope="session")
def media_dir(tmp_path_factory, ffmpeg_dir):
    """A folder holding a 1-second test tone, tone.webm (Opus audio), made with the real ffmpeg."""
    folder = tmp_path_factory.mktemp("media")
    ffmpeg = shutil.which("ffmpeg", path=ffmpeg_dir)
    subprocess.run(
        [ffmpeg, "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
         "-c:a", "libopus", str(folder / "tone.webm")],
        check=True,
    )
    return folder


class AudioHandler(http.server.SimpleHTTPRequestHandler):
    # yt-dlp's generic extractor treats audio/* responses as audio-only formats
    extensions_map = {".webm": "audio/webm", "": "application/octet-stream"}

    def log_message(self, *args):
        pass


@pytest.fixture(scope="session")
def media_server(media_dir):
    """Base URL of a local HTTP server serving media_dir. No internet needed."""
    handler = functools.partial(AudioHandler, directory=str(media_dir))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture
def tone_url(media_server):
    return f"{media_server}/tone.webm"


@pytest.fixture
def run_cli(tmp_path):
    """Run downloader.py as a real subprocess, from a copy in tmp_path so the repo's cookies.txt and links.txt are never used."""
    script = tmp_path / "app" / "downloader.py"
    script.parent.mkdir()
    shutil.copy(os.path.join(REPO_ROOT, "downloader.py"), script)

    def run(*args):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        return subprocess.run([sys.executable, str(script), *map(str, args)],
                              capture_output=True, text=True, encoding="utf-8", env=env, timeout=120)
    return run
