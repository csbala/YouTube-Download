"""Building and writing a Foundry VTT playlist from the audio files in a folder.

Patterns:
- Prototype: SoundPrototype holds a fully filled-in Foundry sound; clone() copies it per track.
- Bridge: PlaylistWriter (what to write) holds a PlaylistSink (where it goes), and the two vary
  independently: JsonFileSink writes playlist.json, MemorySink keeps it, e.g. for tests or previews.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import urllib.parse
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ..events import EventBus, PlaylistEmpty, PlaylistWritten, console_event_bus
from ..formats import AudioFormat
from ..settings import FOUNDRY_CORE_VERSION
from .paths import FoundryDataLocator, PathLike

PLAYLIST_FILENAME = "playlist.json"

Playlist = dict[str, Any]
Sound = dict[str, Any]


def stable_id(text: str) -> str:
    """16-character ID derived from text, so re-imports keep the same track IDs."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class PlaylistOptions:
    audio_format: str = "webm"
    foundry_root: PathLike | None = None
    volume: float = 0.5
    foundry_folder: str | None = None


class SoundPrototype:
    def __init__(self, template: Sound) -> None:
        self._template = template

    def clone(self, **fields: Any) -> Sound:
        sound = copy.deepcopy(self._template)
        sound.update(fields)
        return sound


FOUNDRY_SOUND = SoundPrototype({
    "name": "",
    "path": "",
    "channel": "music",
    "repeat": False,
    "fade": None,
    "description": "",
    "volume": 0.5,
    "_id": "",
    "playing": False,
    "pausedTime": None,
    "sort": 0,
    "flags": {},
})


class PlaylistAssembler:
    """Builds the playlist dict Foundry imports, one track per audio file in a folder."""

    def __init__(self, events: EventBus | None = None, now: Callable[[], datetime] = datetime.now) -> None:
        self._events = events or console_event_bus()
        self._locator = FoundryDataLocator(self._events)
        self._now = now

    def assemble(self, folder: PathLike, options: PlaylistOptions) -> Playlist:
        audio_format = AudioFormat.from_name(options.audio_format)
        audio_files = sorted(name for name in os.listdir(folder) if audio_format.owns_file(name))
        if not audio_files:
            self._events.notify(PlaylistEmpty(os.fspath(folder), audio_format.extension))

        relative_folder = self._locator.relative_folder(folder, options.foundry_root)
        sounds = [self._sound_for(filename, relative_folder, position, options.volume)
                  for position, filename in enumerate(audio_files)]

        current_time = int(self._now().timestamp() * 1000)
        return {
            "folder": options.foundry_folder,
            "name": os.path.basename(os.path.normpath(folder)),
            "sounds": sounds,
            "channel": "music",
            "mode": 0,
            "playing": False,
            "fade": 2000,
            "sorting": "a",
            "flags": {},
            "_stats": {
                "coreVersion": FOUNDRY_CORE_VERSION,
                "createdTime": current_time,
                "modifiedTime": current_time,
            },
            "description": "",
        }

    @staticmethod
    def _sound_for(filename: str, relative_folder: str, position: int, volume: float) -> Sound:
        # Foundry paths always use forward slashes, even on Windows
        relative_path = f"{relative_folder}/{filename}" if relative_folder else filename
        return FOUNDRY_SOUND.clone(
            name=os.path.splitext(filename)[0],
            path=urllib.parse.quote(relative_path, safe="/"),
            volume=volume,
            _id=stable_id(relative_path),
            sort=position,
        )


class PlaylistSink(ABC):
    @abstractmethod
    def save(self, playlist: Playlist, folder: PathLike) -> str:
        """Store the playlist and return where it went."""


class JsonFileSink(PlaylistSink):
    def __init__(self, filename: str = PLAYLIST_FILENAME) -> None:
        self._filename = filename

    def save(self, playlist: Playlist, folder: PathLike) -> str:
        output_path = os.path.join(folder, self._filename)
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(playlist, file, indent=2)
        return output_path


class MemorySink(PlaylistSink):
    def __init__(self) -> None:
        self.saved: list[Playlist] = []

    def save(self, playlist: Playlist, folder: PathLike) -> str:
        self.saved.append(playlist)
        return f"<memory #{len(self.saved)}>"


class PlaylistWriter:
    def __init__(self, sink: PlaylistSink, events: EventBus | None = None) -> None:
        self._sink = sink
        self._events = events or console_event_bus()
        self._assembler = PlaylistAssembler(self._events)

    def write(self, folder: PathLike, options: PlaylistOptions) -> str:
        playlist = self._assembler.assemble(folder, options)
        location = self._sink.save(playlist, folder)
        self._events.notify(PlaylistWritten(len(playlist["sounds"]), location))
        return location


def build_playlist(folder: PathLike, audio_format: str = "webm", foundry_root: PathLike | None = None,
                   volume: float = 0.5, foundry_folder: str | None = None, events: EventBus | None = None) -> Playlist:
    """Build a Foundry VTT playlist dict from every audio_format file in folder."""
    options = PlaylistOptions(audio_format, foundry_root, volume, foundry_folder)
    return PlaylistAssembler(events).assemble(folder, options)


def write_playlist(folder: PathLike, output_filename: str = PLAYLIST_FILENAME, *, audio_format: str = "webm",
                   foundry_root: PathLike | None = None, volume: float = 0.5, foundry_folder: str | None = None,
                   events: EventBus | None = None) -> str:
    """Write playlist.json into folder and return its path."""
    options = PlaylistOptions(audio_format, foundry_root, volume, foundry_folder)
    return PlaylistWriter(JsonFileSink(output_filename), events).write(folder, options)
