"""The command line: `download` and `doctor`.

Pattern: Command. Each subcommand is an object that declares its own arguments (configure) and runs
itself (execute). main() only parses and dispatches, so adding a subcommand means adding a class.
"""

from __future__ import annotations

import argparse
import os
import sys
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import IntEnum
from typing import ClassVar

from . import doctor, download
from .doctor import CheckResult
from .download import BatchResult
from .formats import AUDIO_FORMATS, DEFAULT_FORMAT, FORMAT_NAMES
from .links import read_links
from .settings import get_settings


class ExitCode(IntEnum):
    SUCCESS = 0
    SOME_LINKS_FAILED = 1  # also: doctor found something blocking
    COULD_NOT_RUN = 2  # bad arguments or a setup error, such as ffmpeg missing for mp3


@dataclass(frozen=True)
class Services:
    """What the commands call into. Tests swap these for recorders."""

    download_audio: Callable[..., BatchResult]
    diagnose: Callable[[], list[CheckResult]]


def default_services() -> Services:
    return Services(download_audio=download.download_audio, diagnose=doctor.diagnose)


def describe_formats() -> str:
    return ", ".join(f"{fmt.name} ({fmt.description})" for fmt in AUDIO_FORMATS.values())


class CliCommand(ABC):
    name: ClassVar[str]
    help: ClassVar[str]

    @abstractmethod
    def configure(self, parser: argparse.ArgumentParser) -> None: ...

    @abstractmethod
    def execute(self, args: argparse.Namespace, services: Services) -> ExitCode: ...


class DownloadCommand(CliCommand):
    name = "download"
    help = "Download the audio of YouTube links into a folder"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("folder", help="Folder to download into")
        parser.add_argument("urls", nargs="*", help="YouTube links. Default: read them from --links")
        parser.add_argument(
            "--links", default=get_settings().links_file, help="File of links used when no URLs are given (default: links.txt)"
        )
        parser.add_argument(
            "--format", choices=FORMAT_NAMES, default=DEFAULT_FORMAT, help=f"Audio format (default {DEFAULT_FORMAT}): {describe_formats()}"
        )
        parser.add_argument("--suffix", default="", help='Text added after each title, e.g. " [EXTENDED]"')
        parser.add_argument(
            "--allow-playlists", action="store_true", help="Download whole YouTube playlists instead of only the linked video"
        )
        parser.add_argument("--archive", action="store_true", help="Skip videos already downloaded into this folder on earlier runs")

    def execute(self, args: argparse.Namespace, services: Services) -> ExitCode:
        links = self._links_to_download(args)
        if links is None:
            print(f"Error: no links given and {args.links} not found. Pass URLs as arguments or create the file.")
            return ExitCode.COULD_NOT_RUN

        try:
            result = services.download_audio(
                links, args.folder, args.format, suffix=args.suffix, allow_playlists=args.allow_playlists, archive=args.archive
            )
        except RuntimeError as error:  # a setup problem, such as ffmpeg missing for mp3
            print(f"Error: {error}")
            return ExitCode.COULD_NOT_RUN

        self._print_summary(links, result)
        return ExitCode.SOME_LINKS_FAILED if result.failed_links else ExitCode.SUCCESS

    @staticmethod
    def _links_to_download(args: argparse.Namespace) -> list[str] | None:
        """The URLs given on the command line, else the links file's contents. None when there are neither."""
        if args.urls:
            return list(args.urls)
        if os.path.isfile(args.links):
            return read_links(args.links)
        return None

    @staticmethod
    def _print_summary(links: list[str], result: BatchResult) -> None:
        downloaded_count = len(links) - len(result.failed_links)
        print(f"\nSummary: {downloaded_count} of {len(links)} links downloaded ({len(result.files)} files).")
        for link in result.failed_links:
            print(f"FAILED: {link}")


class DoctorCommand(CliCommand):
    name = "doctor"
    help = "Check that yt-dlp, Node.js, ffmpeg and cookies.txt are ready"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        pass

    def execute(self, args: argparse.Namespace, services: Services) -> ExitCode:
        """One [OK], [WARN] or [MISSING] line per check, each with its fix. Fails if any check blocks a download."""
        results = services.diagnose()
        for result in results:
            print(result)
        return ExitCode.SOME_LINKS_FAILED if any(result.blocks_download for result in results) else ExitCode.SUCCESS


COMMANDS: tuple[CliCommand, ...] = (DownloadCommand(), DoctorCommand())


def build_parser(commands: Sequence[CliCommand] = COMMANDS) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download the audio of YouTube videos as mp3 or webm")
    subparsers = parser.add_subparsers(dest="command_name", required=True)
    for command in commands:
        command_parser = subparsers.add_parser(command.name, help=command.help)
        command.configure(command_parser)
        command_parser.set_defaults(command=command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    command: CliCommand = args.command
    return int(command.execute(args, default_services()))
