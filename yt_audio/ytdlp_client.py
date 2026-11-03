"""Fetching one link with yt-dlp.

Pattern: Decorator. ErrorTranslatingClient wraps any MediaClient and turns the errors yt-dlp and the
filesystem raise into a LinkFailed result, so the batch loop never needs try/except.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Protocol

from .media import MediaNode, YtDlpInfoAdapter


@dataclass(frozen=True)
class LinkFetched:
    media: MediaNode


@dataclass(frozen=True)
class LinkFailed:
    reason: str | None  # None when yt-dlp has already printed its own ERROR line


FetchResult = LinkFetched | LinkFailed


class MediaClient(Protocol):
    def fetch(self, link: str) -> FetchResult: ...


class YtDlpClient:
    """Downloads with an open yt_dlp.YoutubeDL. Lets its errors through."""

    def __init__(self, youtube_dl: Any) -> None:
        self._youtube_dl = youtube_dl

    def fetch(self, link: str) -> FetchResult:
        return LinkFetched(YtDlpInfoAdapter.to_media(self._youtube_dl.extract_info(link, download=True)))


class ErrorTranslatingClient:
    def __init__(self, wrapped: MediaClient) -> None:
        self._wrapped = wrapped

    def fetch(self, link: str) -> FetchResult:
        import yt_dlp

        try:
            return self._wrapped.fetch(link)
        except yt_dlp.utils.DownloadError:
            return LinkFailed(reason=None)
        except OSError as error:
            return LinkFailed(reason=str(error))


@contextmanager
def open_ytdlp_client(ytdlp_options: dict[str, Any]) -> Iterator[MediaClient]:
    import yt_dlp

    with yt_dlp.YoutubeDL(ytdlp_options) as youtube_dl:
        yield ErrorTranslatingClient(YtDlpClient(youtube_dl))
