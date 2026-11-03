import os

import pytest

from yt_audio.formats import AudioFormat
from yt_audio.settings import MAX_TITLE_LENGTH, override_settings
from yt_audio.ytdlp_options import DownloadRequest, YtDlpOptionsDirector, max_title_length


def build_ytdlp_options(folder, audio_format, suffix="", allow_playlists=False, archive=False):
    request = DownloadRequest(
        folder, AudioFormat.from_name(audio_format), title_suffix=suffix, allow_playlists=allow_playlists, use_archive=archive
    )
    return YtDlpOptionsDirector().options_for(request)


def test_webm_options_pick_best_webm_audio(tmp_path, fake_tools):
    opts = build_ytdlp_options(str(tmp_path), "webm")

    assert opts["format"] == "bestaudio[ext=webm]/bestaudio"
    assert not any(pp["key"] == "FFmpegExtractAudio" for pp in opts.get("postprocessors", []))


def test_mp3_options_convert_with_ffmpeg(tmp_path, fake_tools):
    opts = build_ytdlp_options(str(tmp_path), "mp3")

    extract = next(pp for pp in opts["postprocessors"] if pp["key"] == "FFmpegExtractAudio")
    assert extract["preferredcodec"] == "mp3"
    assert extract["preferredquality"] == "192"
    assert opts["ffmpeg_location"] == fake_tools.ffmpeg


def test_mp3_without_ffmpeg_raises(tmp_path, fake_tools):
    fake_tools.ffmpeg = None

    with pytest.raises(RuntimeError, match="ffmpeg is required"):
        build_ytdlp_options(str(tmp_path), "mp3")


def test_output_template_has_folder_title_and_suffix(tmp_path, fake_tools):
    opts = build_ytdlp_options(str(tmp_path), "webm", suffix=" [EXTENDED]")

    assert opts["paths"]["home"] == str(tmp_path)
    assert opts["outtmpl"]["default"] == "%(title)s [EXTENDED].%(ext)s"


def test_percent_in_suffix_is_kept_literally(tmp_path, fake_tools):
    opts = build_ytdlp_options(str(tmp_path), "webm", suffix=" 100%")

    assert opts["outtmpl"]["default"] == "%(title)s 100%%.%(ext)s"


def test_long_titles_are_trimmed(tmp_path, fake_tools):
    opts = build_ytdlp_options(str(tmp_path), "webm")

    assert opts["trim_file_name"] == max_title_length(str(tmp_path))


@pytest.mark.parametrize(
    ("folder_length", "expected"),
    [
        (20, MAX_TITLE_LENGTH),
        (150, 90),
        (230, 40),
    ],
)
def test_max_filename_length_leaves_room_for_the_folder(monkeypatch, folder_length, expected):
    monkeypatch.setattr(os.path, "abspath", lambda p: p)

    assert max_title_length("x" * folder_length) == expected


def test_node_is_used_as_js_runtime(tmp_path, fake_tools):
    opts = build_ytdlp_options(str(tmp_path), "webm")

    assert opts["js_runtimes"]["node"] == {"path": fake_tools.node}


@pytest.mark.parametrize(
    ("ejs_installed", "remote_components"),
    [
        (True, []),
        (False, ["ejs:github"]),
    ],
)
def test_challenge_solver_from_github_only_without_ejs(tmp_path, fake_tools, ejs_installed, remote_components):
    fake_tools.ejs = ejs_installed

    opts = build_ytdlp_options(str(tmp_path), "webm")

    assert opts.get("remote_components", []) == remote_components


def test_missing_node_warns_and_is_not_configured(tmp_path, fake_tools, capsys):
    fake_tools.node = None

    opts = build_ytdlp_options(str(tmp_path), "webm")

    assert "node" not in opts.get("js_runtimes", {})
    assert "Node.js not found" in capsys.readouterr().out


def test_cookies_used_when_file_exists(tmp_path, fake_tools):
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n")

    with override_settings(cookies_file=str(cookies)):
        opts = build_ytdlp_options(str(tmp_path), "webm")

    assert opts["cookiefile"] == str(cookies)


def test_cookies_missing_warns(tmp_path, fake_tools, capsys):
    opts = build_ytdlp_options(str(tmp_path), "webm")

    assert opts.get("cookiefile") is None
    assert "Cookies file not found" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("allow_playlists", "noplaylist", "ignoreerrors"),
    [
        (False, True, False),
        (True, False, "only_download"),
    ],
)
def test_playlist_handling(tmp_path, fake_tools, allow_playlists, noplaylist, ignoreerrors):
    opts = build_ytdlp_options(str(tmp_path), "webm", allow_playlists=allow_playlists)

    assert bool(opts.get("noplaylist")) is noplaylist
    assert opts["ignoreerrors"] == ignoreerrors


@pytest.mark.parametrize(
    ("archive", "expected"),
    [
        (False, None),
        (True, ".download-archive.txt"),
    ],
)
def test_archive_file_lives_in_download_folder(tmp_path, fake_tools, archive, expected):
    opts = build_ytdlp_options(str(tmp_path), "webm", archive=archive)

    expected_path = os.path.join(str(tmp_path), expected) if expected else None
    assert opts.get("download_archive") == expected_path


@pytest.mark.parametrize(
    ("allow_playlists", "use_archive", "expected"),
    [
        (False, False, False),
        (True, False, True),
        (True, True, False),
    ],
)
def test_only_a_playlist_without_archive_fails_when_nothing_downloads(allow_playlists, use_archive, expected):
    request = DownloadRequest("out", AudioFormat.from_name("webm"), allow_playlists=allow_playlists, use_archive=use_archive)

    assert request.empty_result_is_failure is expected
