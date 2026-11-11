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

FFMPEG_MISSING = "ffmpeg is required for {name} but was not found. Install it with: winget install -e --id Gyan.FFmpeg"
AUDIO_QUALITY = "192K"  # Only used when ffmpeg has to re-encode


class AudioFormat(ABC):
    name: ClassVar[str]
    description: ClassVar[str]

    @property
    def extension(self) -> str:
        return f".{self.name}"

    @abstractmethod
    def ytdlp_args(self, ffmpeg_dir: str | None) -> list[str]:
        """yt-dlp command-line arguments that pick and produce this format."""

    def tag_args(self) -> list[str]:
        """yt-dlp arguments that write title, artist and cover art into the file. None by default."""
        return []

    @staticmethod
    def from_name(name: str) -> AudioFormat:
        try:
            return AUDIO_FORMATS[name]
        except KeyError:
            raise ValueError(f"unknown audio format {name!r}, expected one of {', '.join(AUDIO_FORMATS)}") from None


class FfmpegExtractedFormat(AudioFormat):
    """Picks a source stream, then has ffmpeg turn it into this format and tag it.
    When the source is already in this codec, ffmpeg copies it instead of re-encoding."""

    source_selector: ClassVar[str]

    def ytdlp_args(self, ffmpeg_dir: str | None) -> list[str]:
        if not ffmpeg_dir:
            raise RuntimeError(FFMPEG_MISSING.format(name=self.name))
        return [
            "-f",
            self.source_selector,
            "-x",
            "--audio-format",
            self.name,
            "--audio-quality",
            AUDIO_QUALITY,
            "--ffmpeg-location",
            ffmpeg_dir,
        ]

    def tag_args(self) -> list[str]:
        # Cover art is the video thumbnail; yt-dlp converts YouTube's webp thumbnails as needed
        return ["--embed-metadata", "--embed-thumbnail"]


class Mp3Format(FfmpegExtractedFormat):
    """Converted with ffmpeg. Plays everywhere, including Roll20's jukebox, which accepts only mp3."""

    name = "mp3"
    description = "plays everywhere; needs ffmpeg"
    source_selector = "bestaudio"


class M4aFormat(FfmpegExtractedFormat):
    """YouTube's AAC stream, usually just repackaged, so no quality is lost to re-encoding."""

    name = "m4a"
    description = "AAC, original quality, plays almost everywhere; needs ffmpeg"
    source_selector = "bestaudio[ext=m4a]/bestaudio"


class WebmFormat(AudioFormat):
    """YouTube's own audio stream, saved untouched. No ffmpeg needed, but not every player supports it.
    Untagged: yt-dlp can't embed cover art in webm, and tagging would need ffmpeg."""

    name = "webm"
    description = "YouTube's original audio, no conversion"

    def ytdlp_args(self, ffmpeg_dir: str | None) -> list[str]:
        return ["-f", "bestaudio[ext=webm]/bestaudio"]  # Best webm audio, or the best audio of any kind


# Formats hold no per-download state, so every caller shares these instances.
AUDIO_FORMATS: Mapping[str, AudioFormat] = MappingProxyType({fmt.name: fmt for fmt in (Mp3Format(), M4aFormat(), WebmFormat())})
FORMAT_NAMES = tuple(AUDIO_FORMATS)
DEFAULT_FORMAT = Mp3Format.name
