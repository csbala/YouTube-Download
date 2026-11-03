import os

import pytest

from yt_audio.foundry import FoundryDataLocator, foundry_relative_folder
from yt_audio.foundry.paths import iter_folder_and_ancestors


def test_foundry_relative_folder_detects_enclosing_data_folder(foundry_data_dir):
    folder = foundry_data_dir / "music" / "boss fights"
    folder.mkdir(parents=True)

    assert foundry_relative_folder(folder) == "music/boss fights"


def test_foundry_relative_folder_detects_data_case_insensitively(tmp_path):
    folder = tmp_path / "foundrydata" / "DATA" / "Music_Import" / "apple"
    folder.mkdir(parents=True)

    assert foundry_relative_folder(folder) == "Music_Import/apple"


def test_foundry_relative_folder_detects_data_next_to_config(tmp_path):
    (tmp_path / "userdata" / "Config").mkdir(parents=True)
    folder = tmp_path / "userdata" / "Data" / "music"
    folder.mkdir(parents=True)

    assert foundry_relative_folder(folder) == "music"


def test_foundry_relative_folder_ignores_unrelated_data_folder(tmp_path, capsys):
    folder = tmp_path / "projects" / "data" / "music"  # tmp_path's own name contains "foundry"
    folder.mkdir(parents=True)

    assert foundry_relative_folder(folder) == "Music_Import/music"
    assert "isn't inside a Foundry Data folder" in capsys.readouterr().out


def test_foundry_relative_folder_uses_explicit_root(tmp_path):
    folder = tmp_path / "a" / "b"
    folder.mkdir(parents=True)

    assert foundry_relative_folder(folder, tmp_path) == "a/b"


def test_foundry_relative_folder_root_itself_is_empty(foundry_data_dir):
    assert foundry_relative_folder(foundry_data_dir) == ""


def test_foundry_relative_folder_outside_root_raises(tmp_path):
    root = tmp_path / "root"
    outside = tmp_path / "elsewhere"
    root.mkdir()
    outside.mkdir()

    with pytest.raises(ValueError, match="not inside the Foundry root"):
        foundry_relative_folder(outside, root)


def test_foundry_relative_folder_without_data_falls_back_and_warns(tmp_path, capsys):
    folder = tmp_path / "Downloads" / "tavern"
    folder.mkdir(parents=True)

    assert foundry_relative_folder(folder) == "Music_Import/tavern"
    assert "isn't inside a Foundry Data folder" in capsys.readouterr().out


def test_foundry_relative_folder_other_drive_raises(monkeypatch, tmp_path):
    def different_drive(path, start):
        raise ValueError("path is on mount 'D:', start on mount 'C:'")

    monkeypatch.setattr("yt_audio.foundry.paths.os.path.relpath", different_drive)

    with pytest.raises(ValueError, match="not inside the Foundry root"):
        foundry_relative_folder(tmp_path / "music", tmp_path / "root")


def test_foundry_relative_folder_allows_names_starting_with_dots(tmp_path):
    folder = tmp_path / "..music"
    folder.mkdir()

    assert foundry_relative_folder(folder, tmp_path) == "..music"


def test_iter_folder_and_ancestors_walks_up_to_the_root(tmp_path):
    chain = list(iter_folder_and_ancestors(str(tmp_path / "a" / "b")))

    assert chain[:3] == [str(tmp_path / "a" / "b"), str(tmp_path / "a"), str(tmp_path)]
    assert chain[-1] == os.path.dirname(chain[-1])


@pytest.mark.parametrize(
    ("parts", "is_data"),
    [
        (("FoundryVTT", "Data"), True),
        (("FoundryVTT", "data"), True),
        (("projects", "data"), False),
        (("FoundryVTT", "Config"), False),
    ],
)
def test_is_foundry_data_folder(tmp_path, parts, is_data):
    folder = tmp_path.joinpath("x", *parts)  # "x" keeps tmp_path's own name (which contains "foundry") out of it

    assert FoundryDataLocator.is_foundry_data_folder(str(folder)) is is_data
