def test_cli_help_exits_0(run_cli):
    result = run_cli("--help")

    assert result.returncode == 0
    assert "download" in result.stdout and "doctor" in result.stdout


def test_cli_download_mp3_by_default(run_cli, tmp_path, tone_url):
    folder = tmp_path / "out"

    result = run_cli("download", folder, tone_url)

    assert result.returncode == 0, result.stdout + result.stderr
    assert sorted(path.name for path in folder.iterdir()) == ["tone.mp3"]


def test_cli_download_reads_links_file(run_cli, tmp_path, tone_url):
    links = tmp_path / "links.txt"
    links.write_text(f"# test\n{tone_url}\n", encoding="utf-8")

    result = run_cli("download", tmp_path / "out", "--links", links, "--format", "webm")

    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / "out" / "tone.webm").is_file()


def test_cli_failed_download_exits_1(run_cli, tmp_path, media_server):
    missing = f"{media_server}/missing.webm"

    result = run_cli("download", tmp_path / "out", missing)

    assert result.returncode == 1
    assert f"FAILED: {missing}" in result.stdout
