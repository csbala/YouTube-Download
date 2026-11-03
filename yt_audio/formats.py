"""The audio formats the downloader can produce.

Patterns:
- Strategy: each AudioFormat knows the yt-dlp arguments that produce it, so no other code branches
  on `if audio_format == "mp3"`.
- Factory Method: AudioFormat.from_name() turns a command-line choice into the matching strategy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar

FFMPEG_MISSING = "ffmpeg is required for mp3 but was not found. Install it with: winget install -e --id Gyan.FFmpeg"


class AudioFormat(ABC):
    name: ClassVar[str]
    description: ClassVar[str]

    @property
    def extension(self) -> str:
        return f".{self.name}"

    @abstractmethod
    def ytdlp_args(self, ffmpeg_dir: str | None) -> list[str]:
        """yt-dlp command-line arguments that pick and produce this format."""

    @staticmethod
    def from_name(name: str) -> AudioFormat:
        try:
            return AUDIO_FORMATS[name]
        except KeyError:
            raise ValueError(f"unknown audio format {name!r}, expected one of {', '.join(AUDIO_FORMATS)}") from None


class Mp3Format(AudioFormat):
    """Converted with ffmpeg. Plays everywhere, including Roll20's jukebox, which accepts only mp3."""

    name = "mp3"
    description = "plays everywhere; needs ffmpeg"

    def ytdlp_args(self, ffmpeg_dir: str | None) -> list[str]:
        if not ffmpeg_dir:
            raise RuntimeError(FFMPEG_MISSING)
        return ["-f", "bestaudio", "-x", "--audio-format", "mp3", "--audio-quality", "192K", "--ffmpeg-location", ffmpeg_dir]


class WebmFormat(AudioFormat):
    """YouTube's own audio stream, saved untouched. No ffmpeg needed, but not every player supports it."""

    name = "webm"
    description = "YouTube's original audio, no conversion"

    def ytdlp_args(self, ffmpeg_dir: str | None) -> list[str]:
        return ["-f", "bestaudio[ext=webm]/bestaudio"]  # Best webm audio, or the best audio of any kind


# Formats hold no per-download state, so every caller shares these instances.
AUDIO_FORMATS: Mapping[str, AudioFormat] = MappingProxyType({fmt.name: fmt for fmt in (Mp3Format(), WebmFormat())})
FORMAT_NAMES = tuple(AUDIO_FORMATS)
DEFAULT_FORMAT = Mp3Format.name
