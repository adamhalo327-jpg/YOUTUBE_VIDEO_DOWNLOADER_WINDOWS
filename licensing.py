"""Digitally signed offline licenses with accurate UTC expiry and legacy support.

The app ships ONLY with its public Ed25519 key. License validity is measured
from the date/time of issuance, not first activation (which cannot be securely
established in an offline app). Validation uses the local computer clock.
"""
from __future__ import annotations

import base64
import binascii
import datetime as dt
import json
import math
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from core import load_json, save_json, user_data_dir

# Keep the same public key as YVD 3.0; previously issued signed codes still work.
PUBLIC_KEY_B64 = "EUj46Vi49pIWqVd6dkg4D9z3KG7eKi/+18bdrQCm0HA="
PRODUCT = "YVD3-PRO"
PREFIX = "YVD3-"
UTC = dt.timezone.utc


def b64decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _now_utc(now: dt.datetime | None = None) -> dt.datetime:
    if now is None:
        return dt.datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Czas musi zawierać strefę czasową.")
    return now.astimezone(UTC)


def parse_timestamp(value: str) -> dt.datetime:
    """Parse a timezone-aware ISO-8601 time from a signed license."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Kod ma niepoprawną datę i godzinę ważności.")
    try:
        result = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Kod ma niepoprawną datę i godzinę ważności.") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("Kod nie zawiera strefy czasowej ważności.")
    return result.astimezone(UTC)


def expiry_time(payload: dict) -> dt.datetime | None:
    """Return exclusive expiry timestamp (premium is invalid at this time)."""
    version = payload.get("version")
    if version == 2:
        expiration = payload.get("expires_at")
        if expiration is None:
            return None
        return parse_timestamp(expiration)
    if version == 1:
        expiration = payload.get("expires")
        if expiration is None:
            return None
        try:
            date = dt.date.fromisoformat(expiration)
            # v3.0 date-only codes were valid through the entire expiry date.
            return dt.datetime.combine(date + dt.timedelta(days=1), dt.time(), tzinfo=UTC)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError("Niepoprawna data wygaśnięcia licencji.") from exc
    raise ValueError("Nieobsługiwana wersja kodu Premium.")


def _verify_signed_payload(code: str) -> dict:
    if not isinstance(code, str):
        raise ValueError("Wklej kod aktywacyjny Premium.")
    normalized = "".join(code.split())
    if not normalized.startswith(PREFIX):
        raise ValueError("Kod Premium musi zaczynać się od YVD3-.")
    rest = normalized[len(PREFIX):]
    parts = rest.split(".")
    if len(parts) != 2 or len(rest) > 2048:
        raise ValueError("Błędny format kodu aktywacyjnego.")
    try:
        payload_bytes, signature = b64decode(parts[0]), b64decode(parts[1])
        Ed25519PublicKey.from_public_bytes(base64.b64decode(PUBLIC_KEY_B64)).verify(signature, payload_bytes)
        payload = json.loads(payload_bytes)
    except (ValueError, InvalidSignature, TypeError, UnicodeDecodeError, KeyError, binascii.Error) as exc:
        raise ValueError("Kod nie został podpisany przez wydawcę programu.") from exc
    if not isinstance(payload, dict) or payload.get("product") != PRODUCT or payload.get("version") not in (1, 2):
        raise ValueError("Kod dotyczy innego produktu lub nieobsługiwanej wersji.")
    if not isinstance(payload.get("id"), str) or not 8 <= len(payload["id"]) <= 64:
        raise ValueError("Kod ma niepoprawny identyfikator.")
    expiry = expiry_time(payload)
    if payload["version"] == 2:
        issued = parse_timestamp(payload.get("issued_at"))
        if expiry is not None and expiry <= issued:
            raise ValueError("Data wygaśnięcia nie może poprzedzać wystawienia kodu.")
    return payload


def remaining_seconds(payload: dict, *, now: dt.datetime | None = None) -> int | None:
    expiry = expiry_time(payload)
    if expiry is None:
        return None
    return max(0, math.ceil((expiry - _now_utc(now)).total_seconds()))


def format_remaining(seconds: int | None) -> str:
    if seconds is None:
        return "BEZTERMINOWO — na zawsze"
    if seconds <= 0:
        return "0 sek. — kod wygasł"
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, sec = divmod(remainder, 60)
    if days:
        return f"{days} dni  {hours:02d} godz.  {minutes:02d} min  {sec:02d} sek."
    if hours:
        return f"{hours} godz.  {minutes:02d} min  {sec:02d} sek."
    if minutes:
        return f"{minutes} min  {sec:02d} sek."
    return f"{sec} sek."


def validate_license(code: str, *, today: dt.date | None = None, now: dt.datetime | None = None) -> dict:
    """Verify signed product and expiration. today remains for v3.0 test compatibility."""
    payload = _verify_signed_payload(code)
    expiry = expiry_time(payload)
    if expiry is not None:
        if payload["version"] == 1 and today is not None and now is None:
            invalid = today > dt.date.fromisoformat(payload["expires"])
        else:
            invalid = _now_utc(now) >= expiry
        if invalid:
            raise ValueError(f"Licencja wygasła {expiry.isoformat()}.")
    return payload


class LicenseManager:
    def __init__(self, path: Path | None = None):
        self.path = path or user_data_dir() / "premium-license.json"

    def status(self, *, now: dt.datetime | None = None) -> dict:
        """state: free / active / expired / invalid; includes remaining and payload."""
        stored = load_json(self.path, {})
        if not isinstance(stored, dict) or not isinstance(stored.get("code"), str):
            return {"state": "free", "payload": None, "remaining": None, "expires_at": None}
        try:
            payload = _verify_signed_payload(stored["code"])
            expiry = expiry_time(payload)
            remain = remaining_seconds(payload, now=now)
        except (ValueError, TypeError):
            return {"state": "invalid", "payload": None, "remaining": None, "expires_at": None}
        return {"state": "expired" if remain == 0 else "active",
                "payload": payload, "remaining": remain, "expires_at": expiry}

    def info(self) -> dict | None:
        result = self.status()
        return result["payload"] if result["state"] == "active" else None

    def premium(self) -> bool:
        return self.status()["state"] == "active"

    def activate(self, code: str) -> dict:
        payload = validate_license(code)
        save_json(self.path, {"code": "".join(code.split())})
        return payload

    def deactivate(self):
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
