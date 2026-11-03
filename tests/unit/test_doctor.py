import importlib.metadata
import os
import time

import pytest

from yt_audio.cli import main
from yt_audio.doctor import CheckResult, CheckStatus, version_tuple
from yt_audio.settings import override_settings


@pytest.fixture
def ready(monkeypatch, fake_tools, tmp_path):
    """Everything installed, with fresh cookies. Tests break one thing at a time."""
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\nsecret-session-value\n")
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "2026.01.01")
    with override_settings(cookies_file=str(cookies)):
        yield cookies


def test_doctor_all_ready_exits_0(ready, capsys):
    assert main(["doctor"]) == 0

    output = capsys.readouterr().out
    assert "[MISSING]" not in output and "[WARN]" not in output
    assert "secret-session-value" not in output


@pytest.mark.parametrize(("version", "expected"), [
    ("2025.11.12", "[OK] yt-dlp"),
    ("2025.10.22", "[MISSING] yt-dlp 2025.10.22 is too old"),
    ("2025.11.12.232920", "[OK] yt-dlp"),
])
def test_doctor_checks_yt_dlp_version(ready, monkeypatch, capsys, version, expected):
    monkeypatch.setattr(importlib.metadata, "version", lambda name: version)

    main(["doctor"])

    assert expected in capsys.readouterr().out


def test_doctor_yt_dlp_not_installed_blocks(ready, monkeypatch, capsys):
    def not_installed(name):
        raise importlib.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(importlib.metadata, "version", not_installed)

    assert main(["doctor"]) == 1
    assert "[MISSING] yt-dlp is not installed" in capsys.readouterr().out


@pytest.mark.parametrize(("tool", "message"), [("node", "Node.js not found"), ("ffmpeg", "ffmpeg not found")])
def test_doctor_missing_tool_blocks(ready, fake_tools, capsys, tool, message):
    setattr(fake_tools, tool, None)

    assert main(["doctor"]) == 1
    assert f"[MISSING] {message}" in capsys.readouterr().out


def test_doctor_missing_ejs_only_warns(ready, fake_tools, capsys):
    fake_tools.ejs = False

    assert main(["doctor"]) == 0
    assert "[WARN] yt-dlp-ejs is not installed" in capsys.readouterr().out


def test_doctor_cookie_problems_only_warn(ready, capsys):
    ready.write_text("not a cookie file\n")
    assert main(["doctor"]) == 0
    assert "isn't in Netscape format" in capsys.readouterr().out

    ready.write_text("# Netscape HTTP Cookie File\n")
    old = time.time() - 40 * 86400
    os.utime(ready, (old, old))
    assert main(["doctor"]) == 0
    assert "40 days old" in capsys.readouterr().out

    with override_settings(cookies_file=str(ready) + ".missing"):
        assert main(["doctor"]) == 0
    assert "[WARN] cookies.txt not found" in capsys.readouterr().out


def test_check_result_prints_status_tag_and_only_missing_blocks():
    assert str(CheckResult(CheckStatus.WARN, "careful")) == "[WARN] careful"
    assert CheckResult(CheckStatus.MISSING, "x").blocks_download
    assert not CheckResult(CheckStatus.WARN, "x").blocks_download


def test_version_tuple_ignores_non_numeric_parts():
    assert version_tuple("2025.11.12.dev0") == (2025, 11, 12)
