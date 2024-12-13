# YouTube Downloader using yt-dlp

This repository contains a simple Python script that uses **yt-dlp** to download YouTube videos or audio files in the best quality available. Whether you're new to programming or an experienced developer, this script is easy to use and helps you save YouTube content effortlessly.

---

## Features

- Download YouTube videos in the highest available quality.
- Extract and save audio as MP3 files.
- Specify a custom output folder for your downloads.
- Simple and easy-to-use command-line interface.

---

## Requirements

1. **Python 3.6 or higher** installed on your system.
2. Install **yt-dlp** (a YouTube downloader tool):
   ```bash
   pip install yt-dlp
   ```

## How to Use

### 1. Clone the Repository
Download or clone the repository to your local machine:
```bash
git clone https://github.com/your-username/yt-dlp-youtube-downloader.git
cd yt-dlp-youtube-downloader
```

### 2. Run the Script

Open a terminal or command prompt in the folder where `downloader.py` is located, and use the following commands:

#### **Basic Usage**
To download a YouTube video in the best quality:
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

## Example Commands

- Download a video:
  ```bash
  python downloader.py --url https://www.youtube.com/watch?v=dQw4w9WgXcQ
  ```

- Download a video as MP3:
  ```bash
  python downloader.py --url https://www.youtube.com/watch?v=dQw4w9WgXcQ --audio
  ```

- Download a video and save it in a folder named `my_videos`:
  ```bash
  python downloader.py --url https://www.youtube.com/watch?v=dQw4w9WgXcQ --output my_videos
  ```

---

## Troubleshooting

1. **Command Not Found**: Ensure that `yt-dlp` is installed using:
   ```bash
   pip install yt-dlp
   ```
2. **Python Not Installed**: Download Python from [python.org](https://www.python.org/) and add it to your system's PATH.

---

## Contribution

Feel free to contribute by submitting issues or pull requests to enhance this project!

---

## License

This project is open-source and available under the MIT License.
```

You can copy and paste this file as `README.md` into your repository. It’s structured for easy understanding and use! Let me know if you want to add or tweak anything further.