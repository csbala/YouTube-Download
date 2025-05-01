import os
import json
import urllib.parse
import random
import string
import subprocess
import argparse
from datetime import datetime

# --- Foundry VTT Playlist Generator with Integrated Downloader ---

def generate_random_id():
    """Generate a random 16-character alphanumeric ID."""
    characters = string.ascii_letters + string.digits  # a-z, A-Z, 0-9
    return ''.join(random.choice(characters) for _ in range(16))

def generate_foundry_playlist(folder_path, output_filename="playlist.json"):
    """Download .webm files to the specified folder and generate a playlist JSON for Foundry VTT."""
    # Create the folder if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)
    
    # Path to the cookies file (relative to the script's directory)
    cookies_file = os.path.join(os.path.dirname(__file__), "www.youtube.com_cookies.txt")

    # Check if cookies file exists
    if not os.path.isfile(cookies_file):
        print(f"Error: Cookies file not found at {cookies_file}. Please provide www.youtube.com_cookies.txt.")
        return

    # Check if links.txt exists
    links_file = "links.txt"
    if not os.path.isfile(links_file):
        print(f"Error: links.txt not found in the current directory. Please create it with YouTube URLs.")
        return

    # Read links from links.txt
    with open(links_file, "r") as file:
        content = file.read()
        links = [link.strip() for link in content.replace("\n", ",").split(",") if link.strip()]

    # Download .webm files directly to the specified folder
    print(f"Starting batch download for {len(links)} links to {folder_path}...")
    for link in links:
        print(f"Downloading: {link}")
        # Build the yt-dlp command for .webm audio
        command = [
            "yt-dlp",
            "-f", "bestaudio[ext=webm]",  # Download best audio in .webm format
            "-o", f"{folder_path}/%(title)s [EXTENDED]..%(ext)s",  # Output with full title
            link,
            "--cookies", cookies_file  # Use cookies for authentication
        ]

        try:
            subprocess.run(command, check=True)
            print(f"Download completed successfully: {link}")
        except subprocess.CalledProcessError as e:
            print(f"Error during download: {e}")

    # List all .webm files in the folder
    webm_files = [f for f in os.listdir(folder_path) if f.endswith('.webm')]
    if not webm_files:
        print(f"No .webm files found in {folder_path}. Playlist will be empty.")
    
    # Generate a list of sound entries
    sounds = []
    for i, filename in enumerate(webm_files):
        sound_name = filename
        relative_path = os.path.join("Music_Import", os.path.basename(folder_path), filename)
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
    parser.add_argument("--generate", type=str, required=True, help="Path to the folder where .webm files will be downloaded and a Foundry VTT playlist JSON will be generated")

    args = parser.parse_args()

    # Generate Foundry VTT playlist JSON for the specified folder, including downloading
    generate_foundry_playlist(args.generate)