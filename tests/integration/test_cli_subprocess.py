import json


def test_cli_help_exits_0(run_cli):
    result = run_cli("--help")

    assert result.returncode == 0
    assert "download" in result.stdout and "playlist" in result.stdout


def test_cli_download_writes_audio_and_playlist(run_cli, foundry_data_dir, tone_url):
    folder = foundry_data_dir / "Music_Import" / "cli"

    result = run_cli("download", folder, tone_url)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (folder / "tone.webm").is_file()
    playlist = json.loads((folder / "playlist.json").read_text(encoding="utf-8"))
    assert [s["path"] for s in playlist["sounds"]] == ["Music_Import/cli/tone.webm"]


def test_cli_download_reads_links_file(run_cli, tmp_path, tone_url):
    links = tmp_path / "links.txt"
    links.write_text(f"# test\n{tone_url}\n", encoding="utf-8")

    result = run_cli("download", tmp_path / "out", "--links", links, "--no-playlist-json")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "out" / "tone.webm").is_file()


def test_cli_failed_download_exits_1(run_cli, tmp_path, media_server):
    missing = f"{media_server}/missing.webm"

    result = run_cli("download", tmp_path / "out", missing)

    assert result.returncode == 1
    assert f"FAILED: {missing}" in result.stdout


def test_cli_playlist_command_uses_existing_files(run_cli, foundry_data_dir, make_audio_files):
    folder = make_audio_files(foundry_data_dir / "Music_Import" / "old", "a.mp3", "b.webm")

    result = run_cli("playlist", folder, "--format", "mp3")

    assert result.returncode == 0, result.stdout + result.stderr
    playlist = json.loads((folder / "playlist.json").read_text(encoding="utf-8"))
    assert [s["name"] for s in playlist["sounds"]] == ["a"]
