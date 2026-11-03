import pytest

from yt_audio.formats import DEFAULT_FORMAT, FORMAT_NAMES, AudioFormat, Mp3Format, WebmFormat


@pytest.mark.parametrize(("name", "strategy"), [("mp3", Mp3Format), ("webm", WebmFormat)])
def test_from_name_returns_the_shared_strategy(name, strategy):
    audio_format = AudioFormat.from_name(name)

    assert isinstance(audio_format, strategy)
    assert audio_format is AudioFormat.from_name(name)  # one shared instance per format
    assert audio_format.extension == f".{name}"


def test_from_name_rejects_unknown_formats():
    with pytest.raises(ValueError, match="unknown audio format 'flac'"):
        AudioFormat.from_name("flac")


def test_mp3_is_the_default_and_listed_first():
    assert DEFAULT_FORMAT == "mp3"
    assert FORMAT_NAMES == ("mp3", "webm")


def test_webm_needs_no_ffmpeg():
    assert WebmFormat().ytdlp_args(ffmpeg_dir=None) == ["-f", "bestaudio[ext=webm]/bestaudio"]


def test_mp3_without_ffmpeg_raises_with_the_fix():
    with pytest.raises(RuntimeError, match=r"winget install -e --id Gyan\.FFmpeg"):
        Mp3Format().ytdlp_args(ffmpeg_dir=None)


def test_mp3_converts_at_192k_with_the_given_ffmpeg():
    args = Mp3Format().ytdlp_args(ffmpeg_dir="/ffmpeg/bin")

    assert args[args.index("--audio-quality") + 1] == "192K"
    assert args[args.index("--ffmpeg-location") + 1] == "/ffmpeg/bin"
