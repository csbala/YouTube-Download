import pytest

from downloader import downloaded_files


def video(*paths):
    return {"requested_downloads": [{"filepath": p} for p in paths]}


@pytest.mark.parametrize("info, expected", [
    (None, []),
    ({}, []),
    (video("a.mp3"), ["a.mp3"]),
    ({"requested_downloads": [{"filepath": None}, {}]}, []),
    ({"entries": [video("a.mp3"), None, video("b.mp3")]}, ["a.mp3", "b.mp3"]),
    ({"entries": [{"entries": [video("nested.mp3")]}]}, ["nested.mp3"]),
    ({"entries": []}, []),
], ids=["none", "empty", "video", "missing-filepath", "playlist", "nested-playlist", "empty-playlist"])
def test_downloaded_files(info, expected):
    assert downloaded_files(info) == expected
