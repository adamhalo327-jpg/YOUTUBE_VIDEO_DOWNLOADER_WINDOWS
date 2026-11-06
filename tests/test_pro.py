import base64
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from licensing import LicenseManager, validate_license
from core import make_download_command, normalize_trim_range, seconds_from_clock, SPEED_PROFILES


class LicenseTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()

    def code(self, *, expiry=None):
        payload = {"id":"ABCDEF123456", "product":"YVD3-PRO", "version":1,
                   "owner":"Licencja testowa", "expires":expiry}
        data = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        b64 = lambda x: base64.urlsafe_b64encode(x).decode().rstrip("=")
        return "YVD3-" + b64(data) + "." + b64(self.key.sign(data))

    def test_signed_code_activates_and_persists(self):
        with patch("licensing.PUBLIC_KEY_B64", self.pub), tempfile.TemporaryDirectory() as d:
            manager = LicenseManager(Path(d)/"license.json")
            self.assertFalse(manager.premium())
            info = manager.activate(self.code())
            self.assertEqual(info["product"], "YVD3-PRO")
            self.assertTrue(LicenseManager(Path(d)/"license.json").premium())
            manager.deactivate()
            self.assertFalse(manager.premium())

    def test_changed_signature_does_not_activate(self):
        with patch("licensing.PUBLIC_KEY_B64", self.pub):
            c = self.code()
            parts = c.split(".")
            tampered = parts[0] + "." + ("A" if parts[1][0] != "A" else "B") + parts[1][1:]
            with self.assertRaises(ValueError):
                validate_license(tampered)

    def test_expired_and_perpetual(self):
        with patch("licensing.PUBLIC_KEY_B64", self.pub):
            with self.assertRaises(ValueError):
                validate_license(self.code(expiry="2020-01-01"))
            self.assertTrue(validate_license(self.code(), today=dt.date(2030,1,1)))

    def test_garbage_is_handled(self):
        for text in ("", "foobar", "YVD3-&&&&.%%%%", "YVD3-abcd.A" ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate_license(text)


class ProFormatTests(unittest.TestCase):
    def fake_tool(self, name):
        return {"yt-dlp.exe": "C:/yd.exe", "ffmpeg.exe": "C:/ffmpeg.exe"}.get(name)

    def command(self, kind, **options):
        with patch("core.tool", side_effect=self.fake_tool):
            return make_download_command("https://youtu.be/test", Path("C:/Movies"),
                                         kind, "1080p (Full HD)", **options)

    def test_all_video_formats(self):
        for kind, extension in (("MP4 (wideo)", "mp4"), ("MKV (wideo)", "mkv"), ("WEBM (wideo)", "webm")):
            with self.subTest(kind=kind):
                cmd = self.command(kind)
                self.assertIn("--recode-video", cmd)
                self.assertEqual(cmd[cmd.index("--recode-video")+1], extension)
                self.assertIn("height<=1080", " ".join(cmd))

    def test_audio_formats(self):
        for kind, ext in (("MP3 (audio)", "mp3"), ("WAV (audio)", "wav")):
            with self.subTest(kind=kind):
                cmd = self.command(kind)
                self.assertIn("--audio-format", cmd)
                self.assertEqual(cmd[cmd.index("--audio-format")+1], ext)

    def test_turbo_pro_flags(self):
        cmd = self.command("MP4 (wideo)", fragments=SPEED_PROFILES["Turbo Pro 24"])
        self.assertEqual(cmd[cmd.index("--concurrent-fragments")+1], "24")
        self.assertIn("--buffer-size", cmd)
        self.assertIn("--part", cmd)
        self.assertIn("--continue", cmd)

    def test_trim(self):
        cmd = self.command("MP4 (wideo)", trim_start="1:20", trim_end="2:10")
        self.assertEqual(cmd[cmd.index("--download-sections")+1], "*80-130")
        self.assertIn("--force-keyframes-at-cuts", cmd)
        self.assertEqual(normalize_trim_range("", "01:00"), "*0-60")
        self.assertEqual(seconds_from_clock("01:01:02"), 3662)
        with self.assertRaises(ValueError):
            normalize_trim_range("02:10", "01:00")
        with self.assertRaises(ValueError):
            seconds_from_clock("xx:22")


if __name__ == "__main__":
    unittest.main()
