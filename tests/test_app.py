import unittest
from pathlib import Path
from unittest.mock import patch

from app import valid_video_url, make_download_command


class DownloaderTests(unittest.TestCase):
    def test_accept_youtube_links(self):
        for url in [
            "https://www.youtube.com/watch?v=abc123XYZ",
            "https://youtu.be/abc123XYZ",
            "https://youtube.com/shorts/abc123XYZ",
            "https://m.youtube.com/live/abc123XYZ",
        ]:
            with self.subTest(url=url):
                self.assertTrue(valid_video_url(url))

    def test_reject_bad_urls(self):
        for url in [
            "", "https://evil.com/watch?v=foo", "https://youtube.com.evil.com/watch?v=abc",
            "file:///tmp/video", "https://www.youtube.com/playlist?list=abc",
            "https://www.youtube.com/watch", "https://youtube.com/", "https://user@youtube.com/watch?v=abc",
        ]:
            with self.subTest(url=url):
                self.assertFalse(valid_video_url(url))

    def test_mp4_quality(self):
        with patch("app.yt_base_command", return_value=["yt-dlp.exe"]):
            cmd = make_download_command("https://youtu.be/abc", Path("C:/Videos"),
                                        "MP4 (wideo)", "720p (HD)")
        self.assertIn("--merge-output-format", cmd)
        self.assertIn("mp4", cmd)
        self.assertIn("height<=720", " ".join(cmd))
        self.assertEqual(cmd[-2], "--")

    def test_mp3_conversion(self):
        with patch("app.yt_base_command", return_value=["yt-dlp.exe"]), \
             patch("app.tool", return_value="C:/ffmpeg.exe"):
            cmd = make_download_command("https://youtu.be/abc", Path("C:/Videos"),
                                        "MP3 (audio)", "1080p (Full HD)")
        self.assertIn("--audio-format", cmd)
        self.assertIn("mp3", cmd)


if __name__ == "__main__":
    unittest.main()
