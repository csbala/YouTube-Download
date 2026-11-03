# YouTube Audio Downloader & Foundry VTT Playlist Generator

Downloads audio from YouTube links and, for Foundry Virtual Tabletop, writes a `playlist.json` you can import straight into the Audio Playlists tab.

- **webm** (default): for Foundry VTT. Also writes `playlist.json`.
- **mp3**: for Roll20's jukebox (which only accepts mp3) and most other tools. Needs ffmpeg.

## Requirements

- **Python 3.9 or later**
- **yt-dlp** 2025.11.12 or newer: `pip install -r requirements.txt`
- **Node.js**: yt-dlp uses it to solve YouTube's JavaScript challenge. `winget install -e --id OpenJS.NodeJS.LTS`
- **ffmpeg** (mp3 only): `winget install -e --id Gyan.FFmpeg`. The script finds a winget install even before you open a new terminal.
- **cookies.txt** (optional): needed for age-restricted videos and "confirm you're not a bot" blocks. Export your YouTube cookies with a browser extension such as "Get cookies.txt LOCALLY" and save the file as `cookies.txt` next to `downloader.py`. Git ignores it. **Never commit it**: it's your Google login.

## Usage

### Download

```
python downloader.py download "<folder>" [links...] [options]
```

Pass links as arguments, or leave them out to read `links.txt` (one link per line or comma-separated; lines starting with `#` are ignored). Copy `links.example.txt` to get started. Git ignores `links.txt`.

```
# Foundry: download into the Data folder and write playlist.json
python downloader.py download "%LOCALAPPDATA%\FoundryVTT\Data\Music_Import\tavern" https://youtu.be/VIDEO_ID

# Roll20: mp3, links from links.txt
python downloader.py download "%USERPROFILE%\Downloads\YouTube-Music" --format mp3
```

| Option | What it does |
|---|---|
| `--format webm\|mp3` | Audio format (default `webm`) |
| `--links FILE` | Read links from another file |
| `--allow-playlists` | Download whole YouTube playlists. By default only the linked video is downloaded, even if the link is part of a playlist |
| `--archive` | Remember downloaded videos (in `.download-archive.txt` in the folder) and skip them next time |
| `--suffix TEXT` | Add text after each title, e.g. `--suffix " [EXTENDED]"` |
| `--playlist-json` / `--no-playlist-json` | Force `playlist.json` on or off (default: on for webm, off for mp3) |

The script exits with code 1 and lists the `FAILED:` links if any download fails.

### Rebuild the playlist only

```
python downloader.py playlist "<folder>" [--format webm|mp3]
```

Writes `playlist.json` from the audio files already in the folder, without downloading anything.

### Playlist options (both commands)

| Option | What it does |
|---|---|
| `--foundry-root DIR` | Foundry's `Data` folder. By default the script uses the nearest enclosing folder named `Data`, so track paths come out like `Music_Import/tavern/Song.webm` |
| `--foundry-folder ID` | ID of a sidebar folder to put the playlist in (default: none) |
| `--volume N` | Track volume from 0 to 1 (default 0.5) |

The playlist is named after the folder and includes **every** file of the chosen format in it, including files from earlier runs. Track IDs are derived from the file path, so they stay the same when you rebuild the playlist and import it again.

The old form `python downloader.py --generate "<folder>"` still works.

## Import into Foundry VTT

1. Download into a folder inside Foundry's `Data` directory.
2. In Foundry, open **Audio Playlists**, create a playlist, right-click it and choose **Import Data**.
3. Pick the `playlist.json` from that folder.

Tested against Foundry VTT 12.331. Importing very large playlists (100+ tracks) can lag, so split them into several folders if needed.

## Troubleshooting

- **Download fails** (403, "Unable to extract", "nsig"): update yt-dlp with `pip install -U yt-dlp`.
- **"Sign in to confirm you're not a bot" / age restriction**: export fresh cookies into `cookies.txt`.
- **ffmpeg not found**: install it (see above) or use `--format webm`.
- **Foundry can't find the tracks**: make sure the folder is inside Foundry's `Data` directory, or pass `--foundry-root`.

## Tests

```
python -m unittest discover -s tests
```

## License

Provided as-is, with no warranty. Follow YouTube's Terms of Service, and only download content you have the right to use.

Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp).
