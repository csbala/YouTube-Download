"""The audio formats the downloader can produce.

Patterns:
- Strategy: each AudioFormat knows its yt-dlp format arguments and which files are its own.
- Factory Method: AudioFormat.from_name() turns a command-line choice into a strategy.
- Flyweight: formats hold no per-download state, so one shared instance per format lives in AUDIO_FORMATS.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar

FFMPEG_MISSING = "ffmpeg is required for mp3 but was not found. Install it with: winget install -e --id Gyan.FFmpeg"


class AudioFormat(ABC):
    name: ClassVar[str]

    @property
    def extension(self) -> str:
        return f".{self.name}"

    def owns_file(self, filename: str) -> bool:
        return filename.lower().endswith(self.extension)

    @abstractmethod
    def ydl_args(self, ffmpeg_dir: str | None) -> list[str]:
        """yt-dlp command-line arguments that pick and produce this format."""

    @staticmethod
    def from_name(name: str) -> AudioFormat:
        try:
            return AUDIO_FORMATS[name]
        except KeyError:
            raise ValueError(f"unknown audio format {name!r}, expected one of {', '.join(AUDIO_FORMATS)}") from None


class WebmFormat(AudioFormat):
    """YouTube's own audio stream, untouched. Foundry VTT plays it directly."""
    name = "webm"

    def ydl_args(self, ffmpeg_dir: str | None) -> list[str]:
        return ["-f", "bestaudio[ext=webm]/bestaudio"]  # Best webm audio, fallback to best audio


class Mp3Format(AudioFormat):
    """Converted with ffmpeg, because Roll20's jukebox only accepts mp3."""
    name = "mp3"

    def ydl_args(self, ffmpeg_dir: str | None) -> list[str]:
        if not ffmpeg_dir:
            raise RuntimeError(FFMPEG_MISSING)
        return ["-f", "bestaudio", "-x", "--audio-format", "mp3", "--audio-quality", "192K", "--ffmpeg-location", ffmpeg_dir]


AUDIO_FORMATS: Mapping[str, AudioFormat] = MappingProxyType({fmt.name: fmt for fmt in (WebmFormat(), Mp3Format())})
FORMAT_NAMES = tuple(AUDIO_FORMATS)
