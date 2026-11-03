"""Command-line entry point: python downloader.py <download|doctor> ...

The code lives in the yt_audio package next to this file.
"""

import sys

from yt_audio.cli import main

if __name__ == "__main__":
    sys.exit(main())
