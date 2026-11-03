"""What the downloader reports while it works, and who hears about it.

Pattern: Observer. Library code notifies an EventBus instead of printing; ConsoleReporter is the
subscriber that turns events into the console lines users (and the download-music skill) read.
Every user-facing progress message lives in ConsoleReporter.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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


@dataclass(frozen=True)
class TitleClash(Event):
    title: str | None


@dataclass(frozen=True)
class LinkDone(Event):
    link: str


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
            case LinkErrored(reason):
                return f"ERROR: {reason}"
            case TitleClash(title):
                return (
                    f"ERROR: {title} has the same file name as an earlier video, so it was skipped. "
                    f"Download it again on its own with --suffix."
                )
            case LinkDone(link):
                return f"Done: {link}"
        return None


def console_event_bus() -> EventBus:
    return EventBus(ConsoleReporter())
