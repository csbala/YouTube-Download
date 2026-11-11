import os

import pytest

from yt_audio.settings import PROJECT_ROOT, AppSettings, get_settings, override_settings, user_files_dir


def test_get_settings_returns_the_same_settings_every_time():
    assert get_settings() is get_settings()


def test_project_settings_point_next_to_downloader_py():
    settings = AppSettings.for_project()

    assert settings.cookies_file == os.path.join(PROJECT_ROOT, "cookies.txt")
    assert settings.links_file == os.path.join(PROJECT_ROOT, "links.txt")
    assert os.path.isfile(os.path.join(PROJECT_ROOT, "downloader.py"))


def test_override_settings_restores_the_previous_settings_even_after_an_error():
    before = get_settings()

    try:
        with override_settings(links_file="elsewhere.txt") as changed:
            assert get_settings() is changed
            assert changed.links_file == "elsewhere.txt"
            assert changed.cookies_file == before.cookies_file
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    assert get_settings() == before


def test_overrides_nest_and_unwind_in_order():
    before = get_settings()

    with override_settings(cookies_file="outer.txt"), override_settings(links_file="inner.txt") as inner:
        assert (inner.cookies_file, inner.links_file) == ("outer.txt", "inner.txt")

    assert get_settings() == before


def test_user_files_live_in_the_repo_when_running_from_a_checkout():
    assert user_files_dir(environ={}) == PROJECT_ROOT


def test_yt_audio_home_wins_over_everything(tmp_path):
    assert user_files_dir(environ={"YT_AUDIO_HOME": str(tmp_path)}) == str(tmp_path)


@pytest.mark.parametrize(
    ("os_name", "environ", "expected"),
    [
        ("nt", {"APPDATA": "C:/Users/me/AppData/Roaming"}, os.path.join("C:/Users/me/AppData/Roaming", "yt-audio")),
        ("nt", {"USERPROFILE": "C:/Users/me"}, os.path.join("C:/Users/me", "AppData", "Roaming", "yt-audio")),
        ("posix", {"XDG_CONFIG_HOME": "/home/me/.cfg"}, os.path.join("/home/me/.cfg", "yt-audio")),
        ("posix", {"HOME": "/home/me"}, os.path.join("/home/me", ".config", "yt-audio")),
    ],
)
def test_installed_package_keeps_user_files_in_the_config_folder(tmp_path, os_name, environ, expected):
    installed = tmp_path / "site-packages"  # no downloader.py next to the package

    assert user_files_dir(environ=environ, project_root=str(installed), os_name=os_name) == expected
