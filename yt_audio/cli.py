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
from dataclasses import dataclass, replace
from enum import IntEnum
from typing import ClassVar

from . import doctor, download
from .doctor import CheckResult
from .download import BatchResult, DownloadInterrupted
from .events import BatchFinished, RunFailed, console_event_bus, json_event_bus
from .formats import AUDIO_FORMATS, DEFAULT_FORMAT, FORMAT_NAMES
from .links import read_links
from .settings import HOME_ENV_VAR, AppSettings, get_settings
from .version import describe_version


class ExitCode(IntEnum):
    SUCCESS = 0
    SOME_LINKS_FAILED = 1  # also: doctor found something blocking
    COULD_NOT_RUN = 2  # bad arguments or a setup error, such as ffmpeg missing for mp3
    INTERRUPTED = 130  # Ctrl+C; the usual shell convention (128 + SIGINT)


@dataclass(frozen=True)
class Services:
    """What the commands call into. Tests swap these for recorders."""

    download_audio: Callable[..., BatchResult]
    diagnose: Callable[..., list[CheckResult]]  # called as diagnose(settings=...)


def default_services() -> Services:
    return Services(download_audio=download.download_audio, diagnose=doctor.diagnose)


def add_cookies_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--cookies",
        metavar="FILE",
        help=f"cookies.txt to use (default: {get_settings().cookies_file}; set {HOME_ENV_VAR} to move the default folder)",
    )


def settings_from(args: argparse.Namespace) -> AppSettings:
    """The current settings, with --cookies applied."""
    settings = get_settings()
    return replace(settings, cookies_file=args.cookies) if args.cookies else settings


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
            "--links",
            default=get_settings().links_file,
            help=f"File of links used when no URLs are given (default: {get_settings().links_file})",
        )
        add_cookies_argument(parser)
        parser.add_argument(
            "--format", choices=FORMAT_NAMES, default=DEFAULT_FORMAT, help=f"Audio format (default {DEFAULT_FORMAT}): {describe_formats()}"
        )
        parser.add_argument("--suffix", default="", help='Text added after each title, e.g. " [EXTENDED]"')
        parser.add_argument(
            "--allow-playlists", action="store_true", help="Download whole YouTube playlists instead of only the linked video"
        )
        parser.add_argument("--archive", action="store_true", help="Skip videos already downloaded into this folder on earlier runs")
        parser.add_argument(
            "--no-tags",
            dest="embed_tags",
            action="store_false",
            help="Don't write title, artist and cover art into mp3/m4a files (webm is never tagged)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Print progress and the summary as JSON lines on stdout, for scripts; yt-dlp's errors still go to stderr",
        )

    def execute(self, args: argparse.Namespace, services: Services) -> ExitCode:
        events = json_event_bus() if args.json else console_event_bus()
        links = self._links_to_download(args)
        if not links:
            events.notify(RunFailed(self._why_no_links(args)))
            return ExitCode.COULD_NOT_RUN

        try:
            result = services.download_audio(
                links,
                args.folder,
                args.format,
                suffix=args.suffix,
                allow_playlists=args.allow_playlists,
                archive=args.archive,
                embed_tags=args.embed_tags,
                quiet=args.json,
                events=events,
                settings=settings_from(args),
            )
        except RuntimeError as error:  # a setup problem, such as ffmpeg missing for mp3
            events.notify(RunFailed(str(error)))
            return ExitCode.COULD_NOT_RUN
        except DownloadInterrupted as interrupted:
            events.notify(self._summary(links, interrupted.partial, interrupted.unfinished))
            return ExitCode.INTERRUPTED

        events.notify(self._summary(links, result))
        return ExitCode.SOME_LINKS_FAILED if result.failed_links else ExitCode.SUCCESS

    @staticmethod
    def _links_to_download(args: argparse.Namespace) -> list[str]:
        """The URLs given on the command line, else the links file's contents, else nothing."""
        if args.urls:
            return list(args.urls)
        if os.path.isfile(args.links):
            return read_links(args.links)
        return []

    @staticmethod
    def _why_no_links(args: argparse.Namespace) -> str:
        if os.path.isfile(args.links):
            return f"no links given and {args.links} has no links in it. Pass URLs as arguments or add links to the file."
        return f"no links given and {args.links} not found. Pass URLs as arguments or create the file."

    @staticmethod
    def _summary(links: list[str], result: BatchResult, unfinished: Sequence[str] = ()) -> BatchFinished:
        return BatchFinished(len(links), tuple(result.files), tuple(result.failed_links), tuple(unfinished))


class DoctorCommand(CliCommand):
    name = "doctor"
    help = "Check that yt-dlp, Node.js, ffmpeg and cookies.txt are ready"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        add_cookies_argument(parser)

    def execute(self, args: argparse.Namespace, services: Services) -> ExitCode:
        """One [OK], [WARN] or [MISSING] line per check, each with its fix. Fails if any check blocks a download."""
        results = services.diagnose(settings=settings_from(args))
        for result in results:
            print(result)
        return ExitCode.SOME_LINKS_FAILED if any(result.blocks_download for result in results) else ExitCode.SUCCESS


COMMANDS: tuple[CliCommand, ...] = (DownloadCommand(), DoctorCommand())


def build_parser(commands: Sequence[CliCommand] = COMMANDS) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Download the audio of YouTube videos as mp3, m4a or webm")
    parser.add_argument("--version", action="version", version=describe_version())
    subparsers = parser.add_subparsers(dest="command_name", required=True)
    for command in commands:
        command_parser = subparsers.add_parser(command.name, help=command.help)
        command.configure(command_parser)
        command_parser.set_defaults(command=command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(sys.argv[1:] if argv is None else argv)
    command: CliCommand = args.command
    try:
        return int(command.execute(args, default_services()))
    except KeyboardInterrupt:  # Ctrl+C outside a batch, e.g. while the doctor runs: no traceback
        print("\nStopped by Ctrl+C.")
        return int(ExitCode.INTERRUPTED)
