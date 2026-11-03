import pytest

from yt_audio import build_playlist


@pytest.fixture
def apple_folder(foundry_data_dir):
    return foundry_data_dir / "Music_Import" / "apple"


def test_build_playlist_lists_tracks_sorted_by_filename(apple_folder, make_audio_files):
    make_audio_files(apple_folder, "B song.webm", "A song.webm", "C song.webm")

    playlist = build_playlist(apple_folder)

    assert [s["name"] for s in playlist["sounds"]] == ["A song", "B song", "C song"]
    assert [s["sort"] for s in playlist["sounds"]] == [0, 1, 2]


@pytest.mark.parametrize(
    ("audio_format", "expected"),
    [
        ("webm", ["a", "b"]),
        ("mp3", ["c", "d"]),
    ],
)
def test_build_playlist_includes_only_chosen_format(apple_folder, make_audio_files, audio_format, expected):
    make_audio_files(apple_folder, "a.webm", "b.WEBM", "c.mp3", "d.MP3", "notes.txt", "playlist.json")

    playlist = build_playlist(apple_folder, audio_format=audio_format)

    assert [s["name"] for s in playlist["sounds"]] == expected


@pytest.mark.parametrize(
    ("filename", "expected_path"),
    [
        ("A song.webm", "Music_Import/apple/A%20song.webm"),
        ("Track #1.webm", "Music_Import/apple/Track%20%231.webm"),
        ("Zene ő.webm", "Music_Import/apple/Zene%20%C5%91.webm"),
    ],
)
def test_build_playlist_url_encodes_paths(apple_folder, make_audio_files, filename, expected_path):
    make_audio_files(apple_folder, filename)

    [sound] = build_playlist(apple_folder)["sounds"]

    assert sound["path"] == expected_path


def test_build_playlist_passes_options_through(apple_folder, make_audio_files):
    make_audio_files(apple_folder, "a.webm")

    playlist = build_playlist(apple_folder, volume=0.3, foundry_folder="folder123")

    assert playlist["folder"] == "folder123"
    assert playlist["sounds"][0]["volume"] == 0.3


def test_build_playlist_defaults(apple_folder, make_audio_files):
    make_audio_files(apple_folder, "a.webm")

    playlist = build_playlist(apple_folder)

    assert playlist["name"] == "apple"
    assert playlist["folder"] is None
    assert playlist["sounds"][0]["volume"] == 0.5
    assert playlist["flags"] == {}
    assert set(playlist["_stats"]) == {"coreVersion", "createdTime", "modifiedTime"}


def test_build_playlist_ids_are_stable_and_unique(apple_folder, make_audio_files):
    make_audio_files(apple_folder, "a.webm", "b.webm")

    first = [s["_id"] for s in build_playlist(apple_folder)["sounds"]]
    second = [s["_id"] for s in build_playlist(apple_folder)["sounds"]]

    assert first == second
    assert len(set(first)) == 2


def test_build_playlist_empty_folder_warns(apple_folder, capsys):
    apple_folder.mkdir(parents=True)

    playlist = build_playlist(apple_folder)

    assert playlist["sounds"] == []
    assert "Playlist will be empty" in capsys.readouterr().out


def test_build_playlist_in_data_root_has_bare_filenames(foundry_data_dir, make_audio_files):
    make_audio_files(foundry_data_dir, "a.webm")

    [sound] = build_playlist(foundry_data_dir)["sounds"]

    assert sound["path"] == "a.webm"
