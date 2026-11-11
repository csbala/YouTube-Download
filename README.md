# YouTube Audio Downloader

Saves the audio of YouTube videos to a folder, as **mp3**, **m4a** or **webm**, with the title, artist and cover art written into mp3 and m4a files.

```
python downloader.py download "%USERPROFILE%\Downloads\YouTube-Music" https://youtu.be/VIDEO_ID
```

| Format | Pick it when | Needs |
|---|---|---|
| **mp3** (default) | You want files that play everywhere: phones, music players, Roll20's jukebox, Foundry VTT | ffmpeg |
| **m4a** | You want the best quality: YouTube's AAC audio, repackaged rather than re-encoded. Plays on phones, iTunes/Music and most players, but not Roll20 | ffmpeg |
| **webm** | You want YouTube's original audio with no conversion, and your player supports it. Not tagged | nothing extra |

## Setup

1. **Python 3.10 or later**, then `pip install -r requirements.txt` (installs yt-dlp).
2. **Node.js**: yt-dlp uses it to solve YouTube's JavaScript challenge. `winget install -e --id OpenJS.NodeJS.LTS`
3. **ffmpeg** (for mp3): `winget install -e --id Gyan.FFmpeg`. The script finds a fresh winget install even before you open a new terminal.
4. **cookies.txt** (optional): needed for age-restricted videos and "confirm you're not a bot" blocks. Export your YouTube cookies with a browser extension such as "Get cookies.txt LOCALLY" and save the file as `cookies.txt` in the [user files folder](#where-cookiestxt-and-linkstxt-live) (next to `downloader.py` when you run from this repo). Git ignores it. **Never commit it**: it's your Google login. yt-dlp is only ever given a temporary copy, so your file is never rewritten.

Then check everything is ready:

```
python downloader.py doctor
```

It prints one `[OK]`, `[WARN]` or `[MISSING]` line per item, each with the command that fixes it.

### Install as a command (optional)

To run it from any folder as `yt-audio` instead of `python downloader.py`, install it with [pipx](https://pipx.pypa.io/):

```
pipx install git+https://github.com/csbala/YouTube-Download
yt-audio doctor
yt-audio download "%USERPROFILE%\Downloads\YouTube-Music" https://youtu.be/VIDEO_ID
```

Upgrade with `pipx upgrade yt-audio`; `yt-audio --version` shows the installed version along with yt-dlp's.

### Where cookies.txt and links.txt live

1. In the folder named by the `YT_AUDIO_HOME` environment variable, if it's set.
2. Otherwise, when you run from this repo: the repo folder, next to `downloader.py`.
3. Otherwise (installed with pipx or pip): `%APPDATA%\yt-audio` on Windows, `~/.config/yt-audio` elsewhere.

`doctor` prints the exact path it checks. `--cookies FILE` and `--links FILE` point a single run somewhere else.

## Downloading

```
python downloader.py download "<folder>" [links...] [options]
```

Pass links as arguments, or leave them out to read `links.txt` (one link per line or comma-separated; lines starting with `#` are ignored). Copy `links.example.txt` to get started. Git ignores `links.txt`.

| Option | What it does |
|---|---|
| `--format mp3\|m4a\|webm` | Audio format (default `mp3`) |
| `--links FILE` | Read links from another file |
| `--cookies FILE` | Use another cookies file (also works with `doctor`) |
| `--no-tags` | Don't write title, artist and cover art into mp3/m4a files |
| `--json` | Print progress and the summary as JSON lines, for scripts (see below) |
| `--allow-playlists` | Download whole YouTube playlists. By default only the linked video is downloaded, even if it's part of a playlist |
| `--archive` | Remember downloaded videos (in `.download-archive.txt` in the folder) and skip them next time |
| `--suffix TEXT` | Add text after each title, e.g. `--suffix " [EXTENDED]"` |

Files are named after the video title. Very long titles are shortened so the full path stays under Windows' 260-character limit. If two different videos have the same title, the second one is reported as failed instead of silently overwriting the first: download it again on its own with `--suffix`.

**Exit codes:** `0` every link downloaded, `1` some links failed (each is listed on a `FAILED:` line; for a playlist, with how many items failed), `2` couldn't start (for example, ffmpeg is missing for mp3, or there were no links), `130` stopped with Ctrl+C (the summary still lists what finished, and `NOT FINISHED:` lines list the rest).

**JSON output:** with `--json`, stdout carries only JSON lines, one per event, such as `{"event": "link_done", "link": "...", "files": ["..."]}`. The last one is `batch_finished`, with `files`, `failed_links`, `unfinished` and `downloaded_count`; a run that couldn't start prints `run_failed` with a `message`. yt-dlp's own messages are silenced, and its errors go to stderr and also arrive as `link_errored` events with a `reason`. The download-music skill uses this mode, so it never depends on yt-dlp's wording.

## Troubleshooting

| You see | Do this |
|---|---|
| 403, "Unable to extract", "nsig" | Update yt-dlp: `pip install -U "yt-dlp[default]"` |
| "Sign in to confirm you're not a bot" / age restriction | Export fresh cookies into `cookies.txt` |
| "ffmpeg is required for mp3" (or m4a) | Install ffmpeg (see Setup) or use `--format webm` |
| Roll20 says "You can't upload files of this type" | The file is webm; download it again as mp3 |
| Not sure what's wrong | `python downloader.py doctor` |

## How the code is organised

`downloader.py` is only the entry point. The code lives in the `yt_audio` package, one job per module:

```
downloader.py           entry point: python downloader.py <download|doctor>
yt_audio/
  cli.py                the download and doctor commands
  download.py           downloads a batch of links and decides which ones failed
  ytdlp_options.py      turns a download request into yt-dlp options
  ytdlp_client.py       fetches one link, turning errors into results
  media.py              turns yt-dlp's raw info dicts into a typed tree of videos and playlists
  formats.py            mp3, m4a and webm, and how each is tagged
  doctor.py             the setup checks
  tools.py              finds Node.js and ffmpeg
  events.py             progress events and the console messages they print
  links.py              reads links.txt
  settings.py           where cookies.txt and links.txt live, and constants
  version.py            the version, and what --version prints
```

A download flows like this:

```
cli.DownloadCommand ─► download.AudioDownloader ─► ytdlp_options (build options once)
                                │
                                └─► BatchDownloadSession, for each link:
                                      ytdlp_client.fetch(link) ─► media tree ─► keep new files, spot title clashes
                                      events ─► ConsoleReporter prints progress
```

### Design patterns

Each module's docstring names the patterns it uses (names from the [refactoring.guru catalog](https://refactoring.guru/design-patterns/python)). A pattern is used only where it removes a branch, a dependency or a repeated step:

| Pattern | Where | What it saves |
|---|---|---|
| Command | `cli.DownloadCommand`, `DoctorCommand` | Each subcommand declares and runs itself; `main()` only dispatches |
| Facade | `yt_audio/__init__.py`, `download.AudioDownloader` | One simple entry point over yt-dlp and the rest of the package |
| Mediator | `download.BatchDownloadSession` | The yt-dlp client, the file-ownership registry and the event bus never talk to each other |
| Builder + Director | `ytdlp_options.YtDlpOptionsBuilder`, `YtDlpOptionsDirector` | yt-dlp options are added one concern at a time, in one readable chain |
| Decorator | `ytdlp_client.ErrorTranslatingClient` | Turns yt-dlp and OS errors into a `LinkFailed` result, so the batch loop needs no try/except |
| Adapter | `media.YtDlpInfoAdapter` | Only this class knows yt-dlp's raw dict shape (`entries`, `None` entries, `requested_downloads`) |
| Composite | `media.VideoNode`, `FailedEntryNode`, `PlaylistNode` | A video and a playlist of playlists are handled the same way |
| Iterator | `MediaNode.iter_videos()`, `links.iter_links()` | Lazy traversal with generators |
| Strategy + Factory Method | `formats.Mp3Format`, `M4aFormat`, `WebmFormat`, `AudioFormat.from_name()` | No `if audio_format == "mp3"` branches; adding a format means adding a class (m4a was one) |
| Template Method | `doctor.SetupCheck.run()` | Every check follows the same probe, find problem, describe OK steps |
| Chain of Responsibility | `tools.SystemPathLookup` → `KnownLocationLookup` / `WingetPackageLookup` | Each lookup tries one place, then passes the search on |
| Proxy | `tools.CachingToolLocator` | Each tool is looked up only once per run |
| Observer | `events.EventBus`, `ConsoleReporter`, `JsonReporter` | Library code reports events instead of printing; every user-facing progress message lives in one class, and `--json` is just another subscriber |

Patterns deliberately **not** used, because here they would add classes without removing any complexity: **Visitor** (the media tree has two calculations, which are plain Composite methods), **Abstract Factory**, **Bridge** and **Prototype** (they served the old Foundry playlist export), **State** (nothing changes behaviour over its lifetime), **Flyweight** (there's nothing heavy to share), and **Singleton + Memento**, which settings used to have: a module-level value that `override_settings()` swaps does the same job in a few lines.

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

See [tests/README.md](tests/README.md) for how the suite is organised. GitHub Actions runs all of these, with unit and integration tests on Windows and Linux, on every push.

## Upgrading from 3.0

Nothing to change: running from the repo still reads `cookies.txt` and `links.txt` from the repo folder. New in 3.1: the m4a format, title/artist/cover-art tags (turn off with `--no-tags`), `--json`, `--cookies`, `--version`, pipx install, exit code `2` for an empty links file and `130` for Ctrl+C, and yt-dlp no longer rewrites your `cookies.txt` (so the doctor's "cookies are old" warning now works).

## Upgrading from 2.x

Version 3 is a general audio downloader. The Foundry VTT support is gone: the `playlist` command, `playlist.json`, `--playlist-json`, `--foundry-root`, `--foundry-folder`, `--volume` and the old `--generate` form. The default format is now **mp3**. Foundry still plays the mp3 files; import them through its own Audio Playlists tab.

## License

Provided as-is, with no warranty. Follow YouTube's Terms of Service, and only download content you have the right to use.

Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp).
