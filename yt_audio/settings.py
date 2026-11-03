"""Paths and constants shared by the whole package.

Patterns:
- Singleton: SettingsHolder keeps the one AppSettings the process uses (thread-safe).
- Memento: SettingsHolder.save() / restore() snapshot and roll back the settings, which is what
  override_settings() uses so tests never read the user's real cookies.txt or links.txt.
"""
from __future__ import annotations

import os
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from typing import Any

# The folder holding downloader.py and the yt_audio package. cookies.txt and links.txt live here.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FOUNDRY_CORE_VERSION = "12.331"
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
    def for_project(cls, project_root: str = PROJECT_ROOT) -> AppSettings:
        return cls(
            cookies_file=os.path.join(project_root, "cookies.txt"),
            links_file=os.path.join(project_root, "links.txt"),
        )


@dataclass(frozen=True)
class SettingsMemento:
    """An opaque snapshot of the settings, handed back to SettingsHolder.restore()."""
    _state: AppSettings


class SettingsHolder:
    """Singleton holder of the current AppSettings."""
    _instance: SettingsHolder | None = None
    _lock = threading.Lock()
    _settings: AppSettings

    def __new__(cls) -> SettingsHolder:
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._settings = AppSettings.for_project()
                cls._instance = instance
            return cls._instance

    @property
    def settings(self) -> AppSettings:
        return self._settings

    def update(self, **changes: Any) -> None:
        self._settings = replace(self._settings, **changes)

    def save(self) -> SettingsMemento:
        return SettingsMemento(self._settings)

    def restore(self, memento: SettingsMemento) -> None:
        self._settings = memento._state


def get_settings() -> AppSettings:
    return SettingsHolder().settings


@contextmanager
def override_settings(**changes: Any) -> Iterator[AppSettings]:
    """Temporarily change settings, e.g. override_settings(cookies_file=...). Restores them on exit."""
    holder = SettingsHolder()
    memento = holder.save()
    holder.update(**changes)
    try:
        yield holder.settings
    finally:
        holder.restore(memento)
