"""Regression tests for YTD 14.0.1 AUDIO FIX (no network required)."""
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from core import make_download_command, verify_video_contains_audio
from universal_downloader import UniversalSelection, build_command


class AudioFixTests(unittest.TestCase):
    def test_main_requires_ffmpeg_for_video(self):
        with self.assertRaises(FileNotFoundError):
            make_download_command(
                "https://youtu.be/example", Path("C:/Test"), "MP4 (wideo)",
                "Najlepsza dostępna", _tool=lambda _: None,
                _base_command=lambda: ["yt-dlp"],
            )

    def test_mp4_selects_video_plus_audio_not_video_only(self):
        for quality in ("Najlepsza dostępna", "1080p (Full HD)"):
            with self.subTest(quality=quality):
                cmd = make_download_command(
                    "https://youtu.be/example", Path("C:/Test"), "MP4 (wideo)",
                    quality, _tool=lambda _: "ffmpeg.exe",
                    _base_command=lambda: ["yt-dlp"],
                )
                fmt = cmd[cmd.index("-f") + 1]
                self.assertIn("+ba", fmt)
                self.assertNotIn("bv*", fmt)
                self.assertIn("--merge-output-format", cmd)

    def test_universal_requires_ffmpeg_for_video(self):
        selection = UniversalSelection(
            url="https://youtu.be/example", folder=Path("C:/Test"),
            container="MP4", quality="720p"
        )
        with self.assertRaises(FileNotFoundError):
            build_command(selection, premium=True, base=["yt-dlp"], ffmpeg="")

    @patch("core.tool", return_value="ffprobe.exe")
    @patch("subprocess.run")
    def test_verify_accepts_audio_video(self, run, _tool):
        run.return_value = SimpleNamespace(
            returncode=0, stdout=json.dumps({"streams": [
                {"codec_type": "video"}, {"codec_type": "audio"}
            ]}), stderr=""
        )
        verify_video_contains_audio("movie.mp4")

    @patch("core.tool", return_value="ffprobe.exe")
    @patch("subprocess.run")
    def test_verify_rejects_silent_video(self, run, _tool):
        run.return_value = SimpleNamespace(
            returncode=0, stdout=json.dumps({"streams": [
                {"codec_type": "video"}
            ]}), stderr=""
        )
        with self.assertRaisesRegex(RuntimeError, "ścieżki audio"):
            verify_video_contains_audio("silent.mp4")

    @patch("core.tool", return_value=None)
    def test_verify_requires_ffprobe(self, _tool):
        with self.assertRaises(FileNotFoundError):
            verify_video_contains_audio("movie.mp4")


if __name__ == "__main__":
    unittest.main()
