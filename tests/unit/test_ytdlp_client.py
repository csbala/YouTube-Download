import os
from pathlib import Path

import yt_dlp

from yt_audio.ytdlp_client import open_ytdlp_client, private_cookie_copy

LOGIN = "# Netscape HTTP Cookie File\nsecret-session-value\n"


class CookieSavingYoutubeDL:
    """Behaves like the real YoutubeDL on close: writes its cookie jar back to the cookie file."""

    seen_cookiefile = None

    def __init__(self, opts):
        self.opts = opts
        CookieSavingYoutubeDL.seen_cookiefile = opts.get("cookiefile")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.opts.get("cookiefile"):
            with open(self.opts["cookiefile"], "w", encoding="utf-8") as file:
                file.write("# rewritten by yt-dlp\n")
        return False


def test_ytdlp_never_writes_to_the_users_cookie_file(tmp_path, monkeypatch):
    monkeypatch.setattr(yt_dlp, "YoutubeDL", CookieSavingYoutubeDL)
    cookies = tmp_path / "cookies.txt"
    cookies.write_text(LOGIN, encoding="utf-8")
    modified_before = os.path.getmtime(cookies)

    with open_ytdlp_client({"cookiefile": str(cookies)}):
        pass

    assert cookies.read_text(encoding="utf-8") == LOGIN
    assert os.path.getmtime(cookies) == modified_before
    assert CookieSavingYoutubeDL.seen_cookiefile != str(cookies)
    assert not os.path.exists(CookieSavingYoutubeDL.seen_cookiefile)  # the copy is cleaned up


def test_ytdlp_gets_no_cookie_file_when_there_is_none(monkeypatch):
    monkeypatch.setattr(yt_dlp, "YoutubeDL", CookieSavingYoutubeDL)

    with open_ytdlp_client({}):
        pass

    assert CookieSavingYoutubeDL.seen_cookiefile is None


def test_cookie_copy_holds_the_login_and_is_removed_even_after_an_error(tmp_path):
    cookies = tmp_path / "cookies.txt"
    cookies.write_text(LOGIN, encoding="utf-8")
    copy_path = None

    try:
        with private_cookie_copy(str(cookies)) as copy_path:
            assert Path(copy_path).read_text(encoding="utf-8") == LOGIN
            raise KeyboardInterrupt
    except KeyboardInterrupt:
        pass

    assert copy_path is not None
    assert not os.path.exists(copy_path)
