"""Download the audio of YouTube videos as mp3, m4a or webm.

Pattern: Facade. This module is the package's public surface; callers never need the submodules.
"""

from .cli import main
from .doctor import CheckResult, CheckStatus, diagnose
from .download import AudioDownloader, BatchResult, download_audio
from .formats import DEFAULT_FORMAT, FORMAT_NAMES
from .links import iter_links, read_links
from .version import __version__

__all__ = [
    "DEFAULT_FORMAT",
    "FORMAT_NAMES",
    "AudioDownloader",
    "BatchResult",
    "CheckResult",
    "CheckStatus",
    "__version__",
    "diagnose",
    "download_audio",
    "iter_links",
    "main",
    "read_links",
]
