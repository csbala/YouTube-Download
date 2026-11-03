import json
import urllib.parse

from yt_audio import write_playlist


def test_write_playlist_json_points_at_real_files(foundry_data_dir, make_audio_files):
    folder = make_audio_files(foundry_data_dir / "Music_Import" / "tavern", "Drinking Song.webm", "Bard #2.webm")

    write_playlist(str(folder))

    playlist = json.loads((folder / "playlist.json").read_text(encoding="utf-8"))
    assert playlist["name"] == "tavern"
    for sound in playlist["sounds"]:
        assert (foundry_data_dir / urllib.parse.unquote(sound["path"])).is_file()


def test_write_playlist_rerun_keeps_ids_and_adds_new_tracks(foundry_data_dir, make_audio_files):
    folder = make_audio_files(foundry_data_dir / "Music_Import" / "tavern", "a.webm")
    write_playlist(str(folder))
    first = json.loads((folder / "playlist.json").read_text(encoding="utf-8"))

    make_audio_files(folder, "b.webm")
    write_playlist(str(folder))
    second = json.loads((folder / "playlist.json").read_text(encoding="utf-8"))

    ids = {s["name"]: s["_id"] for s in second["sounds"]}
    assert ids["a"] == first["sounds"][0]["_id"]
    assert set(ids) == {"a", "b"}
