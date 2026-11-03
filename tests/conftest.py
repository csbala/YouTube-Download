import os

import pytest

from yt_audio import tools
from yt_audio.events import EventBus
from yt_audio.settings import override_settings

LAYERS = ("unit", "integration", "e2e")


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(items):
    """Mark each test with the layer of the folder it lives in, so `-m unit` etc. work."""
    for item in items:
        layer = item.path.parent.name
        if layer in LAYERS:
            item.add_marker(layer)


@pytest.fixture(autouse=True)
def isolate_user_files(tmp_path):
    """Never read the real cookies.txt or links.txt from the repo during tests."""
    with override_settings(cookies_file=str(tmp_path / "no-cookies.txt"), links_file=str(tmp_path / "no-links.txt")):
        yield


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


class FakeToolLocator:
    """Pretends Node.js, ffmpeg and yt-dlp-ejs are installed. Set an attribute to None/False to 'uninstall' it."""

    def __init__(self):
        self.node = "/fake/node"
        self.ffmpeg = "/fake/ffmpeg-bin"
        self.ejs = True

    def node_path(self):
        return self.node

    def ffmpeg_dir(self):
        return self.ffmpeg

    def ejs_installed(self):
        return self.ejs


@pytest.fixture
def fake_tools(monkeypatch):
    """Install a FakeToolLocator as the default locator everything uses."""
    fake = FakeToolLocator()
    monkeypatch.setattr(tools, "default_tool_locator", lambda: fake)
    return fake


class EventRecorder:
    def __init__(self):
        self.events = []

    def on_event(self, event):
        self.events.append(event)

    def of_type(self, event_type):
        return [event for event in self.events if isinstance(event, event_type)]


@pytest.fixture
def recorder():
    return EventRecorder()


@pytest.fixture
def recorded_events(recorder):
    """An EventBus whose only subscriber is `recorder`, so nothing reaches the console."""
    return EventBus(recorder)
