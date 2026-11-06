"""License code generator for OWNER, private key file MUST stay off GitHub.
Example: python tools/issue_premium_code.py --key ../YVD_3_0_WLASCICIEL_KLUCZ_PRYWATNY.pem --name Jan --days 365
"""
from __future__ import annotations
import argparse
import base64
import datetime as dt
import json
import secrets
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def issue(private_key: Ed25519PrivateKey, *, name: str = "USER", days: int = 365) -> str:
    if days < 0 or days > 36500:
        raise ValueError("days must be in 0..36500 (0 = perpetual)")
    if not 1 <= len(name) <= 80:
        raise ValueError("Name must be 1..80 chars")
    payload = {
        "product": "YVD3-PRO", "version": 1,
        "id": secrets.token_hex(12), "owner": name,
        "expires": (dt.date.today() + dt.timedelta(days=days)).isoformat() if days else None,
    }
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode()
    part = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")
    return "YVD3-" + part(raw) + "." + part(private_key.sign(raw))


def main():
    parser = argparse.ArgumentParser(description="Generate YVD 3.0 signed offline premium code")
    parser.add_argument("--key", type=Path, required=True, help="Path to owner's PRIVATE .pem key (keep secret)")
    parser.add_argument("--name", default="USER")
    parser.add_argument("--days", type=int, default=365, help="0 = no expiry")
    args = parser.parse_args()
    key = serialization.load_pem_private_key(args.key.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        parser.error("Unsupported private key")
    print(issue(key, name=args.name, days=args.days))


if __name__ == "__main__":
    main()
