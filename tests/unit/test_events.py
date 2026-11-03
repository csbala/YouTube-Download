import pytest

from yt_audio.events import (
    BatchStarted,
    ConsoleReporter,
    CookiesMissing,
    Event,
    EventBus,
    FoundryRootGuessed,
    LinkDone,
    LinkErrored,
    LinkStarted,
    NodeMissing,
    PlaylistEmpty,
    PlaylistWritten,
    TitleClash,
)


def test_bus_notifies_every_subscriber_until_it_unsubscribes(recorder):
    other = type(recorder)()
    bus = EventBus(recorder)
    bus.subscribe(other)

    bus.notify(LinkStarted("https://a"))
    bus.unsubscribe(other)
    bus.notify(LinkDone("https://a"))

    assert recorder.events == [LinkStarted("https://a"), LinkDone("https://a")]
    assert other.events == [LinkStarted("https://a")]


@pytest.mark.parametrize(("event", "message"), [
    (NodeMissing(), "Warning: Node.js not found. YouTube downloads may fail. Install it with: winget install -e --id OpenJS.NodeJS.LTS"),
    (CookiesMissing("C:/c.txt"), "Warning: Cookies file not found at C:/c.txt. Proceeding without cookies (may fail for age-restricted videos)."),
    (BatchStarted(2, "out", "mp3"), "Starting batch download for 2 links to out as .mp3..."),
    (LinkStarted("https://a"), "Downloading: https://a"),
    (LinkErrored("Permission denied"), "ERROR: Permission denied"),
    (TitleClash("Song"), "ERROR: Song has the same file name as an earlier video, so it was skipped. Download it again on its own with --suffix."),
    (LinkDone("https://a"), "Done: https://a"),
    (FoundryRootGuessed("C:/x/tavern", "Music_Import/tavern"),
     "Warning: C:/x/tavern isn't inside a Foundry Data folder, so track paths assume Music_Import/tavern/. Use --foundry-root to set it."),
    (PlaylistEmpty("out", ".webm"), "No .webm files found in out. Playlist will be empty."),
    (PlaylistWritten(3, "out/playlist.json"), "Playlist with 3 tracks written to: out/playlist.json"),
], ids=lambda value: type(value).__name__ if isinstance(value, Event) else "")
def test_console_reporter_keeps_the_exact_user_facing_messages(event, message, capsys):
    ConsoleReporter().on_event(event)

    assert capsys.readouterr().out == message + "\n"


def test_console_reporter_ignores_events_it_has_no_message_for(capsys):
    ConsoleReporter().on_event(Event())

    assert capsys.readouterr().out == ""
