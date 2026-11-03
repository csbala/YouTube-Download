import os
import threading

from yt_audio.settings import PROJECT_ROOT, AppSettings, SettingsHolder, get_settings, override_settings


def test_settings_holder_is_a_singleton_even_across_threads():
    holders = []
    threads = [threading.Thread(target=lambda: holders.append(SettingsHolder())) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert all(holder is SettingsHolder() for holder in holders)


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


def test_memento_round_trip():
    holder = SettingsHolder()
    memento = holder.save()
    holder.update(cookies_file="x")

    holder.restore(memento)

    assert holder.settings.cookies_file != "x"
