import os
import shutil

from yt_audio.tools import (
    NODE_DEFAULT_INSTALL,
    CachingToolLocator,
    KnownLocationLookup,
    SystemPathLookup,
    SystemToolLocator,
    ToolLookup,
)


def which_finds(mapping):
    return lambda name: mapping.get(name)


def test_find_node_prefers_path(monkeypatch):
    monkeypatch.setattr(shutil, "which", which_finds({"node": "/usr/bin/node"}))

    assert SystemToolLocator().node_path() == "/usr/bin/node"


def test_find_node_falls_back_to_default_install(monkeypatch):
    real_isfile = os.path.isfile
    monkeypatch.setattr(shutil, "which", which_finds({}))
    monkeypatch.setattr(os.path, "isfile", lambda p: p == NODE_DEFAULT_INSTALL or real_isfile(p))

    assert SystemToolLocator().node_path() == NODE_DEFAULT_INSTALL


def test_find_node_missing_returns_none(monkeypatch):
    real_isfile = os.path.isfile
    monkeypatch.setattr(shutil, "which", which_finds({}))
    monkeypatch.setattr(os.path, "isfile", lambda p: p != NODE_DEFAULT_INSTALL and real_isfile(p))

    assert SystemToolLocator().node_path() is None


def test_find_ffmpeg_prefers_path(monkeypatch, tmp_path):
    exe = tmp_path / "bin" / "ffmpeg.exe"
    monkeypatch.setattr(shutil, "which", which_finds({"ffmpeg": str(exe)}))

    assert SystemToolLocator().ffmpeg_dir() == str(exe.parent)


def test_find_ffmpeg_finds_winget_install(monkeypatch, tmp_path):
    exe = tmp_path / "Microsoft" / "WinGet" / "Packages" / "Gyan.FFmpeg_abc" / "ffmpeg-9.0" / "bin" / "ffmpeg.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"")
    monkeypatch.setattr(shutil, "which", which_finds({}))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert SystemToolLocator().ffmpeg_dir() == str(exe.parent)


def test_find_ffmpeg_missing_returns_none(monkeypatch, tmp_path):
    monkeypatch.setattr(shutil, "which", which_finds({}))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert SystemToolLocator().ffmpeg_dir() is None


def test_find_ffmpeg_picks_newest_of_several_winget_installs(monkeypatch, tmp_path):
    packages = tmp_path / "Microsoft" / "WinGet" / "Packages"
    exes = []
    for i, version in enumerate(["ffmpeg-8.0", "ffmpeg-7.1"]):
        exe = packages / f"Gyan.FFmpeg_{i}" / version / "bin" / "ffmpeg.exe"
        exe.parent.mkdir(parents=True)
        exe.write_bytes(b"")
        os.utime(exe, (1000 + i, 1000 + i))
        exes.append(exe)
    monkeypatch.setattr(shutil, "which", which_finds({}))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert SystemToolLocator().ffmpeg_dir() == str(exes[1].parent)


class AnswerLookup(ToolLookup):
    def __init__(self, answer, asked):
        super().__init__()
        self._answer = answer
        self._asked = asked

    def _try_locate(self):
        self._asked.append(self._answer)
        return self._answer


def test_lookup_chain_stops_at_the_first_link_that_finds_the_tool():
    asked = []
    head = AnswerLookup(None, asked)
    head.then(AnswerLookup("/second", asked)).then(AnswerLookup("/third", asked))

    assert head.locate() == "/second"
    assert asked == [None, "/second"]


def test_lookup_chain_returns_none_when_no_link_finds_it(monkeypatch):
    monkeypatch.setattr(shutil, "which", which_finds({}))
    head = SystemPathLookup("node")
    head.then(KnownLocationLookup("/definitely/not/here"))

    assert head.locate() is None


def test_caching_locator_asks_the_real_locator_once():
    class CountingLocator:
        calls = 0

        def node_path(self):
            CountingLocator.calls += 1
            return "/node"

        def ffmpeg_dir(self):
            CountingLocator.calls += 1
            return "/ffmpeg"

        def ejs_installed(self):
            CountingLocator.calls += 1
            return True

    proxy = CachingToolLocator(CountingLocator())

    for _ in range(3):
        assert (proxy.node_path(), proxy.ffmpeg_dir(), proxy.ejs_installed()) == ("/node", "/ffmpeg", True)
    assert CountingLocator.calls == 3
