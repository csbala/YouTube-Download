import json

import pytest

import yt_audio
from yt_audio import cli, doctor
from yt_audio.cli import ExitCode, Services, main
from yt_audio.download import BatchResult, DownloadInterrupted
from yt_audio.settings import get_settings


@pytest.fixture
def calls(monkeypatch):
    """Replace the download service with a recorder. Set calls.failed to simulate failed links,
    calls.error to make the download raise. The event bus the CLI passes in is kept in calls.events."""

    class Calls:
        downloads = []
        failed = []
        error = None
        events = None
        settings = None

    def fake_download(links, folder, audio_format, events, settings, **options):
        Calls.events, Calls.settings = events, settings
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


def test_main_empty_links_file_exits_2_instead_of_succeeding(calls, tmp_path, capsys):
    links = tmp_path / "links.txt"
    links.write_text("# nothing yet\n\n", encoding="utf-8")

    exit_code = main(["download", "out", "--links", str(links)])

    assert exit_code == ExitCode.COULD_NOT_RUN
    assert calls.downloads == []
    assert "has no links in it" in capsys.readouterr().out


def test_main_ctrl_c_prints_what_finished_and_exits_130(calls, capsys):
    calls.error = DownloadInterrupted(BatchResult(["out/a.mp3"], []), ["https://b", "https://c"])

    exit_code = main(["download", "out", "https://a", "https://b", "https://c"])

    assert exit_code == ExitCode.INTERRUPTED == 130
    output = capsys.readouterr().out
    assert "1 of 3 links downloaded (1 files)" in output
    assert "NOT FINISHED: https://b" in output
    assert "NOT FINISHED: https://c" in output


def test_main_ctrl_c_outside_a_download_exits_130_without_traceback(calls, monkeypatch, capsys):
    def interrupted(**_settings):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "default_services", lambda: Services(download_audio=None, diagnose=interrupted))

    assert main(["doctor"]) == 130
    assert "Stopped by Ctrl+C." in capsys.readouterr().out


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
        "embed_tags": True,
        "quiet": False,
    }


def test_main_no_tags_turns_tagging_off(calls):
    main(["download", "out", "https://a", "--no-tags"])

    assert calls.downloads[0]["embed_tags"] is False


def test_main_json_prints_only_json_lines_and_quiets_ytdlp(calls, capsys):
    calls.failed = ["https://bad"]

    main(["download", "out", "https://ok", "https://bad", "--json"])

    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert records[-1] == {
        "event": "batch_finished",
        "link_count": 2,
        "files": ["out/file"],
        "failed_links": ["https://bad"],
        "unfinished": [],
        "downloaded_count": 1,
    }
    assert calls.downloads[0]["quiet"] is True


def test_main_json_reports_setup_errors_as_json(calls, capsys):
    calls.error = RuntimeError("ffmpeg is required")

    main(["download", "out", "https://a", "--json"])

    assert json.loads(capsys.readouterr().out) == {"event": "run_failed", "message": "ffmpeg is required"}


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


def test_main_uses_the_configured_cookies_by_default(calls):
    main(["download", "out", "https://a"])

    assert calls.settings == get_settings()


def test_main_cookies_option_points_the_download_at_another_file(calls, tmp_path):
    main(["download", "out", "https://a", "--cookies", str(tmp_path / "other.txt")])

    assert calls.settings.cookies_file == str(tmp_path / "other.txt")
    assert calls.settings.links_file == get_settings().links_file


def test_doctor_checks_the_cookies_file_given_with_cookies(tmp_path, monkeypatch, capsys):
    checked = []
    monkeypatch.setattr(
        cli, "default_services", lambda: Services(download_audio=None, diagnose=lambda settings: checked.append(settings) or [])
    )

    main(["doctor", "--cookies", str(tmp_path / "c.txt")])

    assert [settings.cookies_file for settings in checked] == [str(tmp_path / "c.txt")]


def test_version_names_the_package_ytdlp_and_python(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])

    assert exc.value.code == 0
    output = capsys.readouterr().out
    assert output.startswith(f"yt-audio {yt_audio.__version__} (yt-dlp ")
    assert "Python 3." in output
