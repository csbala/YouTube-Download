import pytest

from yt_audio import cli, doctor
from yt_audio.cli import ExitCode, Services, main


@pytest.fixture
def calls(monkeypatch):
    """Replace the download and playlist services with recorders. Set calls.failed to simulate failed links,
    calls.error to make the download raise, calls.playlist_error to make writing playlist.json raise."""

    class Calls:
        downloads = []
        playlists = []
        failed = []
        error = None
        playlist_error = None

    def fake_download(links, folder, audio_format, **options):
        if Calls.error:
            raise Calls.error
        Calls.downloads.append({"links": links, "folder": folder, "format": audio_format, **options})
        return [f"{folder}/file"], list(Calls.failed)

    def fake_write_playlist(folder, **options):
        if Calls.playlist_error:
            raise Calls.playlist_error
        Calls.playlists.append({"folder": folder, **options})

    Calls.downloads, Calls.playlists, Calls.failed = [], [], []
    services = Services(download_audio=fake_download, write_playlist=fake_write_playlist, diagnose=doctor.diagnose)
    monkeypatch.setattr(cli, "default_services", lambda: services)
    return Calls


def test_main_downloads_urls_given_as_arguments(calls):
    exit_code = main(["download", "out", "https://a", "https://b"])

    assert exit_code == ExitCode.SUCCESS == 0
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


@pytest.mark.parametrize(
    ("args", "writes_playlist"),
    [
        (["--format", "webm"], True),
        (["--format", "mp3"], False),
        (["--format", "mp3", "--playlist-json"], True),
        (["--format", "webm", "--no-playlist-json"], False),
    ],
)
def test_main_playlist_json_default_depends_on_format(calls, args, writes_playlist):
    main(["download", "out", "https://a", *args])

    assert bool(calls.playlists) is writes_playlist


def test_main_passes_download_options(calls):
    main(["download", "out", "https://a", "--suffix", " X", "--allow-playlists", "--archive", "--format", "mp3"])

    assert calls.downloads[0] == {
        "links": ["https://a"],
        "folder": "out",
        "format": "mp3",
        "suffix": " X",
        "allow_playlists": True,
        "archive": True,
    }


def test_main_playlist_command_only_writes_json(calls, tmp_path):
    exit_code = main(["playlist", str(tmp_path), "--format", "mp3", "--volume", "0.2", "--foundry-root", "root", "--foundry-folder", "abc"])

    assert exit_code == 0
    assert calls.downloads == []
    assert calls.playlists == [
        {"folder": str(tmp_path), "audio_format": "mp3", "foundry_root": "root", "volume": 0.2, "foundry_folder": "abc"}
    ]


def test_main_without_command_shows_usage(calls):
    with pytest.raises(SystemExit) as exc:
        main([])

    assert exc.value.code == 2


def test_main_playlist_command_missing_folder_exits_2(tmp_path, capsys):
    exit_code = main(["playlist", str(tmp_path / "missing")])

    assert exit_code == 2
    assert "not found" in capsys.readouterr().out


def test_main_playlist_command_bad_foundry_root_exits_2(tmp_path, capsys):
    (tmp_path / "music").mkdir()
    (tmp_path / "root").mkdir()

    exit_code = main(["playlist", str(tmp_path / "music"), "--foundry-root", str(tmp_path / "root")])

    assert exit_code == 2
    assert "Error: couldn't write playlist.json" in capsys.readouterr().out


def test_main_playlist_error_after_download_still_prints_summary(calls, capsys):
    calls.playlist_error = ValueError("out is not inside the Foundry root root")

    exit_code = main(["download", "out", "https://a"])

    assert exit_code == 2
    output = capsys.readouterr().out
    assert "Error: couldn't write playlist.json" in output
    assert "Summary: 1 of 1 links downloaded" in output


@pytest.mark.parametrize("value", ["-0.1", "1.5", "loud"])
def test_main_rejects_volume_outside_0_to_1(calls, value, capsys):
    with pytest.raises(SystemExit) as exc:
        main(["download", "out", "https://a", "--volume", value])

    assert exc.value.code == 2
    assert "must be a number from 0 to 1" in capsys.readouterr().err


@pytest.mark.parametrize("argv", [["download", "out"], ["playlist", "out"], ["doctor"]])
def test_each_subcommand_dispatches_to_its_command_object(argv):
    args = cli.build_parser().parse_args(argv)

    assert args.command.name == argv[0]
    assert args.command in cli.COMMANDS
