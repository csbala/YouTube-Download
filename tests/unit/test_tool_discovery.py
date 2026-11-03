import os

import downloader

NODE_DEFAULT = r"C:\Program Files\nodejs\node.exe"


def which_finds(mapping):
    return lambda name: mapping.get(name)


def test_find_node_prefers_path(monkeypatch):
    monkeypatch.setattr(downloader.shutil, "which", which_finds({"node": "/usr/bin/node"}))

    assert downloader.find_node() == "/usr/bin/node"


def test_find_node_falls_back_to_default_install(monkeypatch):
    real_isfile = os.path.isfile
    monkeypatch.setattr(downloader.shutil, "which", which_finds({}))
    monkeypatch.setattr(downloader.os.path, "isfile", lambda p: p == NODE_DEFAULT or real_isfile(p))

    assert downloader.find_node() == NODE_DEFAULT


def test_find_node_missing_returns_none(monkeypatch):
    real_isfile = os.path.isfile
    monkeypatch.setattr(downloader.shutil, "which", which_finds({}))
    monkeypatch.setattr(downloader.os.path, "isfile", lambda p: p != NODE_DEFAULT and real_isfile(p))

    assert downloader.find_node() is None


def test_find_ffmpeg_prefers_path(monkeypatch, tmp_path):
    exe = tmp_path / "bin" / "ffmpeg.exe"
    monkeypatch.setattr(downloader.shutil, "which", which_finds({"ffmpeg": str(exe)}))

    assert downloader.find_ffmpeg() == str(exe.parent)


def test_find_ffmpeg_finds_winget_install(monkeypatch, tmp_path):
    exe = tmp_path / "Microsoft" / "WinGet" / "Packages" / "Gyan.FFmpeg_abc" / "ffmpeg-9.0" / "bin" / "ffmpeg.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    monkeypatch.setattr(downloader.shutil, "which", which_finds({}))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert downloader.find_ffmpeg() == str(exe.parent)


def test_find_ffmpeg_missing_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(downloader.shutil, "which", which_finds({}))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert downloader.find_ffmpeg() is None


def test_find_ffmpeg_picks_newest_of_several_winget_installs(monkeypatch, tmp_path):
    packages = tmp_path / "Microsoft" / "WinGet" / "Packages"
    exes = []
    for i, version in enumerate(["ffmpeg-8.0", "ffmpeg-7.1"]):
        exe = packages / f"Gyan.FFmpeg_{i}" / version / "bin" / "ffmpeg.exe"
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b"")
        os.utime(exe, (1000 + i, 1000 + i))
        exes.append(exe)
    monkeypatch.setattr(downloader.shutil, "which", which_finds({}))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert downloader.find_ffmpeg() == str(exes[1].parent)
