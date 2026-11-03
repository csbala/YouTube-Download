import os
import sys
import json
import glob
import shutil
import hashlib
import argparse
import importlib.metadata
import importlib.util
import urllib.parse
from datetime import datetime

# --- YouTube audio downloader with a Foundry VTT playlist generator ---

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
COOKIES_FILE = os.path.join(SCRIPT_DIR, "cookies.txt")
LINKS_FILE = os.path.join(SCRIPT_DIR, "links.txt")
FOUNDRY_CORE_VERSION = "12.331"
MAX_FILENAME_LENGTH = 150
MIN_YT_DLP_VERSION = "2025.11.12"  # First release with --js-runtimes and --remote-components


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
    # Several versions can be installed side by side, so take the newest
    return os.path.dirname(max(matches, key=os.path.getmtime)) if matches else None


def has_ejs():
    """True if yt-dlp-ejs, the bundled YouTube challenge solver, is installed (pip install "yt-dlp[default]")."""
    return importlib.util.find_spec("yt_dlp_ejs") is not None


def read_links(links_file):
    """Read URLs from a file, one per line or comma-separated. Lines starting with # are skipped."""
    with open(links_file, "r", encoding="utf-8") as file:
        lines = [line for line in file if not line.lstrip().startswith("#")]
    return [link.strip() for link in ",".join(lines).replace("\n", ",").split(",") if link.strip()]


# --- Downloading ---

def max_filename_length(folder_path):
    """Longest title to use for files in folder_path, so the full path stays under Windows' 260-character
    limit, with room for the extension and yt-dlp's .part suffix. Never below 40 characters."""
    return max(40, min(MAX_FILENAME_LENGTH, 240 - len(os.path.abspath(folder_path))))


def build_ydl_options(folder_path, audio_format, suffix="", allow_playlists=False, archive=False):
    """Build yt-dlp options from the same flags the command line would use."""
    import yt_dlp

    args = [
        "-P", folder_path,  # Kept out of -o, because --trim-filenames would trim the folder path too
        "-o", f"%(title)s{suffix.replace('%', '%%')}.%(ext)s",  # % is special in templates
        "--trim-filenames", str(max_filename_length(folder_path)),
    ]
    if not has_ejs():
        # Without the yt-dlp-ejs package, fetch YouTube's challenge solver from GitHub on every run
        args += ["--remote-components", "ejs:github"]
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


def videos(info):
    """Flatten a video or playlist info dict into its videos. A failed playlist entry comes back as None."""
    if not info:
        return []  # A single video the archive skipped
    if info.get("entries") is None:
        return [info]
    # yt-dlp keeps failed entries as None and drops the ones the archive skipped
    return [video for entry in info["entries"] for video in (videos(entry) if entry else [None])]


def video_files(video):
    return [d["filepath"] for d in video.get("requested_downloads", []) if d.get("filepath")]


def downloaded_files(info):
    """Return the final file paths yt-dlp wrote for a video or playlist info dict."""
    return [path for video in videos(info) if video for path in video_files(video)]


def download_audio(links, folder_path, audio_format="webm", **options):
    """Download each link as audio into folder_path. Returns (files, failed), where failed
    holds each failed link, with the reason appended when it's only partly failed."""
    import yt_dlp

    os.makedirs(folder_path, exist_ok=True)
    ydl_opts = build_ydl_options(folder_path, audio_format, **options)

    files, failed = [], []
    owners = {}  # file path -> ID of the video that wrote it, to catch two videos with the same title
    print(f"Starting batch download for {len(links)} links to {folder_path} as .{audio_format}...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for link in links:
            print(f"Downloading: {link}")
            try:
                results = videos(ydl.extract_info(link, download=True))
            except yt_dlp.utils.DownloadError:
                failed.append(link)  # yt-dlp has already printed the ERROR line
                continue
            except OSError as e:
                print(f"ERROR: {e}")
                failed.append(link)
                continue

            new_files, problems = [], []
            broken = results.count(None)
            if broken:
                problems.append(f"{broken} of {len(results)} playlist items failed")
            for video in filter(None, results):
                for path in video_files(video):
                    if path not in owners:
                        owners[path] = video.get("id")
                        new_files.append(path)
                    elif owners[path] != video.get("id"):
                        print(f"ERROR: {video.get('title')} has the same file name as an earlier video, so it was skipped. "
                              f"Download it again on its own with --suffix.")
                        problems.append(f"same title as an earlier video: {os.path.basename(path)}")
            files += new_files

            if problems:
                failed.append(f"{link} ({'; '.join(problems)})")
            elif not new_files and options.get("allow_playlists") and not options.get("archive"):
                # A playlist with nothing downloaded failed, unless the archive skipped it all
                failed.append(link)
            else:
                print(f"Done: {link}")
    return files, failed


# --- Foundry VTT playlist ---

def stable_id(text):
    """16-character ID derived from text, so re-imports keep the same track IDs."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def is_foundry_data(path):
    """True for a folder named Data that sits next to Foundry's Config folder or inside a folder named like Foundry.
    That keeps an unrelated folder such as C:\\data from being taken for Foundry's."""
    if os.path.basename(path).lower() != "data":
        return False
    parent = os.path.dirname(path)
    return os.path.isdir(os.path.join(parent, "Config")) or "foundry" in os.path.basename(parent).lower()


def foundry_relative_folder(folder_path, foundry_root=None):
    """Path of folder_path relative to Foundry's Data folder, with forward slashes."""
    folder_path = os.path.abspath(folder_path)
    if foundry_root is None:
        # Look for the folder itself or an enclosing Foundry "Data" folder, e.g. ...\FoundryVTT\Data\Music_Import\apple
        candidate = folder_path
        while True:
            if is_foundry_data(candidate):
                foundry_root = candidate
                break
            if os.path.dirname(candidate) == candidate:
                break
            candidate = os.path.dirname(candidate)
    if foundry_root is None:
        fallback = "Music_Import/" + os.path.basename(folder_path)
        print(f"Warning: {folder_path} isn't inside a Foundry Data folder, so track paths assume {fallback}/. Use --foundry-root to set it.")
        return fallback
    try:
        relative = os.path.relpath(folder_path, os.path.abspath(foundry_root))
    except ValueError:  # Different Windows drives
        relative = ".."
    if relative == ".." or relative.startswith(".." + os.sep):
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


# --- Setup check ---

def version_tuple(version):
    return tuple(int(part) for part in version.split(".") if part.isdigit())


def doctor():
    """Check everything a download needs. Prints one [OK], [WARN] or [MISSING] line per check, each with
    its fix, and returns how many block a download. Never prints cookies.txt: it's the user's login."""
    upgrade = f'"{sys.executable}" -m pip install -U "yt-dlp[default]"'
    missing = 0

    try:
        version = importlib.metadata.version("yt-dlp")
    except importlib.metadata.PackageNotFoundError:
        version = None
    if version is None:
        print(f"[MISSING] yt-dlp is not installed for this Python. Fix: {upgrade}")
        missing += 1
    elif version_tuple(version) < version_tuple(MIN_YT_DLP_VERSION):
        print(f"[MISSING] yt-dlp {version} is too old (this script needs {MIN_YT_DLP_VERSION} or newer). Fix: {upgrade}")
        missing += 1
    else:
        print(f"[OK] yt-dlp {version}")

    if has_ejs():
        print("[OK] yt-dlp-ejs (YouTube challenge solver)")
    else:
        print(f"[WARN] yt-dlp-ejs is not installed, so the YouTube challenge solver is fetched from GitHub on every run. Fix: {upgrade}")

    node = find_node()
    if node:
        print(f"[OK] Node.js at {node}")
    else:
        print("[MISSING] Node.js not found (yt-dlp uses it to solve YouTube's JS challenge). Fix: winget install -e --id OpenJS.NodeJS.LTS")
        missing += 1

    ffmpeg = find_ffmpeg()
    if ffmpeg:
        print(f"[OK] ffmpeg in {ffmpeg}")
    else:
        print("[MISSING] ffmpeg not found (needed for mp3; webm still works without it). Fix: winget install -e --id Gyan.FFmpeg")
        missing += 1

    if not os.path.isfile(COOKIES_FILE):
        print(f"[WARN] cookies.txt not found at {COOKIES_FILE}. Public videos usually work; age-restricted ones and "
              "'confirm you're not a bot' blocks will fail. Fix: export YouTube cookies with the 'Get cookies.txt LOCALLY' "
              "browser extension and save them as cookies.txt next to downloader.py.")
    else:
        with open(COOKIES_FILE, "r", encoding="utf-8", errors="replace") as f:
            header = f.readline()
        age_days = int((datetime.now().timestamp() - os.path.getmtime(COOKIES_FILE)) / 86400)
        if "HTTP Cookie File" not in header:
            print("[WARN] cookies.txt isn't in Netscape format (its first line should mention 'HTTP Cookie File'). Re-export it with 'Get cookies.txt LOCALLY'.")
        elif age_days > 30:
            print(f"[WARN] cookies.txt is {age_days} days old and may have expired. Re-export it if downloads fail with a sign-in or bot error.")
        else:
            print(f"[OK] cookies.txt ({age_days} days old)")
    return missing


# --- Main Execution ---

def volume(text):
    """argparse type for --volume: a number from 0 to 1."""
    try:
        value = float(text)
    except ValueError:
        value = None
    if value is None or not 0 <= value <= 1:
        raise argparse.ArgumentTypeError(f"must be a number from 0 to 1, not {text}")
    return value


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
        p.add_argument("--volume", type=volume, default=0.5, help="Track volume from 0 to 1 (default 0.5)")

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

    commands.add_parser("doctor", help="Check that yt-dlp, Node.js, ffmpeg and cookies.txt are ready")

    args = parser.parse_args(argv)
    if args.command == "doctor":
        return 1 if doctor() else 0
    playlist_options = dict(audio_format=args.format, foundry_root=args.foundry_root, volume=args.volume, foundry_folder=args.foundry_folder)

    def try_write_playlist():
        """Write playlist.json, printing an error instead of a traceback. Returns True on success."""
        try:
            write_playlist(args.folder, **playlist_options)
            return True
        except (ValueError, OSError) as e:
            print(f"Error: couldn't write playlist.json: {e}")
            return False

    if args.command == "playlist":
        if not os.path.isdir(args.folder):
            print(f"Error: folder {args.folder} not found.")
            return 2
        return 0 if try_write_playlist() else 2

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

    playlist_ok = True
    if args.playlist_json if args.playlist_json is not None else args.format == "webm":
        playlist_ok = try_write_playlist()

    print(f"\nSummary: {len(links) - len(failed)} of {len(links)} links downloaded ({len(files)} files).")
    for link in failed:
        print(f"FAILED: {link}")
    if not playlist_ok:
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
