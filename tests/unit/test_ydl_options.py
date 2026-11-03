import os

import pytest

import downloader
from downloader import build_ydl_options


def test_webm_options_pick_best_webm_audio(tmp_path, fake_tools):
    opts = build_ydl_options(str(tmp_path), "webm")

    assert opts["format"] == "bestaudio[ext=webm]/bestaudio"
    assert not any(pp["key"] == "FFmpegExtractAudio" for pp in opts.get("postprocessors", []))


def test_mp3_options_convert_with_ffmpeg(tmp_path, fake_tools):
    opts = build_ydl_options(str(tmp_path), "mp3")

    extract = next(pp for pp in opts["postprocessors"] if pp["key"] == "FFmpegExtractAudio")
    assert extract["preferredcodec"] == "mp3"
    assert extract["preferredquality"] == "192"
    assert opts["ffmpeg_location"] == fake_tools.ffmpeg


def test_mp3_without_ffmpeg_raises(tmp_path, fake_tools):
    fake_tools.ffmpeg = None

    with pytest.raises(RuntimeError, match="ffmpeg is required"):
        build_ydl_options(str(tmp_path), "mp3")


def test_output_template_has_folder_title_and_suffix(tmp_path, fake_tools):
    opts = build_ydl_options(str(tmp_path), "webm", suffix=" [EXTENDED]")

    assert opts["outtmpl"]["default"] == os.path.join(str(tmp_path), "%(title)s [EXTENDED].%(ext)s")


def test_node_is_used_as_js_runtime(tmp_path, fake_tools):
    opts = build_ydl_options(str(tmp_path), "webm")

    assert opts["js_runtimes"]["node"] == {"path": fake_tools.node}
    assert opts["remote_components"] == ["ejs:github"]


def test_missing_node_warns_and_is_not_configured(tmp_path, fake_tools, capsys):
    fake_tools.node = None

    opts = build_ydl_options(str(tmp_path), "webm")

    assert "node" not in opts.get("js_runtimes", {})
    assert "Node.js not found" in capsys.readouterr().out


def test_cookies_used_when_file_exists(tmp_path, fake_tools, monkeypatch):
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\n")
    monkeypatch.setattr(downloader, "COOKIES_FILE", str(cookies))

    opts = build_ydl_options(str(tmp_path), "webm")

    assert opts["cookiefile"] == str(cookies)


def test_cookies_missing_warns(tmp_path, fake_tools, capsys):
    opts = build_ydl_options(str(tmp_path), "webm")

    assert opts.get("cookiefile") is None
    assert "Cookies file not found" in capsys.readouterr().out


@pytest.mark.parametrize("allow_playlists, noplaylist, ignoreerrors", [
    (False, True, False),
    (True, False, "only_download"),
])
def test_playlist_handling(tmp_path, fake_tools, allow_playlists, noplaylist, ignoreerrors):
    opts = build_ydl_options(str(tmp_path), "webm", allow_playlists=allow_playlists)

    assert bool(opts.get("noplaylist")) is noplaylist
    assert opts["ignoreerrors"] == ignoreerrors


@pytest.mark.parametrize("archive, expected", [
    (False, None),
    (True, ".download-archive.txt"),
])
def test_archive_file_lives_in_download_folder(tmp_path, fake_tools, archive, expected):
    opts = build_ydl_options(str(tmp_path), "webm", archive=archive)

    expected_path = os.path.join(str(tmp_path), expected) if expected else None
    assert opts.get("download_archive") == expected_path
