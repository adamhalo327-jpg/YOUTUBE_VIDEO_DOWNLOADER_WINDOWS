"""Local-only registry of premium codes issued on THIS computer.
Never persists plaintext activation codes or private keys.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

def registry_path():
    base = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))
    return base / 'YouTubeVideoDownloaderOwner' / 'issued_codes.json'

def read_registry(path=None):
    p = Path(path) if path else registry_path()
    if not p.exists():
        return []
    data = json.loads(p.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError('Niepoprawny rejestr licencji')
    return data

def record_issue(code, name, expiry, path=None):
    p = Path(path) if path else registry_path()
    items = read_registry(p)
    item = {'fingerprint': hashlib.sha256(code.encode()).hexdigest()[:18],
            'name': name[:80], 'issued_at': datetime.now(timezone.utc).isoformat(),
            'expires_at': expiry or 'bezterminowo', 'note': ''}
    items.insert(0, item)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replace to avoid damaging existing issuance records.
    fd, tmp = tempfile.mkstemp(dir=p.parent, prefix='registry-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(items, stream, indent=2, ensure_ascii=False)
        os.replace(tmp, p)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    return item

def export_csv(destination, path=None):
    entries = read_registry(path)
    with open(destination, 'w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=['fingerprint','name','issued_at','expires_at','note'], extrasaction='ignore')
        writer.writeheader()
        writer.writerows(entries)
    return len(entries)
