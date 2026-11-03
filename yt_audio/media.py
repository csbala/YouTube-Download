"""What a link turned into: one video, or a (possibly nested) playlist with some broken entries.

Patterns:
- Adapter: YtDlpInfoAdapter turns yt-dlp's raw info dicts into the typed tree below, so no other
  module needs to know about "entries", None entries or "requested_downloads".
- Composite: VideoNode, FailedEntryNode and PlaylistNode share the MediaNode interface, so a single
  video and a playlist of playlists are handled the same way.
- Iterator: MediaNode.iter_videos() walks the tree lazily.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntryCount:
    """How many entries a media tree holds, and how many of them yt-dlp couldn't download."""

    total: int
    failed: int

    def __add__(self, other: EntryCount) -> EntryCount:
        return EntryCount(self.total + other.total, self.failed + other.failed)


class MediaNode(ABC):
    @abstractmethod
    def iter_videos(self) -> Iterator[VideoNode]:
        """Every downloaded video in the tree, in playlist order."""

    @abstractmethod
    def count_entries(self) -> EntryCount: ...

    def downloaded_files(self) -> list[str]:
        return [path for video in self.iter_videos() for path in video.files]


@dataclass(frozen=True)
class VideoNode(MediaNode):
    video_id: str | None
    title: str | None
    files: tuple[str, ...]

    def iter_videos(self) -> Iterator[VideoNode]:
        yield self

    def count_entries(self) -> EntryCount:
        return EntryCount(total=1, failed=0)


@dataclass(frozen=True)
class FailedEntryNode(MediaNode):
    """A playlist entry yt-dlp couldn't download."""

    def iter_videos(self) -> Iterator[VideoNode]:
        yield from ()

    def count_entries(self) -> EntryCount:
        return EntryCount(total=1, failed=1)


@dataclass(frozen=True)
class PlaylistNode(MediaNode):
    children: tuple[MediaNode, ...]

    def iter_videos(self) -> Iterator[VideoNode]:
        for child in self.children:
            yield from child.iter_videos()

    def count_entries(self) -> EntryCount:
        return sum((child.count_entries() for child in self.children), EntryCount(0, 0))


NOTHING_DOWNLOADED = PlaylistNode(children=())


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
