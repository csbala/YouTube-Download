import os
import time

import pytest

import downloader
from downloader import main


@pytest.fixture
def ready(monkeypatch, fake_tools, tmp_path):
    """Everything installed, with fresh cookies. Tests break one thing at a time."""
    cookies = tmp_path / "cookies.txt"
    cookies.write_text("# Netscape HTTP Cookie File\nsecret-session-value\n")
    monkeypatch.setattr(downloader, "COOKIES_FILE", str(cookies))
    monkeypatch.setattr(downloader, "has_ejs", lambda: True)
    monkeypatch.setattr(downloader.importlib.metadata, "version", lambda name: "2026.01.01")
    return cookies


def test_doctor_all_ready_exits_0(ready, capsys):
    assert main(["doctor"]) == 0

    output = capsys.readouterr().out
    assert "[MISSING]" not in output and "[WARN]" not in output
    assert "secret-session-value" not in output


@pytest.mark.parametrize("version, expected", [
    ("2025.11.12", "[OK] yt-dlp"),
    ("2025.10.22", "[MISSING] yt-dlp 2025.10.22 is too old"),
    ("2025.11.12.232920", "[OK] yt-dlp"),
])
def test_doctor_checks_yt_dlp_version(ready, monkeypatch, capsys, version, expected):
    monkeypatch.setattr(downloader.importlib.metadata, "version", lambda name: version)

    main(["doctor"])

    assert expected in capsys.readouterr().out


def test_doctor_yt_dlp_not_installed_blocks(ready, monkeypatch, capsys):
    def not_installed(name):
        raise downloader.importlib.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(downloader.importlib.metadata, "version", not_installed)

    assert main(["doctor"]) == 1
    assert "[MISSING] yt-dlp is not installed" in capsys.readouterr().out


@pytest.mark.parametrize("tool, message", [("node", "Node.js not found"), ("ffmpeg", "ffmpeg not found")])
def test_doctor_missing_tool_blocks(ready, fake_tools, capsys, tool, message):
    setattr(fake_tools, tool, None)

    assert main(["doctor"]) == 1
    assert f"[MISSING] {message}" in capsys.readouterr().out


def test_doctor_missing_ejs_only_warns(ready, monkeypatch, capsys):
    monkeypatch.setattr(downloader, "has_ejs", lambda: False)

    assert main(["doctor"]) == 0
    assert "[WARN] yt-dlp-ejs is not installed" in capsys.readouterr().out


def test_doctor_cookie_problems_only_warn(ready, monkeypatch, capsys):
    ready.write_text("not a cookie file\n")
    assert main(["doctor"]) == 0
    assert "isn't in Netscape format" in capsys.readouterr().out

    ready.write_text("# Netscape HTTP Cookie File\n")
    old = time.time() - 40 * 86400
    os.utime(ready, (old, old))
    assert main(["doctor"]) == 0
    assert "40 days old" in capsys.readouterr().out

    monkeypatch.setattr(downloader, "COOKIES_FILE", str(ready) + ".missing")
    assert main(["doctor"]) == 0
    assert "[WARN] cookies.txt not found" in capsys.readouterr().out
