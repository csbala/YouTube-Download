import os

import pytest

import downloader

LAYERS = ("unit", "integration", "e2e")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    """Mark each test with the layer of the folder it lives in, so `-m unit` etc. work."""
    for item in items:
        layer = item.path.parent.name
        if layer in LAYERS:
            item.add_marker(layer)


@pytest.fixture(autouse=True)
def isolate_user_files(tmp_path, monkeypatch):
    """Never read the real cookies.txt or links.txt from the repo during tests."""
    monkeypatch.setattr(downloader, "COOKIES_FILE", str(tmp_path / "no-cookies.txt"))
    monkeypatch.setattr(downloader, "LINKS_FILE", str(tmp_path / "no-links.txt"))


@pytest.fixture
def foundry_data_dir(tmp_path):
    """An empty Foundry VTT Data folder: <tmp>/FoundryVTT/Data."""
    data = tmp_path / "FoundryVTT" / "Data"
    data.mkdir(parents=True)
    return data


@pytest.fixture
def make_audio_files():
    """Factory: create empty files with the given names in a folder and return the folder."""
    def make(folder, *names):
        os.makedirs(folder, exist_ok=True)
        for name in names:
            (folder / name).write_bytes(b"")
        return folder
    return make


@pytest.fixture
def fake_tools(monkeypatch):
    """Pretend Node.js and ffmpeg are installed at fixed paths. Set an attribute to None to 'uninstall' it."""
    class Tools:
        node = "/fake/node"
        ffmpeg = "/fake/ffmpeg-bin"

    tools = Tools()
    monkeypatch.setattr(downloader, "find_node", lambda: tools.node)
    monkeypatch.setattr(downloader, "find_ffmpeg", lambda: tools.ffmpeg)
    return tools
