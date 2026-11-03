import pytest

from downloader import foundry_relative_folder


def test_foundry_relative_folder_detects_enclosing_data_folder(foundry_data_dir):
    folder = foundry_data_dir / "music" / "boss fights"
    folder.mkdir(parents=True)

    assert foundry_relative_folder(folder) == "music/boss fights"


def test_foundry_relative_folder_detects_data_case_insensitively(tmp_path):
    folder = tmp_path / "DATA" / "Music_Import" / "apple"
    folder.mkdir(parents=True)

    assert foundry_relative_folder(folder) == "Music_Import/apple"


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
