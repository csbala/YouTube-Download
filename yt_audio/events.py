"""What the downloader reports while it works, and who hears about it.

Pattern: Observer. Library code notifies an EventBus instead of printing. ConsoleReporter is the
subscriber that turns events into the console lines users read, and every user-facing progress
message lives in it. JsonReporter prints the same events as JSON lines for scripts (--json).
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Protocol


class Event:
    """Base class of everything the EventBus carries."""


@dataclass(frozen=True)
class NodeMissing(Event):
    pass


@dataclass(frozen=True)
class CookiesMissing(Event):
    cookies_file: str


@dataclass(frozen=True)
class BatchStarted(Event):
    link_count: int
    folder: str
    audio_format: str


@dataclass(frozen=True)
class LinkStarted(Event):
    link: str


@dataclass(frozen=True)
class LinkErrored(Event):
    reason: str
    link: str = ""
    already_printed: bool = False  # yt-dlp printed its own ERROR line, so the console needn't repeat it


@dataclass(frozen=True)
class TitleClash(Event):
    title: str | None


@dataclass(frozen=True)
class LinkDone(Event):
    link: str
    files: tuple[str, ...] = ()  # the new files this link wrote


@dataclass(frozen=True)
class BatchFinished(Event):
    """The end of a run, or of the part that ran before Ctrl+C (then `unfinished` lists what's left)."""

    link_count: int
    files: tuple[str, ...]
    failed_links: tuple[str, ...]
    unfinished: tuple[str, ...] = ()

    @property
    def downloaded_count(self) -> int:
        return self.link_count - len(self.failed_links) - len(self.unfinished)


@dataclass(frozen=True)
class RunFailed(Event):
    """The run couldn't start, e.g. no links or ffmpeg missing for mp3."""

    message: str


class EventListener(Protocol):
    def on_event(self, event: Event) -> None: ...


class EventBus:
    def __init__(self, *listeners: EventListener) -> None:
        self._listeners = list(listeners)

    def subscribe(self, listener: EventListener) -> None:
        self._listeners.append(listener)

    def unsubscribe(self, listener: EventListener) -> None:
        self._listeners.remove(listener)

    def notify(self, event: Event) -> None:
        for listener in self._listeners:
            listener.on_event(event)


class ConsoleReporter:
    def on_event(self, event: Event) -> None:
        message = self.describe(event)
        if message:
            print(message)

    @staticmethod
    def describe(event: Event) -> str | None:
        match event:
            case NodeMissing():
                return "Warning: Node.js not found. YouTube downloads may fail. Install it with: winget install -e --id OpenJS.NodeJS.LTS"
            case CookiesMissing(cookies_file):
                return (
                    f"Warning: Cookies file not found at {cookies_file}. Proceeding without cookies (may fail for age-restricted videos)."
                )
            case BatchStarted(link_count, folder, audio_format):
                return f"Starting batch download for {link_count} links to {folder} as .{audio_format}..."
            case LinkStarted(link):
                return f"Downloading: {link}"
            case LinkErrored(reason, _, already_printed):
                return None if already_printed else f"ERROR: {reason}"
            case TitleClash(title):
                return (
                    f"ERROR: {title} has the same file name as an earlier video, so it was skipped. "
                    f"Download it again on its own with --suffix."
                )
            case LinkDone(link, _):
                return f"Done: {link}"
            case BatchFinished() as finished:
                return ConsoleReporter._describe_summary(finished)
            case RunFailed(message):
                return f"Error: {message}"
        return None

    @staticmethod
    def _describe_summary(finished: BatchFinished) -> str:
        lines = [
            f"\nSummary: {finished.downloaded_count} of {finished.link_count} links downloaded ({len(finished.files)} files).",
            *(f"FAILED: {link}" for link in finished.failed_links),
        ]
        if finished.unfinished:
            lines.append(f"Stopped by Ctrl+C. {len(finished.unfinished)} links not finished:")
            lines += (f"NOT FINISHED: {link}" for link in finished.unfinished)
        return "\n".join(lines)


class JsonReporter:
    """Prints each event as one line of JSON, for scripts and AI tools: {"event": "link_done", "link": ..., ...}.
    ASCII-only, so it parses whatever the console's encoding is."""

    def on_event(self, event: Event) -> None:
        print(json.dumps(self.to_dict(event)), flush=True)

    @staticmethod
    def to_dict(event: Event) -> dict[str, Any]:
        record: dict[str, Any] = {"event": re.sub(r"(?<!^)(?=[A-Z])", "_", type(event).__name__).lower()}
        if is_dataclass(event):
            record.update(asdict(event))
        if isinstance(event, BatchFinished):
            record["downloaded_count"] = event.downloaded_count
        return record


def console_event_bus() -> EventBus:
    return EventBus(ConsoleReporter())


def json_event_bus() -> EventBus:
    """Every event as JSON on stdout. yt-dlp's own messages must then stay off stdout (see YtDlpOptionsBuilder)."""
    return EventBus(JsonReporter())
