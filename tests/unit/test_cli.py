import pytest

import downloader
from downloader import main


@pytest.fixture
def calls(monkeypatch):
    """Replace the download and playlist steps with recorders. Set calls.failed to simulate failed links."""
    class Calls:
        downloads = []
        playlists = []
        failed = []
        error = None

    def fake_download(links, folder, audio_format, **options):
        if Calls.error:
            raise Calls.error
        Calls.downloads.append({"links": links, "folder": folder, "format": audio_format, **options})
        return [f"{folder}/file"], list(Calls.failed)

    def fake_write_playlist(folder, **options):
        Calls.playlists.append({"folder": folder, **options})

    Calls.downloads, Calls.playlists, Calls.failed = [], [], []
    monkeypatch.setattr(downloader, "download_audio", fake_download)
    monkeypatch.setattr(downloader, "write_playlist", fake_write_playlist)
    return Calls


def test_main_downloads_urls_given_as_arguments(calls):
    exit_code = main(["download", "out", "https://a", "https://b"])

    assert exit_code == 0
    assert calls.downloads[0]["links"] == ["https://a", "https://b"]
    assert calls.downloads[0]["folder"] == "out"


def test_main_reads_links_file_when_no_urls(calls, tmp_path):
    links = tmp_path / "mine.txt"
    links.write_text("https://a\nhttps://b\n")

    main(["download", "out", "--links", str(links)])

    assert calls.downloads[0]["links"] == ["https://a", "https://b"]


def test_main_missing_links_file_exits_2(calls, tmp_path, capsys):
    exit_code = main(["download", "out", "--links", str(tmp_path / "missing.txt")])

    assert exit_code == 2
    assert calls.downloads == []
    assert "no links given" in capsys.readouterr().out


def test_main_setup_error_exits_2(calls, capsys):
    calls.error = RuntimeError("ffmpeg is required")

    assert main(["download", "out", "https://a", "--format", "mp3"]) == 2
    assert "Error: ffmpeg is required" in capsys.readouterr().out


def test_main_failed_link_exits_1_and_reports_it(calls, capsys):
    calls.failed = ["https://bad"]

    exit_code = main(["download", "out", "https://ok", "https://bad"])

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "1 of 2 links downloaded" in output
    assert "FAILED: https://bad" in output


def test_main_legacy_generate_flag_still_downloads(calls):
    assert main(["--generate", "out", "https://a"]) == 0
    assert calls.downloads[0]["folder"] == "out"


@pytest.mark.parametrize("args, writes_playlist", [
    (["--format", "webm"], True),
    (["--format", "mp3"], False),
    (["--format", "mp3", "--playlist-json"], True),
    (["--format", "webm", "--no-playlist-json"], False),
])
def test_main_playlist_json_default_depends_on_format(calls, args, writes_playlist):
    main(["download", "out", "https://a", *args])

    assert bool(calls.playlists) is writes_playlist


def test_main_passes_download_options(calls):
    main(["download", "out", "https://a", "--suffix", " X", "--allow-playlists", "--archive", "--format", "mp3"])

    assert calls.downloads[0] == {
        "links": ["https://a"], "folder": "out", "format": "mp3",
        "suffix": " X", "allow_playlists": True, "archive": True,
    }


def test_main_playlist_command_only_writes_json(calls):
    exit_code = main(["playlist", "out", "--format", "mp3", "--volume", "0.2",
                      "--foundry-root", "root", "--foundry-folder", "abc"])

    assert exit_code == 0
    assert calls.downloads == []
    assert calls.playlists == [{"folder": "out", "audio_format": "mp3", "foundry_root": "root",
                                "volume": 0.2, "foundry_folder": "abc"}]


def test_main_without_command_shows_usage(calls):
    with pytest.raises(SystemExit) as exc:
        main([])

    assert exc.value.code == 2
