# YouTube Audio Downloader & Foundry VTT Playlist Generator

Downloads audio from YouTube links and, for Foundry Virtual Tabletop, writes a `playlist.json` you can import straight into the Audio Playlists tab.

- **webm** (default): for Foundry VTT. Also writes `playlist.json`.
- **mp3**: for Roll20's jukebox (which only accepts mp3) and most other tools. Needs ffmpeg.

## Requirements

- **Python 3.10 or later** (yt-dlp needs it)
- **yt-dlp** 2025.11.12 or newer, with its default extras (they include `yt-dlp-ejs`, the YouTube challenge solver): `pip install -r requirements.txt`
- **Node.js**: yt-dlp uses it to solve YouTube's JavaScript challenge. `winget install -e --id OpenJS.NodeJS.LTS`
- **ffmpeg** (mp3 only): `winget install -e --id Gyan.FFmpeg`. The script finds a winget install even before you open a new terminal.
- **cookies.txt** (optional): needed for age-restricted videos and "confirm you're not a bot" blocks. Export your YouTube cookies with a browser extension such as "Get cookies.txt LOCALLY" and save the file as `cookies.txt` next to `downloader.py`. Git ignores it. **Never commit it**: it's your Google login.

## Usage

### Check your setup

```
python downloader.py doctor
```

Lists what's ready and what's missing (yt-dlp, Node.js, ffmpeg, cookies.txt), each with the command that fixes it. Exits with code 1 if something blocks a download.

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

The script exits with code 1 and lists the `FAILED:` links if any download fails. A playlist link with some broken videos is listed too, with how many failed. If it can't start (for example, ffmpeg is missing for mp3) or can't write `playlist.json`, it exits with code 2.

Files are named after the video title. Very long titles are shortened so the full path stays under Windows' 260-character limit. If two different videos have the same title, the second one is reported as failed instead of silently skipped: download it again on its own with `--suffix`.

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

- **Download fails** (403, "Unable to extract", "nsig"): update yt-dlp with `pip install -U "yt-dlp[default]"`.
- **"Sign in to confirm you're not a bot" / age restriction**: export fresh cookies into `cookies.txt`.
- **Not sure what's wrong**: run `python downloader.py doctor`.
- **ffmpeg not found**: install it (see above) or use `--format webm`.
- **Foundry can't find the tracks**: make sure the folder is inside Foundry's `Data` directory, or pass `--foundry-root`. The script only recognises a `Data` folder that sits next to Foundry's `Config` folder or inside a folder with "foundry" in its name.

## Architecture

`downloader.py` is only the entry point. The code lives in the `yt_audio` package, one concern per module, and each module's docstring names the design patterns it uses (names from the [refactoring.guru catalog](https://refactoring.guru/design-patterns/python)).

```
downloader.py           entry point: python downloader.py <command>
yt_audio/
  cli.py                the download / playlist / doctor commands
  download.py           batch download: one session per run, duplicate-title detection, results
  ydl_options.py        a download request -> yt-dlp options
  ydl_client.py         fetching one link, with errors turned into results
  media.py              yt-dlp's info dicts -> a typed tree of videos and playlists
  formats.py            webm and mp3
  targets.py            Foundry (webm + playlist.json) and Roll20 (mp3, no playlist)
  foundry/paths.py      finding Foundry's Data folder
  foundry/playlist.py   building and writing playlist.json
  doctor.py             the setup checks
  tools.py              finding Node.js and ffmpeg
  events.py             progress events and the console messages they print
  links.py              reading links.txt
  settings.py           paths (cookies.txt, links.txt) and constants
```

| Pattern | Where | Why |
|---|---|---|
| Command | `cli.DownloadCommand`, `PlaylistCommand`, `DoctorCommand` | Each subcommand declares and runs itself; `main()` only dispatches |
| Facade | `yt_audio/__init__.py`, `download.AudioDownloader` | One simple entry point over yt-dlp and the rest of the package |
| Mediator | `download.BatchDownloadSession` | Coordinates the yt-dlp client, the file-ownership registry and the event bus, which never talk to each other |
| Builder + Director | `ydl_options.YdlOptionsBuilder`, `YdlOptionsDirector` | yt-dlp options are added one concern at a time |
| Decorator | `ydl_client.ErrorTranslatingClient` | Wraps the client and turns yt-dlp/OS errors into a `LinkFailed` result, so the loop needs no try/except |
| Adapter | `media.YtDlpInfoAdapter` | Only this class knows yt-dlp's raw dict shape (`entries`, `None` entries, `requested_downloads`) |
| Composite | `media.VideoNode`, `FailedEntryNode`, `PlaylistNode` | A video and a playlist of playlists are handled the same way |
| Iterator | `MediaNode.iter_videos()`, `links.iter_links()`, `foundry.paths.iter_folder_and_ancestors()` | Lazy traversal with generators |
| Visitor | `media.PlaylistHealthInspector`, `DownloadedFilesCollector` | New calculations over the media tree without changing the node classes |
| Strategy | `formats.WebmFormat`, `Mp3Format` | Replaces `if audio_format == "mp3"` branches |
| Factory Method | `AudioFormat.from_name()`, `VttTarget.for_format()` | Turns a command-line choice into the right object |
| Flyweight | the shared format instances in `formats.AUDIO_FORMATS` | Formats hold no per-download state, so one instance each is shared |
| Abstract Factory | `targets.FoundryTarget`, `Roll20Target` | Each tabletop gets a matching audio format and playlist exporter, so "playlist.json is on for webm, off for mp3" lives in one place |
| Prototype | `foundry.playlist.FOUNDRY_SOUND.clone()` | Each Foundry track is a copy of one fully filled-in template |
| Bridge | `foundry.playlist.PlaylistWriter` with `JsonFileSink` / `MemorySink` | What the playlist is and where it's stored can vary separately |
| Template Method | `doctor.SetupCheck.run()` | Every check follows the same probe, find problem, describe OK steps |
| Chain of Responsibility | `tools.SystemPathLookup` → `KnownLocationLookup` / `WingetPackageLookup` | Each lookup tries one place, then passes the search on |
| Proxy | `tools.CachingToolLocator` | Looks each tool up only once per run |
| Observer | `events.EventBus`, `ConsoleReporter` | Library code reports events instead of printing; all user-facing progress messages live in one class |
| Singleton | `settings.SettingsHolder` | One thread-safe place for the paths every module reads |
| Memento | `SettingsHolder.save()` / `restore()`, used by `override_settings()` | Settings can be changed temporarily and rolled back, e.g. in tests |

**State** isn't used: nothing here changes its behaviour over its lifetime, so a state machine would add classes without removing any branches.

## Tests

```
pip install -r requirements-dev.txt
pytest              # unit + integration, no internet needed
pytest -m e2e       # real YouTube downloads
ruff format .       # format the code
ruff check .        # lint, including complexity (max 10) and security checks
mypy                # strict type check of yt_audio
pip-audit -r requirements.txt   # known vulnerabilities in dependencies
```

See [tests/README.md](tests/README.md) for how the suite is organised. GitHub Actions runs all four checks, plus unit and integration tests on Windows and Linux, on every push.

## License

Provided as-is, with no warranty. Follow YouTube's Terms of Service, and only download content you have the right to use.

Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp).
