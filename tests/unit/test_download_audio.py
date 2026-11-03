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


def video(path, video_id=None):
    return {"id": video_id or path, "title": path, "requested_downloads": [{"filepath": path}]}


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
    assert failed == ["https://list (2 of 2 playlist items failed)"]


def test_download_audio_archive_skip_is_not_a_failure(tmp_path, fake_ydl):
    fake_ydl["https://list"] = {"entries": []}

    files, failed = download_audio(["https://list"], str(tmp_path), allow_playlists=True, archive=True)

    assert (files, failed) == ([], [])


def test_download_audio_playlist_with_broken_items_is_reported(tmp_path, fake_ydl):
    fake_ydl["https://list"] = {"entries": [video("a.webm"), None, video("b.webm")]}

    files, failed = download_audio(["https://list"], str(tmp_path), allow_playlists=True)

    assert files == ["a.webm", "b.webm"]
    assert failed == ["https://list (1 of 3 playlist items failed)"]


def test_download_audio_same_title_from_two_videos_is_a_failure(tmp_path, fake_ydl, capsys):
    fake_ydl.update({"https://a": video("song.webm", "id-a"), "https://b": video("song.webm", "id-b")})

    files, failed = download_audio(["https://a", "https://b"], str(tmp_path))

    assert files == ["song.webm"]
    assert failed == ["https://b (same title as an earlier video: song.webm)"]
    assert "--suffix" in capsys.readouterr().out


def test_download_audio_same_video_twice_is_not_a_clash(tmp_path, fake_ydl):
    fake_ydl.update({"https://a": video("song.webm", "id-a"), "https://youtu.be/a": video("song.webm", "id-a")})

    files, failed = download_audio(["https://a", "https://youtu.be/a"], str(tmp_path))

    assert (files, failed) == (["song.webm"], [])


def test_download_audio_os_error_fails_only_that_link(tmp_path, fake_ydl, capsys):
    fake_ydl.update({"https://locked": PermissionError(13, "Permission denied"), "https://ok": video("ok.webm")})

    files, failed = download_audio(["https://locked", "https://ok"], str(tmp_path))

    assert files == ["ok.webm"]
    assert failed == ["https://locked"]
    assert "Permission denied" in capsys.readouterr().out
