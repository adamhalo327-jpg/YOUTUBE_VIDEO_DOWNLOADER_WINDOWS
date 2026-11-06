"""Local and privacy-preserving download history metrics."""
from __future__ import annotations
from pathlib import Path

def summarize(entries, file_size=None):
    file_size = file_size or _disk_bytes
    unique_paths, bytes_total, missing = set(), 0, 0
    formats = {}
    for row in entries:
        if not isinstance(row, dict):
            continue
        kind = str(row.get('kind') or 'Inny')
        formats[kind] = formats.get(kind, 0) + 1
        path = str(row.get('path') or '')
        if path and path not in unique_paths:
            unique_paths.add(path)
            amount = file_size(path)
            if amount is None:
                missing += 1
            else:
                bytes_total += amount
    return {"count": len(entries), "bytes": bytes_total, "missing": missing, "formats": formats}

def _disk_bytes(path):
    try:
        p = Path(path)
        return p.stat().st_size if p.is_file() else None
    except (OSError, ValueError):
        return None

def readable_bytes(value):
    n = float(max(0, value))
    for unit in ('B', 'KB', 'MB', 'GB', 'TB'):
        if n < 1024 or unit == 'TB':
            return f'{n:.1f} {unit}'
        n /= 1024
