"""Signed offline PREMIUM codes. No secret/private key is shipped in application."""
from __future__ import annotations
import base64
import binascii
import datetime as dt
import json
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature
from core import load_json, save_json, user_data_dir

PUBLIC_KEY_B64 = "EUj46Vi49pIWqVd6dkg4D9z3KG7eKi/+18bdrQCm0HA="
PRODUCT = "YVD3-PRO"
PREFIX = "YVD3-"


def b64decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def validate_license(code: str, *, today: dt.date | None = None) -> dict:
    """Verify the signed payload, product and expiry. Raises ValueError on invalid code."""
    normalized = "".join(code.split())
    if not normalized.startswith(PREFIX):
        raise ValueError("Kod Premium musi zaczynać się od YVD3-.")
    rest = normalized[len(PREFIX):]
    parts = rest.split(".")
    if len(parts) != 2 or len(rest) > 2048:
        raise ValueError("Błędny format kodu aktywacyjnego.")
    try:
        payload_bytes = b64decode(parts[0]); sig = b64decode(parts[1])
        Ed25519PublicKey.from_public_bytes(base64.b64decode(PUBLIC_KEY_B64)).verify(sig, payload_bytes)
        payload = json.loads(payload_bytes)
    except (ValueError, InvalidSignature, TypeError, UnicodeDecodeError, KeyError, binascii.Error) as exc:
        raise ValueError("Kod nie został podpisany przez wydawcę programu.") from exc
    if not isinstance(payload, dict) or payload.get("product") != PRODUCT or payload.get("version") != 1:
        raise ValueError("Kod dotyczy innego produktu.")
    if not isinstance(payload.get("id"), str) or not (8 <= len(payload["id"]) <= 64):
        raise ValueError("Kod ma niepoprawny identyfikator.")
    if payload.get("expires"):
        try:
            expiry = dt.date.fromisoformat(payload["expires"])
        except (ValueError, TypeError) as exc:
            raise ValueError("Niepoprawna data wygaśnięcia.") from exc
        if (today or dt.date.today()) > expiry:
            raise ValueError(f"Licencja wygasła {expiry.isoformat()}.")
    return payload


class LicenseManager:
    def __init__(self, path: Path | None = None):
        self.path = path or user_data_dir() / "premium-license.json"

    def info(self) -> dict | None:
        data = load_json(self.path, {})
        if isinstance(data, dict) and isinstance(data.get("code"), str):
            try:
                return validate_license(data["code"])
            except ValueError:
                pass
        return None

    def premium(self) -> bool:
        return self.info() is not None

    def activate(self, code: str) -> dict:
        payload = validate_license(code)
        save_json(self.path, {"code": "".join(code.split())})
        return payload

    def deactivate(self):
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass
