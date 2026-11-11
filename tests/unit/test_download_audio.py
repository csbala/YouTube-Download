import pytest
import yt_dlp

from yt_audio import download_audio
from yt_audio.download import DownloadInterrupted, FileClaim, FileOwnershipRegistry, LinkOutcome
from yt_audio.events import LinkDone, LinkErrored, LinkStarted, TitleClash
from yt_audio.ytdlp_options import YtDlpOptionsDirector


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
        if isinstance(result, BaseException):
            raise result
        return result


@pytest.fixture
def fake_ytdlp(monkeypatch):
    FakeYoutubeDL.script = {}
    # Options are covered by test_ytdlp_options.py; building them needs the real YoutubeDL class
    monkeypatch.setattr(YtDlpOptionsDirector, "options_for", lambda self, request: {})
    monkeypatch.setattr(yt_dlp, "YoutubeDL", FakeYoutubeDL)
    return FakeYoutubeDL.script


def video(path, video_id=None):
    return {"id": video_id or path, "title": path, "requested_downloads": [{"filepath": path}]}


def test_download_audio_collects_files_from_every_link(tmp_path, fake_ytdlp):
    fake_ytdlp.update({"https://a": video("a.mp3"), "https://b": video("b.mp3")})

    files, failed = download_audio(["https://a", "https://b"], str(tmp_path))

    assert files == ["a.mp3", "b.mp3"]
    assert failed == []


def test_download_audio_counts_download_errors_and_continues(tmp_path, fake_ytdlp):
    fake_ytdlp.update({"https://bad": yt_dlp.utils.DownloadError("Video unavailable"), "https://ok": video("ok.mp3")})

    files, failed = download_audio(["https://bad", "https://ok"], str(tmp_path))

    assert files == ["ok.mp3"]
    assert failed == ["https://bad"]


def test_download_audio_creates_missing_folder(tmp_path, fake_ytdlp):
    folder = tmp_path / "new" / "folder"

    download_audio([], str(folder))

    assert folder.is_dir()


def test_download_audio_empty_playlist_is_a_failure(tmp_path, fake_ytdlp):
    fake_ytdlp["https://list"] = {"entries": [None, None]}

    files, failed = download_audio(["https://list"], str(tmp_path), allow_playlists=True)

    assert files == []
    assert failed == ["https://list (2 of 2 playlist items failed)"]


def test_download_audio_archive_skip_is_not_a_failure(tmp_path, fake_ytdlp):
    fake_ytdlp["https://list"] = {"entries": []}

    files, failed = download_audio(["https://list"], str(tmp_path), allow_playlists=True, archive=True)

    assert (files, failed) == ([], [])


def test_download_audio_playlist_with_broken_items_is_reported(tmp_path, fake_ytdlp):
    fake_ytdlp["https://list"] = {"entries": [video("a.mp3"), None, video("b.mp3")]}

    files, failed = download_audio(["https://list"], str(tmp_path), allow_playlists=True)

    assert files == ["a.mp3", "b.mp3"]
    assert failed == ["https://list (1 of 3 playlist items failed)"]


def test_download_audio_same_title_from_two_videos_is_a_failure(tmp_path, fake_ytdlp, capsys):
    fake_ytdlp.update({"https://a": video("song.mp3", "id-a"), "https://b": video("song.mp3", "id-b")})

    files, failed = download_audio(["https://a", "https://b"], str(tmp_path))

    assert files == ["song.mp3"]
    assert failed == ["https://b (same title as an earlier video: song.mp3)"]
    assert "--suffix" in capsys.readouterr().out


def test_download_audio_same_video_twice_is_not_a_clash(tmp_path, fake_ytdlp):
    fake_ytdlp.update({"https://a": video("song.mp3", "id-a"), "https://youtu.be/a": video("song.mp3", "id-a")})

    files, failed = download_audio(["https://a", "https://youtu.be/a"], str(tmp_path))

    assert (files, failed) == (["song.mp3"], [])


def test_download_audio_keeps_ytdlps_error_text_without_printing_it_twice(tmp_path, fake_ytdlp, recorder, recorded_events):
    fake_ytdlp["https://bad"] = yt_dlp.utils.DownloadError("ERROR: [youtube] bad: Video unavailable")

    download_audio(["https://bad"], str(tmp_path), events=recorded_events)

    assert recorder.of_type(LinkErrored) == [LinkErrored("[youtube] bad: Video unavailable", "https://bad", already_printed=True)]


def test_download_audio_os_error_fails_only_that_link(tmp_path, fake_ytdlp, capsys):
    fake_ytdlp.update({"https://locked": PermissionError(13, "Permission denied"), "https://ok": video("ok.mp3")})

    files, failed = download_audio(["https://locked", "https://ok"], str(tmp_path))

    assert files == ["ok.mp3"]
    assert failed == ["https://locked"]
    assert "Permission denied" in capsys.readouterr().out


def test_download_audio_reports_progress_to_subscribers(tmp_path, fake_ytdlp, recorder, recorded_events, capsys):
    fake_ytdlp.update({"https://a": video("song.mp3", "id-a"), "https://b": video("song.mp3", "id-b")})

    download_audio(["https://a", "https://b"], str(tmp_path), events=recorded_events)

    assert recorder.of_type(LinkStarted) == [LinkStarted("https://a"), LinkStarted("https://b")]
    assert recorder.of_type(LinkDone) == [LinkDone("https://a", ("song.mp3",))]
    assert recorder.of_type(TitleClash) == [TitleClash("song.mp3")]
    assert capsys.readouterr().out == ""


def test_download_audio_ctrl_c_keeps_what_finished_and_lists_the_rest(tmp_path, fake_ytdlp, recorded_events):
    fake_ytdlp.update({"https://a": video("a.mp3"), "https://b": KeyboardInterrupt(), "https://c": video("c.mp3")})

    with pytest.raises(DownloadInterrupted) as interrupted:
        download_audio(["https://a", "https://b", "https://c"], str(tmp_path), events=recorded_events)

    assert interrupted.value.partial == (["a.mp3"], [])
    assert interrupted.value.unfinished == ["https://b", "https://c"]


def test_ownership_registry_tells_new_repeated_and_clashing_files_apart():
    registry = FileOwnershipRegistry()

    assert registry.claim("song.mp3", "id-a") is FileClaim.NEW_FILE
    assert registry.claim("song.mp3", "id-a") is FileClaim.SAME_VIDEO_AGAIN
    assert registry.claim("song.mp3", "id-b") is FileClaim.TITLE_CLASH
    assert registry.claim("other.mp3", "id-b") is FileClaim.NEW_FILE


@pytest.mark.parametrize(
    ("outcome", "failed", "description"),
    [
        (LinkOutcome("https://a", empty_result_is_failure=False, files=["a.mp3"]), False, "https://a"),
        (LinkOutcome("https://a", empty_result_is_failure=False), False, "https://a"),
        (LinkOutcome("https://a", empty_result_is_failure=True), True, "https://a"),
        (LinkOutcome.fetch_failed("https://a"), True, "https://a"),
        (LinkOutcome("https://a", empty_result_is_failure=False, files=["a.mp3"], problems=["x", "y"]), True, "https://a (x; y)"),
    ],
    ids=["downloaded", "nothing-new-single", "nothing-new-playlist", "fetch-failed", "problems"],
)
def test_link_outcome_decides_failure_and_describes_it(outcome, failed, description):
    assert outcome.failed is failed
    assert outcome.describe_failure() == description
