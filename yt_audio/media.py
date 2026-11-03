"""What a link turned into: one video, or a (possibly nested) playlist with some broken entries.

Patterns:
- Adapter: YtDlpInfoAdapter turns yt-dlp's raw info dicts into the typed tree below, so no other
  module needs to know about "entries", None entries or "requested_downloads".
- Composite: VideoNode, FailedEntryNode and PlaylistNode share the MediaNode interface, so a single
  video and a playlist of playlists are handled the same way.
- Iterator: MediaNode.iter_videos() walks the tree lazily.
- Visitor: MediaVisitor subclasses (DownloadedFilesCollector, PlaylistHealthInspector) compute things
  over the tree without adding methods to the node classes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

Result = TypeVar("Result")


class MediaNode(ABC):
    @abstractmethod
    def iter_videos(self) -> Iterator[VideoNode]: ...

    @abstractmethod
    def accept(self, visitor: MediaVisitor[Result]) -> Result: ...


@dataclass(frozen=True)
class VideoNode(MediaNode):
    video_id: str | None
    title: str | None
    files: tuple[str, ...]

    def iter_videos(self) -> Iterator[VideoNode]:
        yield self

    def accept(self, visitor: MediaVisitor[Result]) -> Result:
        return visitor.visit_video(self)


@dataclass(frozen=True)
class FailedEntryNode(MediaNode):
    """A playlist entry yt-dlp couldn't download."""

    def iter_videos(self) -> Iterator[VideoNode]:
        yield from ()

    def accept(self, visitor: MediaVisitor[Result]) -> Result:
        return visitor.visit_failed_entry(self)


@dataclass(frozen=True)
class PlaylistNode(MediaNode):
    children: tuple[MediaNode, ...]

    def iter_videos(self) -> Iterator[VideoNode]:
        for child in self.children:
            yield from child.iter_videos()

    def accept(self, visitor: MediaVisitor[Result]) -> Result:
        return visitor.visit_playlist(self)


NOTHING_DOWNLOADED = PlaylistNode(children=())


class MediaVisitor(ABC, Generic[Result]):
    @abstractmethod
    def visit_video(self, video: VideoNode) -> Result: ...

    @abstractmethod
    def visit_failed_entry(self, entry: FailedEntryNode) -> Result: ...

    @abstractmethod
    def visit_playlist(self, playlist: PlaylistNode) -> Result: ...


class DownloadedFilesCollector(MediaVisitor[list[str]]):
    def visit_video(self, video: VideoNode) -> list[str]:
        return list(video.files)

    def visit_failed_entry(self, entry: FailedEntryNode) -> list[str]:
        return []

    def visit_playlist(self, playlist: PlaylistNode) -> list[str]:
        return [path for child in playlist.children for path in child.accept(self)]


@dataclass(frozen=True)
class PlaylistHealth:
    item_count: int
    failed_count: int

    def __add__(self, other: PlaylistHealth) -> PlaylistHealth:
        return PlaylistHealth(self.item_count + other.item_count, self.failed_count + other.failed_count)


class PlaylistHealthInspector(MediaVisitor[PlaylistHealth]):
    """Counts the videos and the broken entries anywhere in the tree."""

    def visit_video(self, video: VideoNode) -> PlaylistHealth:
        return PlaylistHealth(item_count=1, failed_count=0)

    def visit_failed_entry(self, entry: FailedEntryNode) -> PlaylistHealth:
        return PlaylistHealth(item_count=1, failed_count=1)

    def visit_playlist(self, playlist: PlaylistNode) -> PlaylistHealth:
        return sum((child.accept(self) for child in playlist.children), PlaylistHealth(0, 0))


class YtDlpInfoAdapter:
    @classmethod
    def to_media(cls, info: Mapping[str, Any] | None) -> MediaNode:
        if not info:
            return NOTHING_DOWNLOADED  # A single video the archive skipped
        entries = info.get("entries")
        if entries is None:
            return cls._to_video(info)
        # yt-dlp keeps failed entries as None and drops the ones the archive skipped
        return PlaylistNode(tuple(cls.to_media(entry) if entry else FailedEntryNode() for entry in entries))

    @staticmethod
    def _to_video(info: Mapping[str, Any]) -> VideoNode:
        files = tuple(download["filepath"] for download in info.get("requested_downloads", []) if download.get("filepath"))
        return VideoNode(video_id=info.get("id"), title=info.get("title"), files=files)


def downloaded_files(info: Mapping[str, Any] | None) -> list[str]:
    """The final file paths yt-dlp wrote for a video or playlist info dict."""
    return YtDlpInfoAdapter.to_media(info).accept(DownloadedFilesCollector())
