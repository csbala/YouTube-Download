# YouTube Downloader using yt-dlp

This repository contains a simple Python script that uses **yt-dlp** to download YouTube videos or audio files in the best quality available. Whether you're new to programming or an experienced developer, this script is easy to use and helps you save YouTube content effortlessly.

---

## Features

- Download YouTube videos in the highest available quality.
- Extract and save audio as MP3 files.
- Specify a custom output folder for your downloads.
- Batch download multiple YouTube videos or audios from a text file.
- Supports flexible formatting of links (comma-separated or newline-separated).

## Requirements

1. **Python 3.6 or higher** installed on your system.
2. Install **yt-dlp** (a YouTube downloader tool):
   ```bash
   pip install yt-dlp
   ```
3. Install **ffmpeg** for audio extraction (required for MP3 downloads):
   - On Windows: [Download and install ffmpeg](https://ffmpeg.org/download.html), and add it to your PATH.
   - On Linux: Install with:
     ```bash
     sudo apt install ffmpeg
     ```
   - On macOS: Install with:
     ```bash
     brew install ffmpeg
     ```

---

## How to Use

### 1. Clone the Repository

Download or clone the repository to your local machine:

```bash
git clone https://github.com/your-username/yt-dlp-youtube-downloader.git
cd yt-dlp-youtube-downloader
```

### 2. Run the Script

#### **Basic Usage**

To download a single YouTube video in the best quality:

```bash
python downloader.py --url <YouTube-Video-URL>
```

#### **Download as MP3**

To extract only the audio and save it as an MP3 file:

```bash
python downloader.py --url <YouTube-Video-URL> --audio
```

#### **Specify Output Folder**

To save the downloaded file(s) in a custom folder:

```bash
python downloader.py --url <YouTube-Video-URL> --output <folder-name>
```

---

## Batch Download

You can download multiple videos or audios at once by providing a text file with YouTube links.

### Preparing the Text File

1. Create a `.txt` file (e.g., `links.txt`) with YouTube links in any of the following formats:

   - Comma-separated:
     ```
     https://www.youtube.com/watch?v=dQw4w9WgXcQ, https://www.youtube.com/watch?v=3JZ_D3ELwOQ, https://www.youtube.com/watch?v=C0DPdy98e4c
     ```
   - Newline-separated:
     ```
     https://www.youtube.com/watch?v=dQw4w9WgXcQ
     https://www.youtube.com/watch?v=3JZ_D3ELwOQ
     https://www.youtube.com/watch?v=C0DPdy98e4c
     ```
   - Mixed formats (comma + newline):
     ```
     https://www.youtube.com/watch?v=dQw4w9WgXcQ,
     https://www.youtube.com/watch?v=3JZ_D3ELwOQ,
     https://www.youtube.com/watch?v=C0DPdy98e4c
     ```

2. Save the file in your desired location.

### Running the Batch Download

Use the `--batch` flag with the path to the text file:

```bash
python downloader.py --batch path/to/links.txt
```

#### Optional: Download as MP3

Add the `--audio` flag for audio-only downloads:

```bash
python downloader.py --batch path/to/links.txt --audio
```

---

## Example Commands

- Download a single video:

  ```bash
  python downloader.py --url https://www.youtube.com/watch?v=dQw4w9WgXcQ
  ```

- Download a single video as MP3:

  ```bash
  python downloader.py --url https://www.youtube.com/watch?v=dQw4w9WgXcQ --audio
  ```

- Batch download videos from `links.txt`:

  ```bash
  python downloader.py --batch links.txt
  ```

- Batch download audios from `links.txt`:
  ```bash
  python downloader.py --batch links.txt --audio
  ```

---

## Troubleshooting

1. **Command Not Found**: Ensure `yt-dlp` is installed using:
   ```bash
   pip install yt-dlp
   ```
2. **FFmpeg Not Found**: Ensure `ffmpeg` is installed and added to your system's PATH. Check by running:
   ```bash
   ffmpeg -version
   ```
3. **Python Not Installed**: Download Python from [python.org](https://www.python.org/) and add it to your system's PATH.

---

## Contribution

Feel free to contribute by submitting issues or pull requests to enhance this project!

---

## License

This project is open-source and available under the MIT License.
