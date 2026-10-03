import os
import sys
import json
import urllib.parse
import random
import string
import subprocess
import argparse
import shutil
import glob
from datetime import datetime

# --- Foundry VTT Playlist Generator with Integrated Downloader ---

def generate_random_id():
    """Generate a random 16-character alphanumeric ID."""
    characters = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return ''.join(random.choice(characters) for _ in range(16))

def find_ffmpeg():
    """Return the folder containing ffmpeg.exe, or None. Needed for mp3 conversion."""
    found = shutil.which("ffmpeg")
    if found:
        return os.path.dirname(found)
    # winget installs aren't on PATH until a new shell, so look where winget puts it
    local = os.environ.get("LOCALAPPDATA", "")
    matches = glob.glob(os.path.join(local, "Microsoft", "WinGet", "Packages", "Gyan.FFmpeg*", "*", "bin", "ffmpeg.exe"))
    return os.path.dirname(matches[0]) if matches else None

def generate_foundry_playlist(folder_path, output_filename="playlist.json", audio_format="webm"):
    """Download audio files (.webm, or .mp3 for Roll20) to the specified folder and generate a playlist JSON for Foundry VTT."""
    # Create the folder if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)
    
    # Path to the cookies file (relative to the script's directory)
    cookies_file = os.path.join(os.path.dirname(__file__), "cookies.txt")

    # Check if cookies file exists (optional)
    use_cookies = os.path.isfile(cookies_file)
    if not use_cookies:
        print(f"Warning: Cookies file not found at {cookies_file}. Proceeding without cookies (may fail for age-restricted videos).")

    # Check if links.txt exists
    links_file = os.path.join(os.path.dirname(__file__), "links.txt")
    if not os.path.isfile(links_file):
        print(f"Error: links.txt not found in the current directory. Please create it with YouTube URLs.")
        return

    # Read links from links.txt
    with open(links_file, "r") as file:
        content = file.read()
        links = [link.strip() for link in content.replace("\n", ",").split(",") if link.strip()]

    # mp3 needs ffmpeg to convert the downloaded audio
    ffmpeg_dir = None
    if audio_format == "mp3":
        ffmpeg_dir = find_ffmpeg()
        if not ffmpeg_dir:
            print("Error: ffmpeg is required for mp3 but was not found. Install it with: winget install -e --id Gyan.FFmpeg")
            return

    # Download audio files directly to the specified folder
    print(f"Starting batch download for {len(links)} links to {folder_path} as .{audio_format}...")
    for link in links:
        print(f"Downloading: {link}")
        command = [
            sys.executable, "-m", "yt_dlp",
            "--js-runtimes", r"node:C:\Program Files\nodejs\node.exe",  # Use Node.js as JS runtime
            "--remote-components", "ejs:github",  # Use latest challenge solver from GitHub
            "--no-playlist",  # Never download a whole playlist when given a single video URL
            "-o", f"{folder_path}/%(title)s [EXTENDED].%(ext)s",  # Output with full title
        ]
        if audio_format == "mp3":
            # Roll20's jukebox only accepts mp3
            command += [
                "-f", "bestaudio",
                "-x", "--audio-format", "mp3", "--audio-quality", "192K",
                "--ffmpeg-location", ffmpeg_dir,
            ]
        else:
            command += ["-f", "bestaudio[ext=webm]/bestaudio"]  # Best webm audio, fallback to best audio
        command.append(link)
        if use_cookies:
            command += ["--cookies", cookies_file]

        try:
            subprocess.run(command, check=True)
            print(f"Download completed successfully: {link}")
        except subprocess.CalledProcessError as e:
            print(f"Error during download: {e}")

    # List all audio files of the chosen format in the folder
    audio_files = [f for f in os.listdir(folder_path) if f.endswith(f'.{audio_format}')]
    if not audio_files:
        print(f"No .{audio_format} files found in {folder_path}. Playlist will be empty.")

    # Generate a list of sound entries
    sounds = []
    for i, filename in enumerate(audio_files):
        sound_name = filename
        # Foundry paths always use forward slashes, even on Windows
        relative_path = "/".join(["Music_Import", os.path.basename(os.path.normpath(folder_path)), filename])
        encoded_path = urllib.parse.quote(relative_path, safe='/')
        
        sound = {
            "name": sound_name,
            "path": encoded_path,
            "channel": "music",
            "repeat": False,
            "fade": None,
            "description": "",
            "volume": 0.01,
            "_id": generate_random_id(),
            "playing": False,
            "pausedTime": None,
            "sort": i,
            "flags": {}
        }
        sounds.append(sound)
    
    # Get current timestamp in milliseconds for _stats
    current_time = int(datetime.now().timestamp() * 1000)
    
    # Create the playlist JSON structure
    playlist = {
        "folder": "xRZH0HFR0JSeNcZ3",
        "name": os.path.basename(folder_path),
        "sounds": sounds,
        "channel": "music",
        "mode": 0,
        "playing": False,
        "fade": 2000,
        "sorting": "a",
        "seed": 228,
        "flags": {
            "exportSource": {
                "world": "one-piece-dandd-marines",
                "system": "dnd5e",
                "coreVersion": "12.331",
                "systemVersion": "4.3.9"
            }
        },
        "_stats": {
            "coreVersion": "12.331",
            "systemId": "dnd5e",
            "systemVersion": "3.3.1",
            "createdTime": current_time,
            "modifiedTime": current_time,
            "lastModifiedBy": "3AazUso5cQzr2z0e"
        },
        "description": ""
    }
    
    # Write the JSON to a file in the same folder
    output_path = os.path.join(folder_path, output_filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(playlist, f, indent=2)
    
    print(f"JSON file generated successfully at: {output_path}")

# --- Main Execution ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Downloader and Foundry VTT Playlist Generator")
    parser.add_argument("--generate", type=str, required=True, help="Path to the folder where audio files will be downloaded and a Foundry VTT playlist JSON will be generated")
    parser.add_argument("--format", choices=["webm", "mp3"], default="webm", help="Audio format: webm (default, Foundry VTT) or mp3 (Roll20 and most other tools; needs ffmpeg)")

    args = parser.parse_args()

    # Generate Foundry VTT playlist JSON for the specified folder, including downloading
    generate_foundry_playlist(args.generate, audio_format=args.format)