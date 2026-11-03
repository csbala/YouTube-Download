import os

import pytest

from yt_audio import download_audio
from yt_audio.ytdlp_options import max_title_length


@pytest.fixture
def music_dir(tmp_path):
    return tmp_path / "music"


def test_download_webm_saves_file_and_returns_its_path(music_dir, tone_url):
    files, failed = download_audio([tone_url], str(music_dir), "webm")

    assert failed == []
    assert files == [str(music_dir / "tone.webm")]
    assert os.path.getsize(files[0]) > 0


def test_download_mp3_converts_with_ffmpeg(music_dir, tone_url):
    files, failed = download_audio([tone_url], str(music_dir), "mp3")

    assert failed == []
    assert [os.path.basename(f) for f in files] == ["tone.mp3"]
    assert sorted(os.listdir(music_dir)) == ["tone.mp3"]


def test_download_adds_suffix_to_filename(music_dir, tone_url):
    files, _ = download_audio([tone_url], str(music_dir), "webm", suffix=" [EXTENDED]")

    assert os.path.basename(files[0]) == "tone [EXTENDED].webm"


def test_download_trims_long_titles_but_not_the_folder(music_dir, tone_url):
    suffix = " " + "x" * 300

    files, failed = download_audio([tone_url], str(music_dir), "webm", suffix=suffix)

    assert failed == []
    [path] = files
    assert os.path.dirname(path) == str(music_dir)
    assert os.path.basename(path) == ("tone" + suffix)[: max_title_length(music_dir)] + ".webm"


def test_download_archive_skips_second_run(music_dir, tone_url):
    download_audio([tone_url], str(music_dir), "webm", archive=True)

    files, failed = download_audio([tone_url], str(music_dir), "webm", archive=True)

    assert (files, failed) == ([], [])
    assert (music_dir / ".download-archive.txt").is_file()


def test_download_missing_url_is_reported_as_failed(music_dir, media_server, tone_url):
    missing = f"{media_server}/missing.webm"

    files, failed = download_audio([missing, tone_url], str(music_dir), "webm")

    assert failed == [missing]
    assert [os.path.basename(f) for f in files] == ["tone.webm"]
