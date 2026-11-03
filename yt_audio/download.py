"""Downloading a batch of links as audio.

Patterns:
- Mediator: BatchDownloadSession coordinates the MediaClient, the FileOwnershipRegistry and the
  EventBus. None of them knows about the others.
- Facade: AudioDownloader (and download_audio) is the one simple entry point over yt-dlp, the options
  builder and the session.
"""
from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import NamedTuple

from . import tools
from .events import BatchStarted, EventBus, LinkDone, LinkErrored, LinkStarted, TitleClash, console_event_bus
from .formats import AudioFormat
from .media import MediaNode, PlaylistHealthInspector
from .settings import AppSettings
from .tools import ToolLocator
from .ydl_client import LinkFailed, MediaClient, open_ydl_client
from .ydl_options import DownloadRequest, YdlOptionsDirector


class Claim(Enum):
    NEW_FILE = auto()
    SAME_VIDEO_AGAIN = auto()  # e.g. the same video linked twice as youtube.com and youtu.be
    TITLE_CLASH = auto()       # a different video already wrote this file name


class FileOwnershipRegistry:
    """Remembers which video wrote each file, so two videos with the same title are caught."""

    def __init__(self) -> None:
        self._owner_by_path: dict[str, str | None] = {}

    def claim(self, path: str, video_id: str | None) -> Claim:
        if path not in self._owner_by_path:
            self._owner_by_path[path] = video_id
            return Claim.NEW_FILE
        if self._owner_by_path[path] == video_id:
            return Claim.SAME_VIDEO_AGAIN
        return Claim.TITLE_CLASH


@dataclass
class LinkOutcome:
    link: str
    empty_result_is_failure: bool
    files: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @classmethod
    def fetch_failed(cls, link: str) -> LinkOutcome:
        return cls(link, empty_result_is_failure=True)

    @property
    def failed(self) -> bool:
        return bool(self.problems) or (not self.files and self.empty_result_is_failure)

    def describe_failure(self) -> str:
        """The link, with the reason appended when it only partly failed."""
        return f"{self.link} ({'; '.join(self.problems)})" if self.problems else self.link


class BatchResult(NamedTuple):
    files: list[str]
    failed_links: list[str]


class BatchDownloadSession:
    def __init__(self, client: MediaClient, request: DownloadRequest, events: EventBus) -> None:
        self._client = client
        self._request = request
        self._events = events
        self._ownership = FileOwnershipRegistry()

    def download(self, link: str) -> LinkOutcome:
        self._events.notify(LinkStarted(link))
        result = self._client.fetch(link)
        if isinstance(result, LinkFailed):
            if result.reason:
                self._events.notify(LinkErrored(result.reason))
            return LinkOutcome.fetch_failed(link)

        outcome = self._collect_new_files(link, result.media)
        if not outcome.failed:
            self._events.notify(LinkDone(link))
        return outcome

    def _collect_new_files(self, link: str, media: MediaNode) -> LinkOutcome:
        outcome = LinkOutcome(link, empty_result_is_failure=self._request.empty_result_is_failure)
        health = media.accept(PlaylistHealthInspector())
        if health.failed_count:
            outcome.problems.append(f"{health.failed_count} of {health.item_count} playlist items failed")

        for video in media.iter_videos():
            for path in video.files:
                match self._ownership.claim(path, video.video_id):
                    case Claim.NEW_FILE:
                        outcome.files.append(path)
                    case Claim.TITLE_CLASH:
                        self._events.notify(TitleClash(video.title))
                        outcome.problems.append(f"same title as an earlier video: {os.path.basename(path)}")
                    case Claim.SAME_VIDEO_AGAIN:
                        pass
        return outcome


class AudioDownloader:
    def __init__(self, tool_locator: ToolLocator | None = None, events: EventBus | None = None,
                 settings: AppSettings | None = None) -> None:
        self._events = events or console_event_bus()
        self._options_director = YdlOptionsDirector(tool_locator or tools.default_tool_locator(), self._events, settings)

    def download(self, links: Iterable[str], request: DownloadRequest) -> BatchResult:
        links = list(links)
        os.makedirs(request.folder, exist_ok=True)
        ydl_options = self._options_director.options_for(request)

        self._events.notify(BatchStarted(len(links), request.folder, request.audio_format.name))
        with open_ydl_client(ydl_options) as client:
            session = BatchDownloadSession(client, request, self._events)
            outcomes = [session.download(link) for link in links]

        return BatchResult(
            files=[path for outcome in outcomes for path in outcome.files],
            failed_links=[outcome.describe_failure() for outcome in outcomes if outcome.failed],
        )


def download_audio(links: Iterable[str], folder: str, audio_format: str = "webm", *, suffix: str = "",
                   allow_playlists: bool = False, archive: bool = False,
                   tool_locator: ToolLocator | None = None, events: EventBus | None = None) -> BatchResult:
    """Download each link as audio into folder. Returns (files, failed_links), where failed_links holds
    each failed link, with the reason appended when it's only partly failed."""
    request = DownloadRequest(folder, AudioFormat.from_name(audio_format), title_suffix=suffix,
                              allow_playlists=allow_playlists, use_archive=archive)
    return AudioDownloader(tool_locator, events).download(links, request)
