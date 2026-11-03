"""Turning a download request into yt-dlp options.

Patterns:
- Builder: YdlOptionsBuilder adds one concern per step, using the same flags the yt-dlp command line takes.
- Director: YdlOptionsDirector knows which steps a download needs and in what order, and reports
  missing optional tools on the way.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from . import tools
from .events import CookiesMissing, EventBus, NodeMissing, console_event_bus
from .formats import AudioFormat
from .settings import MAX_TITLE_LENGTH, MIN_TITLE_LENGTH, WINDOWS_PATH_BUDGET, AppSettings, get_settings
from .tools import ToolLocator

ARCHIVE_FILENAME = ".download-archive.txt"

YdlOptions = dict[str, Any]


@dataclass(frozen=True)
class DownloadRequest:
    folder: str
    audio_format: AudioFormat
    title_suffix: str = ""
    allow_playlists: bool = False
    use_archive: bool = False

    @property
    def empty_result_is_failure(self) -> bool:
        """A playlist that downloaded nothing failed, unless the archive skipped it all."""
        return self.allow_playlists and not self.use_archive


def max_title_length(folder: str) -> int:
    """Longest title to use for files in folder, so the full path stays under Windows' 260-character
    limit, with room for the extension and yt-dlp's .part suffix. Never below MIN_TITLE_LENGTH."""
    return max(MIN_TITLE_LENGTH, min(MAX_TITLE_LENGTH, WINDOWS_PATH_BUDGET - len(os.path.abspath(folder))))


class YdlOptionsBuilder:
    def __init__(self) -> None:
        self._args: list[str] = []
        self._keep_going_past_broken_entries = False

    def with_output_template(self, folder: str, title_suffix: str) -> YdlOptionsBuilder:
        self._args += [
            "-P",
            folder,  # Kept out of -o, because --trim-filenames would trim the folder path too
            "-o",
            f"%(title)s{title_suffix.replace('%', '%%')}.%(ext)s",  # % is special in templates
            "--trim-filenames",
            str(max_title_length(folder)),
        ]
        return self

    def with_challenge_solver(self, ejs_installed: bool) -> YdlOptionsBuilder:
        if not ejs_installed:
            # Without the yt-dlp-ejs package, fetch YouTube's challenge solver from GitHub on every run
            self._args += ["--remote-components", "ejs:github"]
        return self

    def with_playlist_policy(self, allow_playlists: bool) -> YdlOptionsBuilder:
        if not allow_playlists:
            self._args.append("--no-playlist")  # Only the video a link points at, even if it's in a playlist
        self._keep_going_past_broken_entries = allow_playlists
        return self

    def with_js_runtime(self, node_path: str | None) -> YdlOptionsBuilder:
        if node_path:
            self._args += ["--js-runtimes", f"node:{node_path}"]
        return self

    def with_audio_format(self, audio_format: AudioFormat, ffmpeg_dir: str | None) -> YdlOptionsBuilder:
        self._args += audio_format.ydl_args(ffmpeg_dir)
        return self

    def with_cookies(self, cookies_file: str | None) -> YdlOptionsBuilder:
        if cookies_file:
            self._args += ["--cookies", cookies_file]
        return self

    def with_archive(self, folder: str, use_archive: bool) -> YdlOptionsBuilder:
        if use_archive:
            # Remembers finished videos so later runs skip them, even if the file was renamed
            self._args += ["--download-archive", os.path.join(folder, ARCHIVE_FILENAME)]
        return self

    def build(self) -> YdlOptions:
        import yt_dlp  # Imported late so `doctor` still runs when yt-dlp isn't installed

        options: YdlOptions = yt_dlp.parse_options(self._args).ydl_opts
        # Raise on a failed single video so it's counted. In playlists, keep going past broken entries.
        options["ignoreerrors"] = "only_download" if self._keep_going_past_broken_entries else False
        return options


class YdlOptionsDirector:
    def __init__(
        self, tool_locator: ToolLocator | None = None, events: EventBus | None = None, settings: AppSettings | None = None
    ) -> None:
        self._tools = tool_locator or tools.default_tool_locator()
        self._events = events or console_event_bus()
        self._settings = settings

    def options_for(self, request: DownloadRequest) -> YdlOptions:
        settings = self._settings or get_settings()
        node_path = self._tools.node_path()
        if not node_path:
            self._events.notify(NodeMissing())
        builder = (
            YdlOptionsBuilder()
            .with_output_template(request.folder, request.title_suffix)
            .with_challenge_solver(self._tools.ejs_installed())
            .with_playlist_policy(request.allow_playlists)
            .with_js_runtime(node_path)
            .with_audio_format(request.audio_format, self._tools.ffmpeg_dir())
        )

        cookies_file: str | None = settings.cookies_file
        if not os.path.isfile(settings.cookies_file):
            self._events.notify(CookiesMissing(settings.cookies_file))
            cookies_file = None
        return builder.with_cookies(cookies_file).with_archive(request.folder, request.use_archive).build()
