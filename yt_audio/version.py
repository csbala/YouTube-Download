"""The package version. pyproject.toml reads it from here, so it's defined once."""

from __future__ import annotations

import importlib.metadata
import platform

__version__ = "3.1.0"


def describe_version() -> str:
    """What `--version` prints: this package, yt-dlp and Python, which is what a bug report needs."""
    try:
        ytdlp_version = importlib.metadata.version("yt-dlp")
    except importlib.metadata.PackageNotFoundError:
        ytdlp_version = "not installed"
    return f"yt-audio {__version__} (yt-dlp {ytdlp_version}, Python {platform.python_version()})"
