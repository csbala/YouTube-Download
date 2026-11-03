"""YouTube audio downloader with a Foundry VTT playlist generator.

Pattern: Facade. This module is the package's public surface; callers never need the submodules.
"""

from .cli import main
from .doctor import CheckResult, CheckStatus, diagnose
from .download import AudioDownloader, BatchResult, download_audio
from .foundry import build_playlist, foundry_relative_folder, stable_id, write_playlist
from .links import iter_links, read_links

__all__ = [
    "AudioDownloader",
    "BatchResult",
    "CheckResult",
    "CheckStatus",
    "build_playlist",
    "diagnose",
    "download_audio",
    "foundry_relative_folder",
    "iter_links",
    "main",
    "read_links",
    "stable_id",
    "write_playlist",
]
