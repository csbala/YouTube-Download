import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import downloader  # noqa: E402


def touch(folder, *names):
    for name in names:
        open(os.path.join(folder, name), "w").close()


class ReadLinksTest(unittest.TestCase):
    def test_lines_commas_and_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "links.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("# my list\nhttps://a, https://b\n\nhttps://c\n")
            self.assertEqual(downloader.read_links(path), ["https://a", "https://b", "https://c"])


class FoundryPathTest(unittest.TestCase):
    def test_detects_data_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, "FoundryVTT", "Data", "music", "boss fights")
            os.makedirs(folder)
            self.assertEqual(downloader.foundry_relative_folder(folder), "music/boss fights")

    def test_explicit_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, "a", "b")
            os.makedirs(folder)
            self.assertEqual(downloader.foundry_relative_folder(folder, tmp), "a/b")

    def test_folder_outside_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as other:
            with self.assertRaises(ValueError):
                downloader.foundry_relative_folder(other, tmp)


class BuildPlaylistTest(unittest.TestCase):
    def test_tracks_and_stable_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = os.path.join(tmp, "Data", "Music_Import", "apple")
            os.makedirs(folder)
            touch(folder, "B song.webm", "A song.webm", "skip.mp3", "notes.txt")

            first = downloader.build_playlist(folder, volume=0.3)
            second = downloader.build_playlist(folder, volume=0.3)

            self.assertEqual(first["name"], "apple")
            self.assertIsNone(first["folder"])
            self.assertEqual([s["name"] for s in first["sounds"]], ["A song", "B song"])
            self.assertEqual(first["sounds"][0]["path"], "Music_Import/apple/A%20song.webm")
            self.assertEqual(first["sounds"][0]["volume"], 0.3)
            ids = [s["_id"] for s in first["sounds"]]
            self.assertEqual(ids, [s["_id"] for s in second["sounds"]])
            self.assertTrue(all(len(i) == 16 for i in ids))
            self.assertEqual(len(set(ids)), 2)

    def test_mp3_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            touch(tmp, "x.webm", "y.MP3")
            playlist = downloader.build_playlist(tmp, audio_format="mp3", foundry_root=tmp)
            self.assertEqual([s["path"] for s in playlist["sounds"]], ["y.MP3"])


class DownloadedFilesTest(unittest.TestCase):
    def test_video_and_playlist(self):
        video = {"requested_downloads": [{"filepath": "a.mp3"}]}
        playlist = {"entries": [video, None, {"requested_downloads": [{"filepath": "b.mp3"}]}]}
        self.assertEqual(downloader.downloaded_files(video), ["a.mp3"])
        self.assertEqual(downloader.downloaded_files(playlist), ["a.mp3", "b.mp3"])
        self.assertEqual(downloader.downloaded_files(None), [])


if __name__ == "__main__":
    unittest.main()
