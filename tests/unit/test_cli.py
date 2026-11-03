import pytest

from yt_audio import cli, doctor
from yt_audio.cli import ExitCode, Services, main
from yt_audio.download import BatchResult


@pytest.fixture
def calls(monkeypatch):
    """Replace the download service with a recorder. Set calls.failed to simulate failed links,
    calls.error to make the download raise."""

    class Calls:
        downloads = []
        failed = []
        error = None

    def fake_download(links, folder, audio_format, **options):
        if Calls.error:
            raise Calls.error
        Calls.downloads.append({"links": links, "folder": folder, "format": audio_format, **options})
        return BatchResult([f"{folder}/file"], list(Calls.failed))

    Calls.downloads, Calls.failed = [], []
    services = Services(download_audio=fake_download, diagnose=doctor.diagnose)
    monkeypatch.setattr(cli, "default_services", lambda: services)
    return Calls


def test_main_downloads_urls_given_as_arguments(calls):
    exit_code = main(["download", "out", "https://a", "https://b"])

    assert exit_code == ExitCode.SUCCESS == 0
    assert calls.downloads[0]["links"] == ["https://a", "https://b"]
    assert calls.downloads[0]["folder"] == "out"


def test_main_downloads_mp3_by_default(calls):
    main(["download", "out", "https://a"])

    assert calls.downloads[0]["format"] == "mp3"


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


def test_main_passes_download_options(calls):
    main(["download", "out", "https://a", "--suffix", " X", "--allow-playlists", "--archive", "--format", "webm"])

    assert calls.downloads[0] == {
        "links": ["https://a"],
        "folder": "out",
        "format": "webm",
        "suffix": " X",
        "allow_playlists": True,
        "archive": True,
    }


def test_main_without_command_shows_usage(calls):
    with pytest.raises(SystemExit) as exc:
        main([])

    assert exc.value.code == 2


@pytest.mark.parametrize("removed", [["playlist", "out"], ["--generate", "out"], ["download", "out", "--foundry-root", "x"]])
def test_main_rejects_the_removed_foundry_commands(calls, removed):
    with pytest.raises(SystemExit) as exc:
        main(removed)

    assert exc.value.code == 2
    assert calls.downloads == []


def test_download_help_lists_every_format_with_what_it_is_for(capsys):
    with pytest.raises(SystemExit):
        main(["download", "--help"])

    output = " ".join(capsys.readouterr().out.split())
    assert "mp3 (plays everywhere; needs ffmpeg)" in output
    assert "webm (YouTube's original audio, no conversion)" in output


@pytest.mark.parametrize("argv", [["download", "out"], ["doctor"]])
def test_each_subcommand_dispatches_to_its_command_object(argv):
    args = cli.build_parser().parse_args(argv)

    assert args.command.name == argv[0]
    assert args.command in cli.COMMANDS
