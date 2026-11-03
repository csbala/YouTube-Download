# Tests

```
pip install -r requirements-dev.txt
pytest                      # unit + integration (the default; e2e is skipped)
pytest -m unit              # fast, < 1 s
pytest -m integration       # real yt-dlp + ffmpeg, no internet
pytest -m e2e               # real YouTube; needs internet, Node.js and ffmpeg
pytest --cov=yt_audio --cov-report=term-missing
ruff format --check . && ruff check . && mypy   # format, lint and strict type check, as CI runs them
```

Each test is marked with its layer automatically by the folder it's in (see `conftest.py`), so test files never repeat the marker.

## The pyramid

| Layer | Folder | What's real | What's faked | Count | Time |
|---|---|---|---|---|---|
| Unit | `unit/` | one class or function, `tmp_path` | yt-dlp, tool lookups, the services behind the CLI | many (~150) | < 2 s |
| Integration | `integration/` | yt-dlp, ffmpeg, filesystem, the CLI as a subprocess | the internet: a local HTTP server serves a tone that ffmpeg generates | some (~12) | ~5 s |
| E2E | `e2e/` | everything, including YouTube and the skill's PowerShell script | nothing | few (4) | ~30 s |

Most bugs should be caught at the bottom. Write an integration or e2e test only for what the layer below can't show, such as "yt-dlp really honours these options" or "YouTube still works".

## Principles

- **FIRST**: tests are Fast, Isolated (each gets its own `tmp_path`; nothing is shared between tests), Repeatable (no internet below e2e), Self-validating (they assert, nobody reads output), and written alongside the code.
- **Arrange, Act, Assert**: set up, do one thing, check the result. Blank lines separate the three parts.
- **One behaviour per test**, named `test_<thing>_<situation>_<expected result>`, so a failure explains itself.
- **Test behaviour, not implementation**: assert on return values, files on disk, exit codes and printed messages, not on how a function gets there.
- **Fake at the seams the design provides**, not deep inside: a fake `ToolLocator`, `override_settings()`, an `EventBus` with a recorder, the CLI's `Services`, and `yt_dlp.YoutubeDL` itself. `shutil.which`, `glob` and env vars only in `test_tools.py`, which tests the real lookups. Never mock the class being tested.
- **Tables with `@pytest.mark.parametrize`** when the same behaviour has many inputs.
- **Never touch the user's files**: an autouse fixture uses `override_settings()` to point `cookies_file` and `links_file` at `tmp_path`, and subprocess tests run a copy of `downloader.py` and the `yt_audio` package. Only e2e tests use the real repo, on purpose.

## Shared fixtures (`conftest.py`)

- `foundry_data_dir`: an empty `<tmp>/FoundryVTT/Data`.
- `make_audio_files(folder, *names)`: creates empty audio files.
- `fake_tools`: installs a `FakeToolLocator` that pretends Node.js, ffmpeg and yt-dlp-ejs are installed. Set `fake_tools.ffmpeg = None` (or `.node = None`, `.ejs = False`) to simulate a missing one.
- `recorder` / `recorded_events`: an `EventBus` that records events instead of printing them. Assert with `recorder.of_type(LinkDone)`.
- `integration/conftest.py`: `media_server` / `tone_url` (the local HTTP server) and `run_cli(*args)` (runs the CLI as a subprocess).
