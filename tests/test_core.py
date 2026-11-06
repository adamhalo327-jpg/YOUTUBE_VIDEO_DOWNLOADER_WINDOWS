import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import (
    History, SPEED_PROFILES, QUALITY_OPTIONS, is_playlist_url, make_download_command,
    metadata_command, parse_progress, parse_sha256_sums, parse_urls,
    safe_thumbnail_url, save_json, load_json, subtitle_langs,
    valid_video_url, valid_youtube_url, verify_sha256,
)


class UrlTests(unittest.TestCase):
    def test_video_links_v1(self):
        for link in (
            "https://www.youtube.com/watch?v=ABCdef1234",
            "https://youtu.be/ABCdef1234",
            "https://youtube.com/shorts/ABCdef1234",
            "https://m.youtube.com/live/ABCdef1234",
        ):
            with self.subTest(link=link):
                self.assertTrue(valid_video_url(link))

    def test_reject_tricky_domains(self):
        for link in (
            "", "https://youtube.com.attacker.test/watch?v=x",
            "https://notyoutube.com/watch?v=x", "file:///file",
            "https://user@youtube.com/watch?v=x", "https://youtube.com:9999/watch?v=x",
            "https://youtube.com/watch", "https://youtube.com/",
            "http://evil.com/playlist?list=a",
        ):
            with self.subTest(link=link):
                self.assertFalse(valid_youtube_url(link))

    def test_playlists(self):
        self.assertTrue(valid_youtube_url("https://www.youtube.com/playlist?list=PLabc"))
        self.assertTrue(is_playlist_url("https://www.youtube.com/watch?v=x&list=PLabc"))
        self.assertFalse(is_playlist_url("https://www.youtube.com/watch?v=x"))
        self.assertFalse(valid_video_url("https://www.youtube.com/playlist?list=PLabc"))

    def test_split_dedup(self):
        self.assertEqual(parse_urls("https://youtu.be/x\nhttps://youtu.be/y\nhttps://youtu.be/x\n"),
                         ["https://youtu.be/x", "https://youtu.be/y"])
        with self.assertRaises(ValueError):
            parse_urls("https://youtu.be/x\nhttps://evil.com/")


class CliTests(unittest.TestCase):
    def fake_tools(self, name):
        return {"yt-dlp.exe": "C:/yt-dlp.exe", "ffmpeg.exe": "C:/ffmpeg.exe", "deno.exe": "C:/deno.exe"}.get(name)

    def command(self, url="https://youtu.be/x", kind="MP4 (wideo)", quality="Najlepsza dostępna", **kwargs):
        with patch("core.tool", side_effect=self.fake_tools):
            return make_download_command(url, Path("C:/Movies"), kind, quality, **kwargs)

    def test_v1_best_mp4(self):
        cmd = self.command()
        self.assertIn("--merge-output-format", cmd)
        self.assertIn("--no-playlist", cmd)
        self.assertIn("--concurrent-fragments", cmd)
        self.assertEqual(cmd[-2], "--")
        self.assertEqual(cmd[-1], "https://youtu.be/x")

    def test_v1_quality_ceiling(self):
        cmd = self.command(quality="720p (HD)")
        self.assertIn("height<=720", " ".join(cmd))

    def test_mp3(self):
        cmd = self.command(kind="MP3 (audio)")
        self.assertIn("--audio-format", cmd)
        self.assertIn("mp3", cmd)

    def test_playlist(self):
        cmd = self.command("https://youtube.com/playlist?list=PLabc", playlist=True)
        self.assertIn("--yes-playlist", cmd)
        self.assertNotIn("--no-playlist", cmd)

    def test_playlist_disabled_for_single(self):
        with self.assertRaises(ValueError):
            self.command(playlist=True)

    def test_subtitles(self):
        cmd = self.command(subtitles=True, languages="pl,en")
        self.assertIn("--write-subs", cmd)
        self.assertIn("--write-auto-subs", cmd)
        self.assertIn("--convert-subs", cmd)
        self.assertIn("pl.*,en.*", cmd)

    def test_fast_fragments(self):
        cmd = self.command(fragments=SPEED_PROFILES["Turbo"])
        self.assertEqual(cmd[cmd.index("--concurrent-fragments") + 1], "12")
        with self.assertRaises(ValueError):
            self.command(fragments=99)

    def test_metadata_command(self):
        with patch("core.tool", side_effect=self.fake_tools):
            command = metadata_command("https://youtube.com/playlist?list=PLabc", True)
        self.assertIn("--flat-playlist", command)
        self.assertIn("--playlist-end", command)

    def test_missing_ffmpeg(self):
        with patch("core.tool", side_effect=lambda s: "C:/yt-dlp.exe" if s == "yt-dlp.exe" else None):
            with self.assertRaises(FileNotFoundError):
                make_download_command("https://youtu.be/x", Path("C:/"), "MP3 (audio)", QUALITY_OPTIONS[0])

    def test_sanitize_subtitles_language(self):
        self.assertEqual(subtitle_langs("pl,en"), "pl.*,en.*")
        with self.assertRaises(ValueError):
            subtitle_langs("pl;rm -rf /,en")

    def test_progress_and_files(self):
        result = parse_progress("PROGRESS: 44.7%|3.5MiB/s|00:34")
        self.assertEqual(result["type"], "progress")
        self.assertAlmostEqual(result["percent"], 44.7)
        self.assertEqual(parse_progress("FILE:C:\\Video.mp4")["path"], "C:\\Video.mp4")
        self.assertEqual(parse_progress("ITEM:2|12|Film 2")["index"], "2")
        self.assertIsNone(parse_progress("nothing"))


class PersistenceTests(unittest.TestCase):
    def test_history(self):
        with tempfile.TemporaryDirectory() as d:
            h = History(Path(d) / "history.json")
            self.assertEqual(h.all(), [])
            h.add({"title": "Film testowy", "path": "D:/movie.mp4"})
            self.assertEqual(h.all()[0]["title"], "Film testowy")
            h.clear()
            self.assertEqual(h.all(), [])

    def test_json_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / "settings.json"
            save_json(file, {"name": "Żółw i jeż", "n": 4})
            self.assertEqual(load_json(file, {})["name"], "Żółw i jeż")
            file.write_text("{BROKEN}", encoding="utf-8")
            self.assertEqual(load_json(file, {}), {})

    def test_checksum(self):
        import hashlib
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "file.exe"
            p.write_bytes(b"Hello")
            digest = hashlib.sha256(b"Hello").hexdigest()
            self.assertTrue(verify_sha256(p, digest))
            self.assertFalse(verify_sha256(p, "0" * 64))
            self.assertEqual(parse_sha256_sums(f"{digest} *yt-dlp.exe\n"), digest)
            self.assertIsNone(parse_sha256_sums("no checksum"))

    def test_safe_thumbnail(self):
        self.assertTrue(safe_thumbnail_url("https://i.ytimg.com/vi/x/hqdefault.jpg"))
        self.assertFalse(safe_thumbnail_url("http://i.ytimg.com/vi/x/hqdefault.jpg"))
        self.assertFalse(safe_thumbnail_url("https://i.ytimg.com.attacker.test/a.jpg"))
        self.assertFalse(safe_thumbnail_url("https://127.0.0.1/a.jpg"))


if __name__ == "__main__":
    unittest.main()
