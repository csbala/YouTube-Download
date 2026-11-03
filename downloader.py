import os
import sys
import json
import glob
import shutil
import hashlib
import argparse
import urllib.parse
from datetime import datetime

# --- YouTube audio downloader with a Foundry VTT playlist generator ---

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(SCRIPT_DIR, "cookies.txt")
LINKS_FILE = os.path.join(SCRIPT_DIR, "links.txt")
FOUNDRY_CORE_VERSION = "12.331"


def find_node():
    """Return the path of node.exe, or None. yt-dlp uses it to solve YouTube's JS challenge."""
    found = shutil.which("node")
    if found:
        return found
    default = r"C:\Program Files\nodejs\node.exe"
    return default if os.path.isfile(default) else None


def find_ffmpeg():
    """Return the folder containing ffmpeg.exe, or None. Needed for mp3 conversion."""
    found = shutil.which("ffmpeg")
    if found:
        return os.path.dirname(found)
    # winget installs aren't on PATH until a new shell, so look where winget puts it
    local = os.environ.get("LOCALAPPDATA", "")
    matches = glob.glob(os.path.join(local, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "*", "bin", "ffmpeg.exe"))
    return os.path.dirname(matches[0]) if matches else None


def read_links(links_file):
    """Read URLs from a file, one per line or comma-separated. Lines starting with # are skipped."""
    with open(links_file, "r", encoding="utf-8") as file:
        lines = [line for line in file if not line.lstrip().startswith("#")]
    return [link.strip() for link in ",".join(lines).replace("\n", ",").split(",") if link.strip()]


# --- Downloading ---

def build_ydl_options(folder_path, audio_format, suffix="", allow_playlists=False, archive=False):
    """Build yt-dlp options from the same flags the command line would use."""
    import yt_dlp

    args = [
        "-o", os.path.join(folder_path, f"%(title)s{suffix}.%(ext)s"),
        "--remote-components", "ejs:github",  # Use latest challenge solver from GitHub
    ]
    if not allow_playlists:
        args.append("--no-playlist")  # Only the video a link points at, even if it's in a playlist

    node = find_node()
    if node:
        args += ["--js-runtimes", f"node:{node}"]
    else:
        print("Warning: Node.js not found. YouTube downloads may fail. Install it with: winget install -e --id OpenJS.NodeJS.LTS")

    if audio_format == "mp3":
        ffmpeg_dir = find_ffmpeg()
        if not ffmpeg_dir:
            raise RuntimeError("ffmpeg is required for mp3 but was not found. Install it with: winget install -e --id Gyan.FFmpeg")
        # Roll20's jukebox only accepts mp3
        args += ["-f", "bestaudio", "-x", "--audio-format", "mp3", "--audio-quality", "192K", "--ffmpeg-location", ffmpeg_dir]
    else:
        args += ["-f", "bestaudio[ext=webm]/bestaudio"]  # Best webm audio, fallback to best audio

    if os.path.isfile(COOKIES_FILE):
        args += ["--cookies", COOKIES_FILE]
    else:
        print(f"Warning: Cookies file not found at {COOKIES_FILE}. Proceeding without cookies (may fail for age-restricted videos).")

    if archive:
        # Remembers finished videos so later runs skip them, even if the file was renamed
        args += ["--download-archive", os.path.join(folder_path, ".download-archive.txt")]

    ydl_opts = yt_dlp.parse_options(args).ydl_opts
    # Raise on a failed single video so it's counted. In playlists, keep going past broken entries.
    ydl_opts["ignoreerrors"] = "only_download" if allow_playlists else False
    return ydl_opts


def downloaded_files(info):
    """Return the final file paths yt-dlp wrote for a video or playlist info dict."""
    if not info:
        return []
    if info.get("entries") is not None:
        return [path for entry in info["entries"] for path in downloaded_files(entry)]
    return [d["filepath"] for d in info.get("requested_downloads", []) if d.get("filepath")]


def download_audio(links, folder_path, audio_format="webm", **options):
    """Download each link as audio into folder_path. Returns (files, failed_links)."""
    import yt_dlp

    os.makedirs(folder_path, exist_ok=True)
    ydl_opts = build_ydl_options(folder_path, audio_format, **options)

    files, failed = [], []
    print(f"Starting batch download for {len(links)} links to {folder_path} as .{audio_format}...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for link in links:
            print(f"Downloading: {link}")
            try:
                new_files = downloaded_files(ydl.extract_info(link, download=True))
            except yt_dlp.utils.DownloadError:
                failed.append(link)  # yt-dlp has already printed the ERROR line
                continue
            # A playlist with nothing downloaded failed, unless the archive skipped it all
            if not new_files and options.get("allow_playlists") and not options.get("archive"):
                failed.append(link)
                continue
            files += new_files
            print(f"Done: {link}")
    return files, failed


# --- Foundry VTT playlist ---

def stable_id(text):
    """16-character ID derived from text, so re-imports keep the same track IDs."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def foundry_relative_folder(folder_path, foundry_root=None):
    """Path of folder_path relative to Foundry's Data folder, with forward slashes."""
    folder_path = os.path.abspath(folder_path)
    if foundry_root is None:
        # Look for the folder itself or an enclosing folder named "Data", e.g. ...\FoundryVTT\Data\Music_Import\apple
        candidate = folder_path
        while True:
            if os.path.basename(candidate).lower() == "data":
                foundry_root = candidate
                break
            if os.path.dirname(candidate) == candidate:
                break
            candidate = os.path.dirname(candidate)
    if foundry_root is None:
        fallback = "Music_Import/" + os.path.basename(folder_path)
        print(f"Warning: {folder_path} isn't inside a Foundry Data folder, so track paths assume {fallback}/. Use --foundry-root to set it.")
        return fallback
    relative = os.path.relpath(folder_path, os.path.abspath(foundry_root))
    if relative.startswith(".."):
        raise ValueError(f"{folder_path} is not inside the Foundry root {foundry_root}")
    return "" if relative == "." else relative.replace(os.sep, "/")


def build_playlist(folder_path, audio_format="webm", foundry_root=None, volume=0.5, foundry_folder=None):
    """Build a Foundry VTT playlist dict from every .<audio_format> file in folder_path."""
    audio_files = sorted(f for f in os.listdir(folder_path) if f.lower().endswith(f".{audio_format}"))
    if not audio_files:
        print(f"No .{audio_format} files found in {folder_path}. Playlist will be empty.")

    relative_folder = foundry_relative_folder(folder_path, foundry_root)
    sounds = []
    for i, filename in enumerate(audio_files):
        # Foundry paths always use forward slashes, even on Windows
        relative_path = f"{relative_folder}/{filename}" if relative_folder else filename
        sounds.append({
            "name": os.path.splitext(filename)[0],
            "path": urllib.parse.quote(relative_path, safe="/"),
            "channel": "music",
            "repeat": False,
            "fade": None,
            "description": "",
            "volume": volume,
            "_id": stable_id(relative_path),
            "playing": False,
            "pausedTime": None,
            "sort": i,
            "flags": {},
        })

    current_time = int(datetime.now().timestamp() * 1000)
    return {
        "folder": foundry_folder,
        "name": os.path.basename(os.path.normpath(folder_path)),
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


def write_playlist(folder_path, output_filename="playlist.json", **options):
    playlist = build_playlist(folder_path, **options)
    output_path = os.path.join(folder_path, output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(playlist, f, indent=2)
    print(f"Playlist with {len(playlist['sounds'])} tracks written to: {output_path}")


# --- Main Execution ---

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # Old usage: downloader.py --generate FOLDER [--format X]
    if argv and argv[0] == "--generate":
        argv[0] = "download"

    parser = argparse.ArgumentParser(description="YouTube audio downloader and Foundry VTT playlist generator")
    commands = parser.add_subparsers(dest="command", required=True)

    def add_playlist_options(p):
        p.add_argument("--foundry-root", help="Foundry's Data folder. Default: the nearest enclosing folder named Data")
        p.add_argument("--foundry-folder", help="ID of the Foundry sidebar folder to import the playlist into")
        p.add_argument("--volume", type=float, default=0.5, help="Track volume from 0 to 1 (default 0.5)")

    download = commands.add_parser("download", help="Download audio, then write playlist.json (webm only, by default)")
    download.add_argument("folder", help="Folder to download into")
    download.add_argument("urls", nargs="*", help="YouTube links. Default: read them from --links")
    download.add_argument("--links", default=LINKS_FILE, help="File of links used when no URLs are given (default: links.txt)")
    download.add_argument("--format", choices=["webm", "mp3"], default="webm", help="webm (default, Foundry VTT) or mp3 (Roll20 and most other tools; needs ffmpeg)")
    download.add_argument("--suffix", default="", help='Text added after each title, e.g. " [EXTENDED]"')
    download.add_argument("--allow-playlists", action="store_true", help="Download whole YouTube playlists instead of only the linked video")
    download.add_argument("--archive", action="store_true", help="Skip videos already downloaded into this folder on earlier runs")
    download.add_argument("--playlist-json", action=argparse.BooleanOptionalAction, default=None, help="Write playlist.json (default: on for webm, off for mp3)")
    add_playlist_options(download)

    playlist = commands.add_parser("playlist", help="Only write playlist.json from the audio files already in a folder")
    playlist.add_argument("folder", help="Folder holding the audio files")
    playlist.add_argument("--format", choices=["webm", "mp3"], default="webm", help="Which files to include (default webm)")
    add_playlist_options(playlist)

    args = parser.parse_args(argv)
    playlist_options = dict(audio_format=args.format, foundry_root=args.foundry_root, volume=args.volume, foundry_folder=args.foundry_folder)

    if args.command == "playlist":
        write_playlist(args.folder, **playlist_options)
        return 0

    links = args.urls
    if not links:
        if not os.path.isfile(args.links):
            print(f"Error: no links given and {args.links} not found. Pass URLs as arguments or create the file.")
            return 2
        links = read_links(args.links)
    try:
        files, failed = download_audio(links, args.folder, args.format, suffix=args.suffix,
                                       allow_playlists=args.allow_playlists, archive=args.archive)
    except RuntimeError as e:
        print(f"Error: {e}")
        return 2

    if args.playlist_json if args.playlist_json is not None else args.format == "webm":
        write_playlist(args.folder, **playlist_options)

    print(f"\nSummary: {len(links) - len(failed)} of {len(links)} links downloaded ({len(files)} files).")
    for link in failed:
        print(f"FAILED: {link}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
