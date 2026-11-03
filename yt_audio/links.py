"""Reading the list of links to download.

Pattern: Iterator. iter_links() yields links lazily, one line at a time.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

LinksPath = str | os.PathLike[str]


def iter_links(links_file: LinksPath) -> Iterator[str]:
    """Yield URLs from a file, one per line or comma-separated. Lines starting with # are skipped."""
    with open(links_file, encoding="utf-8") as file:
        for line in file:
            if line.lstrip().startswith("#"):
                continue
            for link in line.split(","):
                if link.strip():
                    yield link.strip()


def read_links(links_file: LinksPath) -> list[str]:
    return list(iter_links(links_file))
