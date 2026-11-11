import pytest

from yt_audio.formats import DEFAULT_FORMAT, FORMAT_NAMES, AudioFormat, M4aFormat, Mp3Format, WebmFormat


@pytest.mark.parametrize(("name", "strategy"), [("mp3", Mp3Format), ("m4a", M4aFormat), ("webm", WebmFormat)])
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
    assert FORMAT_NAMES == ("mp3", "m4a", "webm")


def test_webm_needs_no_ffmpeg():
    assert WebmFormat().ytdlp_args(ffmpeg_dir=None) == ["-f", "bestaudio[ext=webm]/bestaudio"]


def test_mp3_without_ffmpeg_raises_with_the_fix():
    with pytest.raises(RuntimeError, match=r"winget install -e --id Gyan\.FFmpeg"):
        Mp3Format().ytdlp_args(ffmpeg_dir=None)


def test_mp3_converts_at_192k_with_the_given_ffmpeg():
    args = Mp3Format().ytdlp_args(ffmpeg_dir="/ffmpeg/bin")

    assert args[args.index("--audio-quality") + 1] == "192K"
    assert args[args.index("--ffmpeg-location") + 1] == "/ffmpeg/bin"


def test_m4a_prefers_youtubes_aac_stream_and_needs_ffmpeg():
    args = M4aFormat().ytdlp_args(ffmpeg_dir="/ffmpeg/bin")

    assert args[args.index("-f") + 1] == "bestaudio[ext=m4a]/bestaudio"
    assert args[args.index("--audio-format") + 1] == "m4a"
    with pytest.raises(RuntimeError, match="ffmpeg is required for m4a"):
        M4aFormat().ytdlp_args(ffmpeg_dir=None)


@pytest.mark.parametrize(("audio_format", "tagged"), [(Mp3Format(), True), (M4aFormat(), True), (WebmFormat(), False)])
def test_converted_formats_embed_tags_and_cover_art_but_webm_stays_untouched(audio_format, tagged):
    expected = ["--embed-metadata", "--embed-thumbnail"] if tagged else []

    assert audio_format.tag_args() == expected
