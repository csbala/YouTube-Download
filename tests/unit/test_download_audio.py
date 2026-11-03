import pytest
import yt_dlp

import downloader
from downloader import download_audio


class FakeYoutubeDL:
    """Stands in for yt_dlp.YoutubeDL. `script` maps each URL to an info dict, or to an exception to raise."""
    script = {}

    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download):
        result = self.script[url]
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def fake_ydl(monkeypatch):
    FakeYoutubeDL.script = {}
    # Options are covered by test_ydl_options.py; building them needs the real YoutubeDL class
    monkeypatch.setattr(downloader, "build_ydl_options", lambda *args, **kwargs: {})
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    return FakeYoutubeDL.script


def video(path):
    return {"requested_downloads": [{"filepath": path}]}


def test_download_audio_collects_files_from_every_link(tmp_path, fake_ydl):
    fake_ydl.update({"https://a": video("a.webm"), "https://b": video("b.webm")})

    files, failed = download_audio(["https://a", "https://b"], str(tmp_path))

    assert files == ["a.webm", "b.webm"]
    assert failed == []


def test_download_audio_counts_download_errors_and_continues(tmp_path, fake_ydl):
    fake_ydl.update({"https://bad": yt_dlp.utils.DownloadError("Video unavailable"), "https://ok": video("ok.webm")})

    files, failed = download_audio(["https://bad", "https://ok"], str(tmp_path))

    assert files == ["ok.webm"]
    assert failed == ["https://bad"]


def test_download_audio_creates_missing_folder(tmp_path, fake_ydl):
    folder = tmp_path / "new" / "folder"

    download_audio([], str(folder))

    assert folder.is_dir()


def test_download_audio_empty_playlist_is_a_failure(tmp_path, fake_ydl):
    fake_ydl["https://list"] = {"entries": [None, None]}

    files, failed = download_audio(["https://list"], str(tmp_path), allow_playlists=True)

    assert files == []
    assert failed == ["https://list"]


def test_download_audio_archive_skip_is_not_a_failure(tmp_path, fake_ydl):
    fake_ydl["https://list"] = {"entries": []}

    files, failed = download_audio(["https://list"], str(tmp_path), allow_playlists=True, archive=True)

    assert (files, failed) == ([], [])
