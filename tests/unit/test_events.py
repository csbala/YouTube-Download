import json

import pytest

from yt_audio.events import (
    BatchFinished,
    BatchStarted,
    ConsoleReporter,
    CookiesMissing,
    Event,
    EventBus,
    JsonReporter,
    LinkDone,
    LinkErrored,
    LinkStarted,
    NodeMissing,
    RunFailed,
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


@pytest.mark.parametrize(
    ("event", "message"),
    [
        (
            NodeMissing(),
            "Warning: Node.js not found. YouTube downloads may fail. Install it with: winget install -e --id OpenJS.NodeJS.LTS",
        ),
        (
            CookiesMissing("C:/c.txt"),
            "Warning: Cookies file not found at C:/c.txt. Proceeding without cookies (may fail for age-restricted videos).",
        ),
        (BatchStarted(2, "out", "mp3"), "Starting batch download for 2 links to out as .mp3..."),
        (LinkStarted("https://a"), "Downloading: https://a"),
        (LinkErrored("Permission denied"), "ERROR: Permission denied"),
        (LinkErrored("Video unavailable", "https://a", already_printed=True), ""),
        (
            TitleClash("Song"),
            "ERROR: Song has the same file name as an earlier video, so it was skipped. Download it again on its own with --suffix.",
        ),
        (LinkDone("https://a"), "Done: https://a"),
        (RunFailed("ffmpeg is required"), "Error: ffmpeg is required"),
        (
            BatchFinished(2, ("a.mp3",), ("https://b",)),
            "\nSummary: 1 of 2 links downloaded (1 files).\nFAILED: https://b",
        ),
        (
            BatchFinished(3, ("a.mp3",), (), ("https://b", "https://c")),
            "\nSummary: 1 of 3 links downloaded (1 files).\nStopped by Ctrl+C. 2 links not finished:\n"
            "NOT FINISHED: https://b\nNOT FINISHED: https://c",
        ),
    ],
    ids=lambda value: type(value).__name__ if isinstance(value, Event) else "",
)
def test_console_reporter_keeps_the_exact_user_facing_messages(event, message, capsys):
    ConsoleReporter().on_event(event)

    assert capsys.readouterr().out == (message + "\n" if message else "")


def test_console_reporter_ignores_events_it_has_no_message_for(capsys):
    ConsoleReporter().on_event(Event())

    assert capsys.readouterr().out == ""


def test_json_reporter_prints_one_ascii_json_line_per_event(capsys):
    JsonReporter().on_event(LinkDone("https://a", ("Café.mp3",)))

    line = capsys.readouterr().out
    assert line == '{"event": "link_done", "link": "https://a", "files": ["Caf\\u00e9.mp3"]}\n'
    assert json.loads(line)["files"] == ["Café.mp3"]


def test_json_reporter_names_events_in_snake_case_and_handles_empty_ones():
    assert JsonReporter.to_dict(NodeMissing()) == {"event": "node_missing"}
    assert JsonReporter.to_dict(Event()) == {"event": "event"}
