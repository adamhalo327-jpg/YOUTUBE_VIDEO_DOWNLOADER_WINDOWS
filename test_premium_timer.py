"""Tests for v3.1 accurate countdown and owner generator compatibility."""
import base64
import datetime as dt
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from licensing import LicenseManager, format_remaining, remaining_seconds, validate_license
from tools.issue_premium_code import PRESET_DAYS, issue, load_key

UTC = dt.timezone.utc


class PremiumTimerTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.pub = base64.b64encode(self.key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw)).decode()
        self.start = dt.datetime(2026, 11, 6, 12, 0, 0, tzinfo=UTC)

    def test_every_preset_expires_at_exact_utc_instant(self):
        self.assertEqual(PRESET_DAYS, (1, 7, 30, 90, 365))
        for days in PRESET_DAYS:
            with self.subTest(days=days), patch("licensing.PUBLIC_KEY_B64", self.pub):
                code = issue(self.key, days=days, now=self.start, name="Klient")
                deadline = self.start + dt.timedelta(days=days)
                data = validate_license(code, now=deadline - dt.timedelta(seconds=1))
                self.assertEqual(data["version"], 2)
                self.assertEqual(remaining_seconds(data, now=self.start), days * 86400)
                self.assertEqual(remaining_seconds(data, now=deadline), 0)
                with self.assertRaisesRegex(ValueError, "wygasła"):
                    validate_license(code, now=deadline)

    def test_custom_duration_of_days_hours_and_minutes(self):
        with patch("licensing.PUBLIC_KEY_B64", self.pub):
            payload = validate_license(issue(self.key, days=517, hours=6, minutes=42,
                                             now=self.start), now=self.start)
            self.assertEqual(remaining_seconds(payload, now=self.start),
                             517 * 86400 + 6 * 3600 + 42 * 60)
            self.assertIn("517 dni", format_remaining(remaining_seconds(payload, now=self.start)))

    def test_lifetime(self):
        with patch("licensing.PUBLIC_KEY_B64", self.pub):
            code = issue(self.key, days=0, now=self.start)
            payload = validate_license(code, now=self.start + dt.timedelta(days=50000))
            self.assertIsNone(remaining_seconds(payload))
            self.assertIn("BEZTERMINOWO", format_remaining(None))

    def test_very_short_validity(self):
        with patch("licensing.PUBLIC_KEY_B64", self.pub):
            code = issue(self.key, days=0, minutes=2, now=self.start)
            payload = validate_license(code, now=self.start)
            self.assertEqual(remaining_seconds(payload, now=self.start + dt.timedelta(seconds=117)), 3)
            self.assertEqual(format_remaining(3), "3 sek.")

    def test_expired_status_remains_visible_on_disk(self):
        with patch("licensing.PUBLIC_KEY_B64", self.pub), tempfile.TemporaryDirectory() as root:
            manager = LicenseManager(Path(root) / "premium-license.json")
            code = issue(self.key, days=7, now=dt.datetime.now(UTC))
            manager.activate(code)
            d = manager.status(now=dt.datetime.now(UTC))
            self.assertEqual(d["state"], "active")
            deadline = dt.datetime.fromisoformat(d["payload"]["expires_at"].replace("Z", "+00:00"))
            self.assertEqual(manager.status(now=deadline)["state"], "expired")
            self.assertEqual(manager.status(now=deadline)["remaining"], 0)
            manager.deactivate()
            self.assertEqual(manager.status()["state"], "free")

    def test_forged_code_cannot_extend_expiry(self):
        with patch("licensing.PUBLIC_KEY_B64", self.pub):
            code = issue(self.key, days=1, now=self.start)
            payload, sig = code.split(".")
            import json
            data = json.loads(base64.urlsafe_b64decode(payload[5:] + "=="))
            data["expires_at"] = "2099-01-01T00:00:00Z"
            raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
            bad = "YVD3-" + base64.urlsafe_b64encode(raw).decode().rstrip("=") + "." + sig
            with self.assertRaises(ValueError):
                validate_license(bad, now=self.start)

    def test_generator_rejects_invalid_custom_values(self):
        for kwargs in ({"days": -1}, {"hours": -2}, {"minutes": -1},
                       {"days": 1.5}, {"days": 1, "hours": True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                issue(self.key, now=self.start, **kwargs)

    def test_key_picker_rejects_other_owner_keys(self):
        pem = self.key.private_bytes(serialization.Encoding.PEM,
                                     serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption())
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "wrong-owner.pem"
            file.write_bytes(pem)
            with self.assertRaisesRegex(ValueError, "nie pasuje"):
                load_key(file)

    def test_clock_format(self):
        self.assertEqual(format_remaining(3661), "1 godz.  01 min  01 sek.")
        self.assertEqual(format_remaining(59), "59 sek.")
        self.assertIn("0 sek.", format_remaining(0))


if __name__ == "__main__":
    unittest.main()
