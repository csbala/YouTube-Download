# YouTube Downloader & Foundry VTT Playlist Generator (Simplified)

A streamlined Python script to download audio from YouTube as `.webm` files and generate a playlist JSON for Foundry Virtual Tabletop (Foundry VTT), designed for a seamless workflow with minimal commands.

## Features

- **YouTube Downloader**:

  - Downloads audio as `.webm` files from YouTube URLs listed in `links.txt`.
  - Requires a cookies file for authenticated downloads (e.g., age-restricted videos).
  - Runs with a single command: `python downloader.py`.

- **Foundry VTT Playlist Generator**:
  - Generates a JSON file for Foundry VTT playlists from a folder of `.webm` files.
  - Sets the playlist name to the folder name (e.g., "Honkai Impact 3rd OST").
  - Uses the full file name as the track name (e.g., "Honkai Impact 3rd OST： Ace [EXTENDED]..webm").
  - Constructs relative paths compatible with Foundry VTT (e.g., `Music_Import/Honkai Impact 3rd OST/...`).
  - Runs with a simple command: `python downloader.py --generate "path/to/folder"`.

## Prerequisites

- **Python 3.6 or later**: Download and install from [python.org](https://www.python.org/downloads/).
- **yt-dlp**: Install via pip:
  ```
  pip install yt-dlp
  ```
- **Foundry VTT**: Ensure you have Foundry VTT installed and a world set up to import playlists.
- **Google Chrome Cookies**: Export your YouTube cookies using a browser extension like "Get cookies.txt LOCALLY" (available for Chrome/Firefox). Save the file as `www.youtube.com_cookies.txt` in the same directory as the script.

## Installation

1. **Clone or Download the Project**:

   - Download the project files and place them in a folder (e.g., `yt-dlp-youtube-downloader`).

2. **Prepare the Cookies File**:

   - Export your YouTube cookies to `www.youtube.com_cookies.txt` using a browser extension.
   - Place the file in the same directory as `downloader.py`.

3. **Create a links.txt File**:
   - Create a `links.txt` file in the same directory as the script.
   - Add YouTube URLs (one per line or comma-separated):
     ```
     https://www.youtube.com/watch?v=VIDEO_ID1
     https://www.youtube.com/watch?v=VIDEO_ID2
     ```

## Files Overview

- `downloader.py`: The main script for downloading `.webm` files and generating Foundry VTT playlists.
- `www.youtube.com_cookies.txt`: Cookies file for YouTube downloads (must be provided by the user).
- `links.txt`: Text file containing YouTube URLs for downloading.

## Usage

### Step 1: Download .webm Files from YouTube

- Ensure `links.txt` and `www.youtube.com_cookies.txt` are in the same directory as `downloader.py`.
- Run the command:
  ```
  python downloader.py
  ```
- This downloads all audio from the URLs in `links.txt` as `.webm` files to a `downloads` folder.

### Step 2: Move Files to Foundry VTT Data Folder

- Move the downloaded `.webm` files to a folder in Foundry VTT’s data directory.
- Example: `C:\Users\Hp Victus\AppData\Local\FoundryVTT\Data\Music_Import\Honkai Impact 3rd OST`.

### Step 3: Generate a Foundry VTT Playlist JSON

- Run the command with the `--generate` flag, specifying the folder path:
  ```
  python downloader.py --generate "path/to/folder"
  ```
- Example:
  ```
  python downloader.py --generate "C:\Users\Hp Victus\AppData\Local\FoundryVTT\Data\Music_Import\Honkai Impact 3rd OST"
  ```
- This generates `playlist.json` in the specified folder.

### Step 4: Import the JSON into Foundry VTT

- Open Foundry VTT and go to the **Audio Playlists** tab.
- Right-click an existing playlist (or create a new one with **Create Playlist**).
- Select **Import Data** (or open the playlist configuration and click **Bulk Import**).
- In the File Picker, navigate to your folder (e.g., `Music_Import/Honkai Impact 3rd OST`).
- Select `playlist.json` and click **Import**.
- The playlist will load with all tracks, ready for playback.

## Notes

- **Cookies Requirement**: The downloader requires `www.youtube.com_cookies.txt` for authenticated downloads. Without it, some videos (e.g., age-restricted) will fail to download.
- **Foundry VTT Compatibility**: The playlist generator is designed for Foundry VTT version 12.331 (as of May 2025). It generates valid 16-character `_id` values for each track.
- **Performance in Foundry**: Importing a large playlist (e.g., 100 tracks) may cause lag. Consider splitting into smaller playlists within Foundry VTT after importing.
- **File Naming**: The script uses the full file name for track names. Ensure your files are named appropriately for your campaign.

## Troubleshooting

- **YouTube Download Fails**:
  - Ensure `yt-dlp` is installed and up to date (`pip install -U yt-dlp`).
  - Verify your `www.youtube.com_cookies.txt` file is valid and not expired.
  - Check if `links.txt` exists and contains valid YouTube URLs.
- **Foundry VTT Import Fails**:
  - Ensure the `.webm` files are in the correct folder within Foundry’s data directory.
  - Verify the `path` in the JSON matches the relative path in Foundry (e.g., `Music_Import/Honkai%20Impact%203rd%20OST/...`).
  - Check the Foundry VTT console for validation errors.
- **Python Errors**:
  - Ensure Python is installed and added to your PATH.
  - Run the script from a command prompt/terminal in the correct directory.

## License

This project is provided as-is, with no warranty. Use at your own risk. Ensure you comply with YouTube’s terms of service when downloading content.

## Acknowledgments

- Built with `yt-dlp` for YouTube downloading.
- Designed for Foundry Virtual Tabletop (Foundry VTT) playlist importing.
