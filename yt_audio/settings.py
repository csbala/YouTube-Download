"""Paths and constants shared by the whole package.

The current AppSettings is a plain module-level value: get_settings() reads it and override_settings()
swaps it for a while. Code that needs other settings can also take an AppSettings argument instead.
"""

from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any

# The folder holding the yt_audio package: the repo, when running from a checkout
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME_ENV_VAR = "YT_AUDIO_HOME"

MIN_YT_DLP_VERSION = "2025.11.12"  # First release with --js-runtimes and --remote-components

MAX_TITLE_LENGTH = 150
MIN_TITLE_LENGTH = 40
# Windows' MAX_PATH is 260; keep 20 characters for the extension and yt-dlp's .part suffix
WINDOWS_PATH_BUDGET = 240


@dataclass(frozen=True)
class AppSettings:
    cookies_file: str
    links_file: str

    @classmethod
    def in_folder(cls, folder: str) -> AppSettings:
        return cls(cookies_file=os.path.join(folder, "cookies.txt"), links_file=os.path.join(folder, "links.txt"))

    @classmethod
    def for_project(cls, project_root: str = PROJECT_ROOT) -> AppSettings:
        return cls.in_folder(project_root)

    @classmethod
    def default(cls) -> AppSettings:
        return cls.in_folder(user_files_dir())


def user_files_dir(environ: Mapping[str, str] = os.environ, project_root: str = PROJECT_ROOT, os_name: str = os.name) -> str:
    """Where cookies.txt and links.txt live:
    1. $YT_AUDIO_HOME, when set;
    2. the repo, when running from a checkout (next to downloader.py), as before;
    3. otherwise (installed with pip or pipx) the user's config folder: %APPDATA%\\yt-audio on Windows,
       $XDG_CONFIG_HOME/yt-audio or ~/.config/yt-audio elsewhere.
    """
    if environ.get(HOME_ENV_VAR):
        return environ[HOME_ENV_VAR]
    if os.path.isfile(os.path.join(project_root, "downloader.py")):
        return project_root
    home = environ.get("USERPROFILE" if os_name == "nt" else "HOME") or os.path.expanduser("~")
    if os_name == "nt":
        return os.path.join(environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming"), "yt-audio")
    return os.path.join(environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config"), "yt-audio")


_current: AppSettings | None = None  # set on first use, so importing the package touches no files


def get_settings() -> AppSettings:
    """The settings this process uses: the defaults, unless override_settings() is active."""
    global _current
    if _current is None:
        _current = AppSettings.default()
    return _current


@contextmanager
def override_settings(**changes: Any) -> Iterator[AppSettings]:
    """Temporarily change settings, e.g. override_settings(cookies_file=...). Restores them on exit,
    which is how tests keep away from the user's real cookies.txt and links.txt."""
    global _current
    previous = get_settings()
    _current = replace(previous, **changes)
    try:
        yield _current
    finally:
        _current = previous
