import pytest

from yt_audio.formats import AUDIO_FORMATS, FORMAT_NAMES, AudioFormat, Mp3Format, WebmFormat
from yt_audio.foundry.playlist import PlaylistOptions
from yt_audio.targets import FoundryPlaylistExporter, FoundryTarget, NoPlaylistExporter, Roll20Target, VttTarget


@pytest.mark.parametrize(("name", "strategy"), [("webm", WebmFormat), ("mp3", Mp3Format)])
def test_from_name_returns_the_shared_strategy(name, strategy):
    audio_format = AudioFormat.from_name(name)

    assert isinstance(audio_format, strategy)
    assert audio_format is AudioFormat.from_name(name)  # Flyweight: one instance per format
    assert audio_format.extension == f".{name}"


def test_from_name_rejects_unknown_formats():
    with pytest.raises(ValueError, match="unknown audio format 'flac'"):
        AudioFormat.from_name("flac")


def test_format_names_are_the_cli_choices():
    assert FORMAT_NAMES == ("webm", "mp3")


@pytest.mark.parametrize(("filename", "owned"), [("a.webm", True), ("B.WEBM", True), ("a.mp3", False), ("webm", False)])
def test_format_owns_only_its_own_files_case_insensitively(filename, owned):
    assert AUDIO_FORMATS["webm"].owns_file(filename) is owned


def test_webm_needs_no_ffmpeg():
    assert WebmFormat().ydl_args(ffmpeg_dir=None) == ["-f", "bestaudio[ext=webm]/bestaudio"]


@pytest.mark.parametrize(
    ("format_name", "target", "exporter"),
    [
        ("webm", FoundryTarget, FoundryPlaylistExporter),
        ("mp3", Roll20Target, NoPlaylistExporter),
    ],
)
def test_each_target_creates_a_matching_family(format_name, target, exporter):
    vtt = VttTarget.for_format(format_name)

    assert isinstance(vtt, target)
    assert vtt.create_audio_format() is AudioFormat.from_name(format_name)
    assert isinstance(vtt.create_playlist_exporter(lambda folder, **options: None), exporter)


def test_foundry_exporter_passes_every_playlist_option_through():
    written = []
    exporter = FoundryPlaylistExporter(lambda folder, **options: written.append((folder, options)))

    exporter.export("music", PlaylistOptions(audio_format="mp3", foundry_root="root", volume=0.2, foundry_folder="abc"))

    assert written == [("music", {"audio_format": "mp3", "foundry_root": "root", "volume": 0.2, "foundry_folder": "abc"})]


def test_no_playlist_exporter_writes_nothing(tmp_path):
    NoPlaylistExporter().export(tmp_path, PlaylistOptions())

    assert list(tmp_path.iterdir()) == []
