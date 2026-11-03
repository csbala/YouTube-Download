import pytest

from yt_audio.media import (
    NOTHING_DOWNLOADED,
    FailedEntryNode,
    PlaylistHealth,
    PlaylistHealthInspector,
    PlaylistNode,
    VideoNode,
    YtDlpInfoAdapter,
    downloaded_files,
)


def video(*paths):
    return {"requested_downloads": [{"filepath": p} for p in paths]}


@pytest.mark.parametrize(
    ("info", "expected"),
    [
        (None, []),
        ({}, []),
        (video("a.mp3"), ["a.mp3"]),
        ({"requested_downloads": [{"filepath": None}, {}]}, []),
        ({"entries": [video("a.mp3"), None, video("b.mp3")]}, ["a.mp3", "b.mp3"]),
        ({"entries": [{"entries": [video("nested.mp3")]}]}, ["nested.mp3"]),
        ({"entries": []}, []),
    ],
    ids=["none", "empty", "video", "missing-filepath", "playlist", "nested-playlist", "empty-playlist"],
)
def test_downloaded_files(info, expected):
    assert downloaded_files(info) == expected


def test_adapter_builds_a_tree_of_videos_playlists_and_failed_entries():
    info = {"entries": [{"id": "a", "title": "A", **video("a.mp3")}, None, {"entries": [video("b.mp3")]}]}

    assert YtDlpInfoAdapter.to_media(info) == PlaylistNode(
        (
            VideoNode("a", "A", ("a.mp3",)),
            FailedEntryNode(),
            PlaylistNode((VideoNode(None, None, ("b.mp3",)),)),
        )
    )


def test_adapter_treats_a_skipped_video_as_nothing_downloaded():
    assert YtDlpInfoAdapter.to_media(None) is NOTHING_DOWNLOADED


def test_iter_videos_walks_nested_playlists_in_order_and_skips_failed_entries():
    tree = PlaylistNode(
        (
            VideoNode("1", None, ()),
            FailedEntryNode(),
            PlaylistNode((VideoNode("2", None, ()), PlaylistNode((VideoNode("3", None, ()),)))),
        )
    )

    assert [v.video_id for v in tree.iter_videos()] == ["1", "2", "3"]


@pytest.mark.parametrize(
    ("tree", "health"),
    [
        (NOTHING_DOWNLOADED, PlaylistHealth(0, 0)),
        (VideoNode("1", None, ()), PlaylistHealth(1, 0)),
        (PlaylistNode((VideoNode("1", None, ()), FailedEntryNode(), PlaylistNode((FailedEntryNode(),)))), PlaylistHealth(3, 2)),
    ],
    ids=["nothing", "single-video", "nested-with-failures"],
)
def test_health_inspector_counts_items_and_failures_anywhere_in_the_tree(tree, health):
    assert tree.accept(PlaylistHealthInspector()) == health
