import pytest

from yt_audio.links import iter_links, read_links


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ("https://a\nhttps://b\n", ["https://a", "https://b"]),
        ("https://a, https://b,https://c", ["https://a", "https://b", "https://c"]),
        ("https://a\n\n\nhttps://b", ["https://a", "https://b"]),
        ("  https://a  \n\thttps://b\t", ["https://a", "https://b"]),
        ("# my list\nhttps://a\n  # indented comment\n", ["https://a"]),
        ("https://a, https://b\nhttps://c", ["https://a", "https://b", "https://c"]),
        ("", []),
    ],
    ids=["lines", "commas", "blank-lines", "whitespace", "comments", "mixed", "empty"],
)
def test_read_links_parses_file_formats(tmp_path, content, expected):
    links_file = tmp_path / "links.txt"
    links_file.write_text(content, encoding="utf-8")

    assert read_links(links_file) == expected


def test_read_links_handles_utf8(tmp_path):
    links_file = tmp_path / "links.txt"
    links_file.write_text("# zenék, árvíztűrő\nhttps://youtu.be/x\n", encoding="utf-8")

    assert read_links(links_file) == ["https://youtu.be/x"]


def test_read_links_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_links(tmp_path / "missing.txt")


def test_iter_links_is_lazy(tmp_path):
    links_file = tmp_path / "links.txt"
    links_file.write_text("https://a\nhttps://b\n", encoding="utf-8")

    links = iter_links(links_file)

    assert next(links) == "https://a"
    assert list(links) == ["https://b"]
