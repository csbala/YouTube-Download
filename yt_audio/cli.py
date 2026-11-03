"""The command line: `download`, `playlist` and `doctor`.

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
from typing import Any, ClassVar

from . import doctor, download
from .doctor import CheckResult
from .formats import FORMAT_NAMES
from .foundry import playlist
from .foundry.playlist import PlaylistOptions
from .links import read_links
from .settings import get_settings
from .targets import FoundryPlaylistExporter, NoPlaylistExporter, PlaylistExporter, VttTarget


class ExitCode(IntEnum):
    SUCCESS = 0
    SOME_LINKS_FAILED = 1   # also: doctor found something blocking
    COULD_NOT_RUN = 2       # bad arguments, setup error, or playlist.json couldn't be written


@dataclass(frozen=True)
class Services:
    """What the commands call into. Tests swap these for recorders."""
    download_audio: Callable[..., download.BatchResult]
    write_playlist: Callable[..., Any]
    diagnose: Callable[[], list[CheckResult]]


def default_services() -> Services:
    return Services(download_audio=download.download_audio, write_playlist=playlist.write_playlist,
                    diagnose=doctor.diagnose)


def parse_volume(text: str) -> float:
    """argparse type for --volume: a number from 0 to 1."""
    try:
        value = float(text)
    except ValueError:
        value = None
    if value is None or not 0 <= value <= 1:
        raise argparse.ArgumentTypeError(f"must be a number from 0 to 1, not {text}")
    return value


def add_playlist_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--foundry-root", help="Foundry's Data folder. Default: the nearest enclosing folder named Data")
    parser.add_argument("--foundry-folder", help="ID of the Foundry sidebar folder to import the playlist into")
    parser.add_argument("--volume", type=parse_volume, default=0.5, help="Track volume from 0 to 1 (default 0.5)")


def playlist_options_from(args: argparse.Namespace) -> PlaylistOptions:
    return PlaylistOptions(audio_format=args.format, foundry_root=args.foundry_root, volume=args.volume,
                           foundry_folder=args.foundry_folder)


def export_playlist_reporting_errors(exporter: PlaylistExporter, folder: str, options: PlaylistOptions) -> bool:
    """Export the playlist, printing an error instead of a traceback. Returns True on success."""
    try:
        exporter.export(folder, options)
        return True
    except (ValueError, OSError) as error:
        print(f"Error: couldn't write playlist.json: {error}")
        return False


class CliCommand(ABC):
    name: ClassVar[str]
    help: ClassVar[str]

    @abstractmethod
    def configure(self, parser: argparse.ArgumentParser) -> None: ...

    @abstractmethod
    def execute(self, args: argparse.Namespace, services: Services) -> ExitCode: ...


class DownloadCommand(CliCommand):
    name = "download"
    help = "Download audio, then write playlist.json (webm only, by default)"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("folder", help="Folder to download into")
        parser.add_argument("urls", nargs="*", help="YouTube links. Default: read them from --links")
        parser.add_argument("--links", default=get_settings().links_file, help="File of links used when no URLs are given (default: links.txt)")
        parser.add_argument("--format", choices=FORMAT_NAMES, default="webm", help="webm (default, Foundry VTT) or mp3 (Roll20 and most other tools; needs ffmpeg)")
        parser.add_argument("--suffix", default="", help='Text added after each title, e.g. " [EXTENDED]"')
        parser.add_argument("--allow-playlists", action="store_true", help="Download whole YouTube playlists instead of only the linked video")
        parser.add_argument("--archive", action="store_true", help="Skip videos already downloaded into this folder on earlier runs")
        parser.add_argument("--playlist-json", action=argparse.BooleanOptionalAction, default=None, help="Write playlist.json (default: on for webm, off for mp3)")
        add_playlist_arguments(parser)

    def execute(self, args: argparse.Namespace, services: Services) -> ExitCode:
        links = args.urls
        if not links:
            if not os.path.isfile(args.links):
                print(f"Error: no links given and {args.links} not found. Pass URLs as arguments or create the file.")
                return ExitCode.COULD_NOT_RUN
            links = read_links(args.links)

        target = VttTarget.for_format(args.format)
        try:
            files, failed_links = services.download_audio(
                links, args.folder, target.create_audio_format().name,
                suffix=args.suffix, allow_playlists=args.allow_playlists, archive=args.archive)
        except RuntimeError as error:
            print(f"Error: {error}")
            return ExitCode.COULD_NOT_RUN

        exporter = self._choose_playlist_exporter(target, args.playlist_json, services)
        playlist_ok = export_playlist_reporting_errors(exporter, args.folder, playlist_options_from(args))

        print(f"\nSummary: {len(links) - len(failed_links)} of {len(links)} links downloaded ({len(files)} files).")
        for link in failed_links:
            print(f"FAILED: {link}")
        if not playlist_ok:
            return ExitCode.COULD_NOT_RUN
        return ExitCode.SOME_LINKS_FAILED if failed_links else ExitCode.SUCCESS

    @staticmethod
    def _choose_playlist_exporter(target: VttTarget, playlist_json: bool | None, services: Services) -> PlaylistExporter:
        """The target's own exporter, unless --playlist-json / --no-playlist-json says otherwise."""
        if playlist_json is None:
            return target.create_playlist_exporter(services.write_playlist)
        return FoundryPlaylistExporter(services.write_playlist) if playlist_json else NoPlaylistExporter()


class PlaylistCommand(CliCommand):
    name = "playlist"
    help = "Only write playlist.json from the audio files already in a folder"

    def configure(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument("folder", help="Folder holding the audio files")
        parser.add_argument("--format", choices=FORMAT_NAMES, default="webm", help="Which files to include (default webm)")
        add_playlist_arguments(parser)

    def execute(self, args: argparse.Namespace, services: Services) -> ExitCode:
        if not os.path.isdir(args.folder):
            print(f"Error: folder {args.folder} not found.")
            return ExitCode.COULD_NOT_RUN
        exporter = FoundryPlaylistExporter(services.write_playlist)
        if export_playlist_reporting_errors(exporter, args.folder, playlist_options_from(args)):
            return ExitCode.SUCCESS
        return ExitCode.COULD_NOT_RUN


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


COMMANDS: tuple[CliCommand, ...] = (DownloadCommand(), PlaylistCommand(), DoctorCommand())


def build_parser(commands: Sequence[CliCommand] = COMMANDS) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="YouTube audio downloader and Foundry VTT playlist generator")
    subparsers = parser.add_subparsers(dest="command_name", required=True)
    for command in commands:
        command_parser = subparsers.add_parser(command.name, help=command.help)
        command.configure(command_parser)
        command_parser.set_defaults(command=command)
    return parser


def translate_legacy_arguments(argv: list[str]) -> list[str]:
    """Old usage: downloader.py --generate FOLDER [--format X] means `download`."""
    if argv and argv[0] == "--generate":
        return ["download", *argv[1:]]
    return argv


def main(argv: Sequence[str] | None = None) -> int:
    arguments = translate_legacy_arguments(list(sys.argv[1:] if argv is None else argv))
    args = build_parser().parse_args(arguments)
    command: CliCommand = args.command
    return int(command.execute(args, default_services()))
