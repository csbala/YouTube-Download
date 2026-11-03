"""Finding the external tools yt-dlp needs: Node.js (YouTube's JS challenge) and ffmpeg (mp3 conversion).

Patterns:
- Chain of Responsibility: each ToolLookup tries one place and otherwise passes the search to the next.
- Proxy: CachingToolLocator stands in for a ToolLocator and runs each lookup only once.
"""
from __future__ import annotations

import functools
import glob
import importlib.util
import os
import shutil
from abc import ABC, abstractmethod
from typing import Protocol

NODE_DEFAULT_INSTALL = r"C:\Program Files\nodejs\node.exe"


class ToolLookup(ABC):
    """One link in a lookup chain. Returns the tool's path, or asks the next link."""

    def __init__(self) -> None:
        self._next: ToolLookup | None = None

    def then(self, next_lookup: ToolLookup) -> ToolLookup:
        """Set the next link and return it, so chains read left to right: a.then(b).then(c)."""
        self._next = next_lookup
        return next_lookup

    def locate(self) -> str | None:
        found = self._try_locate()
        if found:
            return found
        return self._next.locate() if self._next else None

    @abstractmethod
    def _try_locate(self) -> str | None: ...


class SystemPathLookup(ToolLookup):
    """Looks for the executable on PATH."""

    def __init__(self, executable: str) -> None:
        super().__init__()
        self._executable = executable

    def _try_locate(self) -> str | None:
        return shutil.which(self._executable)


class KnownLocationLookup(ToolLookup):
    """Looks at one fixed install location."""

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path

    def _try_locate(self) -> str | None:
        return self._path if os.path.isfile(self._path) else None


class WingetPackageLookup(ToolLookup):
    """Looks where winget unpacks portable packages. Those aren't on PATH until a new shell starts.
    Several versions can be installed side by side, so the newest one wins."""

    def __init__(self, package_pattern: str, executable: str) -> None:
        super().__init__()
        self._package_pattern = package_pattern
        self._executable = executable

    def _try_locate(self) -> str | None:
        packages = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet", "Packages")
        matches = glob.glob(os.path.join(packages, self._package_pattern, "*", "bin", self._executable))
        return max(matches, key=os.path.getmtime) if matches else None


def node_lookup_chain() -> ToolLookup:
    head = SystemPathLookup("node")
    head.then(KnownLocationLookup(NODE_DEFAULT_INSTALL))
    return head


def ffmpeg_lookup_chain() -> ToolLookup:
    head = SystemPathLookup("ffmpeg")
    head.then(WingetPackageLookup("Gyan.FFmpeg*", "ffmpeg.exe"))
    return head


class ToolLocator(Protocol):
    def node_path(self) -> str | None:
        """Path of the node executable, or None."""
        ...

    def ffmpeg_dir(self) -> str | None:
        """Folder holding the ffmpeg executable (what yt-dlp's --ffmpeg-location wants), or None."""
        ...

    def ejs_installed(self) -> bool:
        """True if yt-dlp-ejs, the bundled YouTube challenge solver, is installed."""
        ...


class SystemToolLocator:
    """Looks at the real machine every time it's asked."""

    def node_path(self) -> str | None:
        return node_lookup_chain().locate()

    def ffmpeg_dir(self) -> str | None:
        executable = ffmpeg_lookup_chain().locate()
        return os.path.dirname(executable) if executable else None

    def ejs_installed(self) -> bool:
        return importlib.util.find_spec("yt_dlp_ejs") is not None


class CachingToolLocator:
    """Proxy for another ToolLocator that remembers each answer."""

    def __init__(self, real_locator: ToolLocator) -> None:
        self._real_locator = real_locator

    @functools.cache  # noqa: B019 - one locator per run, so the cache can't outlive what it describes
    def node_path(self) -> str | None:
        return self._real_locator.node_path()

    @functools.cache  # noqa: B019
    def ffmpeg_dir(self) -> str | None:
        return self._real_locator.ffmpeg_dir()

    @functools.cache  # noqa: B019
    def ejs_installed(self) -> bool:
        return self._real_locator.ejs_installed()


def default_tool_locator() -> ToolLocator:
    """The locator used when none is passed in. Tests replace this function to fake the tools."""
    return CachingToolLocator(SystemToolLocator())
