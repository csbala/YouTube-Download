"""The virtual tabletops the downloader prepares audio for.

Pattern: Abstract Factory. Each VttTarget creates a family of products that belong together: the audio
format that tabletop plays, and the playlist exporter it needs. Foundry gets webm plus playlist.json;
Roll20 gets mp3 and no playlist. VttTarget.for_format() is the factory method that picks one.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import asdict
from typing import Any, ClassVar

from .formats import AUDIO_FORMATS, AudioFormat
from .foundry.paths import PathLike
from .foundry.playlist import PlaylistOptions

WritePlaylist = Callable[..., Any]


class PlaylistExporter(ABC):
    @abstractmethod
    def export(self, folder: PathLike, options: PlaylistOptions) -> None: ...


class FoundryPlaylistExporter(PlaylistExporter):
    def __init__(self, write_playlist: WritePlaylist) -> None:
        self._write_playlist = write_playlist

    def export(self, folder: PathLike, options: PlaylistOptions) -> None:
        self._write_playlist(folder, **asdict(options))


class NoPlaylistExporter(PlaylistExporter):
    def export(self, folder: PathLike, options: PlaylistOptions) -> None:
        pass


class VttTarget(ABC):
    format_name: ClassVar[str]

    def create_audio_format(self) -> AudioFormat:
        return AUDIO_FORMATS[self.format_name]

    @abstractmethod
    def create_playlist_exporter(self, write_playlist: WritePlaylist) -> PlaylistExporter: ...

    @staticmethod
    def for_format(format_name: str) -> VttTarget:
        return next(target for target in VTT_TARGETS if target.format_name == AudioFormat.from_name(format_name).name)


class FoundryTarget(VttTarget):
    format_name = "webm"

    def create_playlist_exporter(self, write_playlist: WritePlaylist) -> PlaylistExporter:
        return FoundryPlaylistExporter(write_playlist)


class Roll20Target(VttTarget):
    """Roll20's jukebox takes mp3 files dragged in by hand, so there's no playlist to write."""
    format_name = "mp3"

    def create_playlist_exporter(self, write_playlist: WritePlaylist) -> PlaylistExporter:
        return NoPlaylistExporter()


VTT_TARGETS: tuple[VttTarget, ...] = (FoundryTarget(), Roll20Target())
