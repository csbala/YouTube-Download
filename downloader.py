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
        "yt-dlp",
        "-f", format_option,
        "-o", f"{output_path}/%(title)s.%(ext)s",  # Output file format
        video_url
    ]

    if audio_only:
        command.extend(["--extract-audio", "--audio-format", "mp3"])

    try:
        # Run the yt-dlp command
        subprocess.run(command, check=True)
        print(f"Download completed successfully: {video_url}")
    except subprocess.CalledProcessError as e:
        print(f"An error occurred during download: {e}")

def batch_download(file_path, output_path="downloads", audio_only=False):
    """Downloads multiple videos from a text file."""
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    with open(file_path, "r") as file:
        # Read links and normalize them (handle commas, newlines, and whitespace)
        content = file.read()
        links = [link.strip() for link in content.replace("\n", ",").split(",") if link.strip()]

    print(f"Starting batch download for {len(links)} links...")
    for link in links:
        print(f"Downloading: {link}")
        download_video(link, output_path, audio_only)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YouTube Downloader using yt-dlp")
    parser.add_argument("--url", type=str, help="The URL of the YouTube video to download")
    parser.add_argument("--output", type=str, default="downloads", help="Output folder for the downloaded file(s)")
    parser.add_argument("--audio", action="store_true", help="Download only the audio as MP3")
    parser.add_argument("--batch", type=str, help="Path to a text file containing YouTube links for batch download")

    args = parser.parse_args()

    if args.batch:
        batch_download(file_path=args.batch, output_path=args.output, audio_only=args.audio)
    elif args.url:
        download_video(video_url=args.url, output_path=args.output, audio_only=args.audio)
    else:
        print("You must provide either --url or --batch flag.")
