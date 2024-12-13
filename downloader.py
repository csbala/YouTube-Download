# yt-dlp-youtube-downloader
# A simple Python script using yt-dlp to download YouTube videos or audio in the best quality.

import argparse
import os
import subprocess

def download_video(video_url, output_path="downloads", audio_only=False):
    """Downloads a video or audio from YouTube using yt-dlp."""
    # Create output directory if it doesn't exist
    os.makedirs(output_path, exist_ok=True)

    # Set the format based on the audio_only flag
    format_option = "bestaudio/best" if audio_only else "best"

    # Build the yt-dlp command
    command = [
    "python", "-m", "yt_dlp",
    "-f", format_option,
    "-o", f"{output_path}/%(title)s.%(ext)s",  # Output file format
    video_url
]

    if audio_only:
        command.extend(["--extract-audio", "--audio-format", "mp3"])

    try:
        # Run the yt-dlp command
        subprocess.run(command, check=True)
        print(f"Download completed successfully. Files are saved in {output_path}.")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred during download: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Downloader using yt-dlp")
    parser.add_argument("--url", type=str, required=True, help="The URL of the YouTube video to download")
    parser.add_argument("--output", type=str, default="downloads", help="Output folder for the downloaded file(s)")
    parser.add_argument("--audio", action="store_true", help="Download only the audio as MP3")

    args = parser.parse_args()

    download_video(video_url=args.url, output_path=args.output, audio_only=args.audio)