"""Fetching one link with yt-dlp.

Pattern: Decorator. ErrorTranslatingClient wraps any MediaClient and turns the errors yt-dlp and the
filesystem raise into a LinkFailed result, so the batch loop never needs try/except.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from typing import Any, Protocol

from .media import MediaNode, YtDlpInfoAdapter


@dataclass(frozen=True)
class LinkFetched:
    media: MediaNode


@dataclass(frozen=True)
class LinkFailed:
    reason: str
    already_printed: bool = False  # True when yt-dlp printed its own ERROR line for it


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
        except yt_dlp.utils.DownloadError as error:
            return LinkFailed(reason=str(error).removeprefix("ERROR: "), already_printed=True)
        except OSError as error:
            return LinkFailed(reason=str(error))


@contextmanager
def private_cookie_copy(cookies_file: str | None) -> Iterator[str | None]:
    """A temporary copy of cookies_file, deleted afterwards.

    yt-dlp saves its cookie jar back to the cookie file when it closes. Handing it a copy keeps the
    user's exported login untouched (a crash can't corrupt it), and keeps its modified time honest
    for the doctor's "cookies are getting old" check. mkstemp makes the copy readable only by the user.
    """
    if not cookies_file:
        yield None
        return
    handle, copy_path = tempfile.mkstemp(prefix="yt-audio-cookies-", suffix=".txt")
    try:
        with os.fdopen(handle, "wb") as copy, open(cookies_file, "rb") as original:
            shutil.copyfileobj(original, copy)
        yield copy_path
    finally:
        with suppress(OSError):
            os.remove(copy_path)


@contextmanager
def open_ytdlp_client(ytdlp_options: dict[str, Any]) -> Iterator[MediaClient]:
    import yt_dlp

    with private_cookie_copy(ytdlp_options.get("cookiefile")) as cookie_copy:
        options = {**ytdlp_options, "cookiefile": cookie_copy} if cookie_copy else ytdlp_options
        with yt_dlp.YoutubeDL(options) as youtube_dl:
            yield ErrorTranslatingClient(YtDlpClient(youtube_dl))
