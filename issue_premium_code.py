"""Generate digitally signed YVD3 codes with the OWNER's private PEM key.

Do NOT upload the private key to GitHub or include it in the customer EXE.

Examples:
  python tools/issue_premium_code.py --key C:/Private/owner.pem --name Jan --days 7
  python tools/issue_premium_code.py --key C:/Private/owner.pem --name Jan --days 0
  python tools/issue_premium_code.py --key C:/Private/owner.pem --name Jan --days 14 --hours 6
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import secrets
from pathlib import Path

from cryptography.hazmat.primitives import serialization
import hmac
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

UTC = dt.timezone.utc
PRESET_DAYS = (1, 7, 30, 90, 365)
EXPECTED_PUB_B64 = "EUj46Vi49pIWqVd6dkg4D9z3KG7eKi/+18bdrQCm0HA="


def issue(private_key: Ed25519PrivateKey, *, name: str = "USER", days: int = 365,
          hours: int = 0, minutes: int = 0, now: dt.datetime | None = None) -> str:
    """Produce a v2 signed code; validity starts at time of generation (UTC)."""
    for val, field_name in ((days, "dni"), (hours, "godziny"), (minutes, "minuty")):
        if isinstance(val, bool) or not isinstance(val, int) or val < 0:
            raise ValueError(f"Pole {field_name} musi być nieujemną liczbą całkowitą.")
    if not any((days, hours, minutes)):
        expire = None   # zero duration means perpetual; backward-compatible with --days 0
    else:
        try:
            delta = dt.timedelta(days=days, hours=hours, minutes=minutes)
        except OverflowError as exc:
            raise ValueError("Zbyt długi okres ważności.") from exc
    name = name.strip()
    if not 1 <= len(name) <= 80:
        raise ValueError("Nazwa odbiorcy musi mieć 1–80 znaków.")
    if now is None:
        now = dt.datetime.now(UTC)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Czas wystawienia musi zawierać strefę czasową.")
    now = now.astimezone(UTC).replace(microsecond=0)
    if any((days, hours, minutes)):
        try:
            expire = now + delta
        except OverflowError as exc:
            raise ValueError("Data wygaśnięcia jest poza zakresem kalendarza.") from exc
    iso = lambda d: d.isoformat(timespec="seconds").replace("+00:00", "Z")
    payload = {
        "product": "YVD3-PRO", "version": 2,
        "id": secrets.token_hex(12), "owner": name,
        "issued_at": iso(now), "expires_at": iso(expire) if expire else None,
    }
    data = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode("utf-8")
    encode = lambda raw: base64.urlsafe_b64encode(raw).decode().rstrip("=")
    return "YVD3-" + encode(data) + "." + encode(private_key.sign(data))


def load_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError("Nieobsługiwany format prywatnego klucza PEM.")
    public = key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    if not hmac.compare_digest(base64.b64encode(public).decode(), EXPECTED_PUB_B64):
        raise ValueError("Klucz PEM nie pasuje do YOUTUBE VIDEO DOWNLOADER 3.0/3.1. Użyj oryginalnego klucza właściciela.")
    return key


def main():
    parser = argparse.ArgumentParser(description="Generate offline Premium licenses")
    parser.add_argument("--key", type=Path, required=True, help="Owner's private PEM path")
    parser.add_argument("--name", default="USER")
    parser.add_argument("--days", type=int, default=365, help="Days; 0 = lifetime if hours/minutes are also 0")
    parser.add_argument("--hours", type=int, default=0)
    parser.add_argument("--minutes", type=int, default=0)
    args = parser.parse_args()
    print(issue(load_key(args.key), name=args.name, days=args.days,
                hours=args.hours, minutes=args.minutes))


if __name__ == "__main__":
    main()
