import json
from datetime import datetime

from yt_audio.events import PlaylistWritten
from yt_audio.foundry.playlist import (
    FOUNDRY_SOUND,
    JsonFileSink,
    MemorySink,
    PlaylistAssembler,
    PlaylistOptions,
    PlaylistWriter,
    SoundPrototype,
)


def test_clones_do_not_share_mutable_state_with_the_prototype():
    prototype = SoundPrototype({"name": "", "flags": {}})

    first = prototype.clone(name="a")
    first["flags"]["changed"] = True
    second = prototype.clone(name="b")

    assert second == {"name": "b", "flags": {}}


def test_foundry_sound_keeps_foundrys_key_order():
    sound = FOUNDRY_SOUND.clone(name="a", sort=3)

    assert list(sound) == [
        "name",
        "path",
        "channel",
        "repeat",
        "fade",
        "description",
        "volume",
        "_id",
        "playing",
        "pausedTime",
        "sort",
        "flags",
    ]
    assert sound["sort"] == 3


def test_writer_hands_the_playlist_to_its_sink(foundry_data_dir, make_audio_files, recorder, recorded_events):
    folder = make_audio_files(foundry_data_dir / "Music_Import" / "tavern", "a.webm")
    sink = MemorySink()

    location = PlaylistWriter(sink, recorded_events).write(folder, PlaylistOptions())

    assert location == "<memory #1>"
    assert [s["name"] for s in sink.saved[0]["sounds"]] == ["a"]
    assert recorder.of_type(PlaylistWritten) == [PlaylistWritten(1, "<memory #1>")]
    assert not (folder / "playlist.json").exists()


def test_json_sink_writes_a_custom_filename(tmp_path):
    output_path = JsonFileSink("custom.json").save({"sounds": []}, tmp_path)

    assert json.loads((tmp_path / "custom.json").read_text(encoding="utf-8")) == {"sounds": []}
    assert output_path == str(tmp_path / "custom.json")


def test_assembler_stamps_the_playlist_with_the_given_clock(foundry_data_dir, recorded_events):
    moment = datetime(2026, 1, 2, 3, 4, 5)

    playlist = PlaylistAssembler(recorded_events, now=lambda: moment).assemble(foundry_data_dir, PlaylistOptions())

    expected = int(moment.timestamp() * 1000)
    assert playlist["_stats"]["createdTime"] == playlist["_stats"]["modifiedTime"] == expected
