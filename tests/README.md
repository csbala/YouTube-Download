# Tests

```
pip install -r requirements-dev.txt
pytest                      # unit + integration (the default; e2e is skipped)
pytest -m unit              # fast, < 1 s
pytest -m integration       # real yt-dlp + ffmpeg, no internet
pytest -m e2e               # real YouTube; needs internet, Node.js and ffmpeg
pytest --cov=downloader --cov-report=term-missing
```

Each test is marked with its layer automatically by the folder it's in (see `conftest.py`), so test files never repeat the marker.

## The pyramid

| Layer | Folder | What's real | What's faked | Count | Time |
|---|---|---|---|---|---|
| Unit | `unit/` | one function, `tmp_path` | yt-dlp, tool lookups, the other steps of `main()` | many (~70) | < 1 s |
| Integration | `integration/` | yt-dlp, ffmpeg, filesystem, the CLI as a subprocess | the internet: a local HTTP server serves a tone that ffmpeg generates | some (~12) | ~5 s |
| E2E | `e2e/` | everything, including YouTube and the skill's PowerShell script | nothing | few (4) | ~30 s |

Most bugs should be caught at the bottom. Write an integration or e2e test only for what the layer below can't show, such as "yt-dlp really honours these options" or "YouTube still works".

## Principles

- **FIRST**: tests are Fast, Isolated (each gets its own `tmp_path`; nothing is shared between tests), Repeatable (no internet below e2e), Self-validating (they assert, nobody reads output), and written alongside the code.
- **Arrange, Act, Assert**: set up, do one thing, check the result. Blank lines separate the three parts.
- **One behaviour per test**, named `test_<thing>_<situation>_<expected result>`, so a failure explains itself.
- **Test behaviour, not implementation**: assert on return values, files on disk, exit codes and printed messages, not on how a function gets there.
- **Mock only at boundaries**: `shutil.which`, `glob`, env vars, `yt_dlp.YoutubeDL` and module paths like `COOKIES_FILE`. Never mock the function being tested.
- **Tables with `@pytest.mark.parametrize`** when the same behaviour has many inputs.
- **Never touch the user's files**: an autouse fixture points `COOKIES_FILE` and `LINKS_FILE` at `tmp_path`, and subprocess tests run a copy of `downloader.py`. Only e2e tests use the real repo, on purpose.

## Shared fixtures (`conftest.py`)

- `foundry_data_dir`: an empty `<tmp>/FoundryVTT/Data`.
- `make_audio_files(folder, *names)`: creates empty audio files.
- `fake_tools`: pretends Node.js and ffmpeg are installed. Set `fake_tools.ffmpeg = None` to simulate a missing ffmpeg.
- `integration/conftest.py`: `media_server` / `tone_url` (the local HTTP server) and `run_cli(*args)` (runs the CLI as a subprocess).
