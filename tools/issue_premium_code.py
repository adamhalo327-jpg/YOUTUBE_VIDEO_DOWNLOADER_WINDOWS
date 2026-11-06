
import base64
import datetime as dt
import hmac
import json
import secrets
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

PRESET_DAYS = (1, 7, 30, 90, 365)

PUBLIC = 'EUj46Vi49pIWqVd6dkg4D9z3KG7eKi/+18bdrQCm0HA='

def load_key(path):
    key = serialization.load_pem_private_key(
        Path(path).read_bytes(), password=None
    )
    if not isinstance(key, Ed25519PrivateKey):
        raise ValueError('Wymagany klucz Ed25519 PEM.')
    raw = key.public_key().public_bytes(
        serialization.Encoding.Raw,
        serialization.PublicFormat.Raw
    )
    if not hmac.compare_digest(base64.b64encode(raw).decode(), PUBLIC):
        raise ValueError('Klucz PEM nie pasuje do aplikacji 3.1.')
    return key

def issue(key, name='Klient', days=30, hours=0, minutes=0):
    if not name.strip() or len(name) > 80:
        raise ValueError('Podaj poprawną nazwę odbiorcy.')
    if any(not isinstance(x, int) or x < 0
           for x in (days, hours, minutes)):
        raise ValueError('Niepoprawny czas ważności.')
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    try:
        until = now + dt.timedelta(
            days=days, hours=hours, minutes=minutes
        ) if any((days, hours, minutes)) else None
    except OverflowError as exc:
        raise ValueError('Zbyt długi czas ważności.') from exc
    fmt = lambda t: t.isoformat(timespec='seconds').replace(
        '+00:00', 'Z'
    ) if t else None
    data = {
        'product': 'YVD3-PRO',
        'version': 2,
        'id': secrets.token_hex(12),
        'owner': name.strip(),
        'issued_at': fmt(now),
        'expires_at': fmt(until)
    }
    raw = json.dumps(
        data, separators=(',', ':'), sort_keys=True,
        ensure_ascii=False
    ).encode()
    enc = lambda b: base64.urlsafe_b64encode(b).decode().rstrip('=')
    return 'YVD3-' + enc(raw) + '.' + enc(key.sign(raw))
