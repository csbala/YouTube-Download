import string

from downloader import stable_id


def test_stable_id_same_input_gives_same_id():
    assert stable_id("Music_Import/apple/song.webm") == stable_id("Music_Import/apple/song.webm")


def test_stable_id_different_input_gives_different_id():
    assert stable_id("a/song.webm") != stable_id("b/song.webm")


def test_stable_id_is_16_alphanumeric_chars():
    track_id = stable_id("árvíztűrő tükörfúrógép.webm")

    assert len(track_id) == 16
    assert set(track_id) <= set(string.ascii_letters + string.digits)
