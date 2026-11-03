"""Where a music folder sits inside Foundry VTT's Data folder.

Pattern: Iterator. iter_folder_and_ancestors() walks up from a folder to the drive root.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

from ..events import EventBus, FoundryRootGuessed, console_event_bus

FALLBACK_PARENT = "Music_Import"
PathLike = str | os.PathLike[str]


def iter_folder_and_ancestors(folder: str) -> Iterator[str]:
    while True:
        yield folder
        parent = os.path.dirname(folder)
        if parent == folder:
            return
        folder = parent


class FoundryDataLocator:
    def __init__(self, events: EventBus | None = None) -> None:
        self._events = events or console_event_bus()

    @staticmethod
    def is_foundry_data_folder(path: str) -> bool:
        """True for a folder named Data that sits next to Foundry's Config folder or inside a folder named like Foundry.
        That keeps an unrelated folder such as C:\\data from being taken for Foundry's."""
        if os.path.basename(path).lower() != "data":
            return False
        parent = os.path.dirname(path)
        return os.path.isdir(os.path.join(parent, "Config")) or "foundry" in os.path.basename(parent).lower()

    def find_enclosing_data_folder(self, folder: str) -> str | None:
        """The folder itself or the nearest enclosing Foundry Data folder, e.g. for ...\\FoundryVTT\\Data\\Music_Import\\apple."""
        return next((candidate for candidate in iter_folder_and_ancestors(folder) if self.is_foundry_data_folder(candidate)), None)

    def relative_folder(self, folder: PathLike, foundry_root: PathLike | None = None) -> str:
        """Path of folder relative to Foundry's Data folder, with forward slashes."""
        folder = os.path.abspath(folder)
        root = os.fspath(foundry_root) if foundry_root is not None else self.find_enclosing_data_folder(folder)
        if root is None:
            assumed_folder = f"{FALLBACK_PARENT}/{os.path.basename(folder)}"
            self._events.notify(FoundryRootGuessed(folder, assumed_folder))
            return assumed_folder

        try:
            relative = os.path.relpath(folder, os.path.abspath(root))
        except ValueError:  # Different Windows drives
            relative = os.pardir
        if relative == os.pardir or relative.startswith(os.pardir + os.sep):
            raise ValueError(f"{folder} is not inside the Foundry root {root}")
        return "" if relative == os.curdir else relative.replace(os.sep, "/")


def foundry_relative_folder(folder: PathLike, foundry_root: PathLike | None = None, events: EventBus | None = None) -> str:
    return FoundryDataLocator(events).relative_folder(folder, foundry_root)
