import json


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


def test_cli_json_output_is_pure_json_lines(run_cli, tmp_path, tone_url, media_server):
    missing = f"{media_server}/missing.webm"

    result = run_cli("download", tmp_path / "out", tone_url, missing, "--format", "webm", "--json")

    assert result.returncode == 1
    records = [json.loads(line) for line in result.stdout.splitlines()]  # every stdout line parses
    events = [record["event"] for record in records]
    assert events[0] in ("node_missing", "cookies_missing", "batch_started")
    assert events[-1] == "batch_finished"
    errored = next(record for record in records if record["event"] == "link_errored")
    assert errored["link"] == missing and errored["reason"]
    assert records[-1]["files"] == [str(tmp_path / "out" / "tone.webm")]
