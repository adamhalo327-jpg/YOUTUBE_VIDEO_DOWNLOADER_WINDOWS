"""Safely check official GitHub Releases. Never auto-execute remote binaries."""
from __future__ import annotations
import json
import re
from urllib.request import Request, urlopen
from urllib.parse import urlparse

RELEASES_API = "https://api.github.com/repos/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS/releases/latest"
RELEASES_WEB = "https://github.com/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS/releases/latest"
CURRENT_VERSION = "12.0"

def version_tuple(version):
    match = re.search(r"(?:^|[^0-9])(\d{1,3})\.(\d{1,3})(?:\.(\d{1,3}))?(?:$|[^0-9])", str(version))
    if not match:
        raise ValueError("Nieznana wersja")
    return tuple(int(x or 0) for x in match.groups())

def newer(tag, current=CURRENT_VERSION):
    try:
        return version_tuple(tag) > version_tuple(current)
    except ValueError:
        return False

def check_release(opener=urlopen):
    req = Request(RELEASES_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "YVD-Windows-12.0"})
    with opener(req, timeout=12) as resp:
        if getattr(resp, 'url', RELEASES_API) and urlparse(getattr(resp, 'url', RELEASES_API)).hostname != 'api.github.com':
            raise ValueError("Niedozwolone przekierowanie")
        payload = resp.read(256_001)
    if len(payload) > 256_000:
        raise ValueError("Odpowiedź serwera jest za duża")
    data = json.loads(payload)
    tag = str(data.get('tag_name', ''))
    url = str(data.get('html_url', ''))
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'github.com' or not parsed.path.startswith('/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS/releases/'):
        raise ValueError("Niezweryfikowany adres wydania")
    return {"tag": tag, "url": url, "newer": newer(tag)}
