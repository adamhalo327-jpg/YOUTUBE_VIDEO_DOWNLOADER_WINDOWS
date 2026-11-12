"""Universal downloader 12.0: bounded URLs, safe argv, compatible with yt-dlp.
Only download media that you own or have permission to save. No DRM bypass.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
import ipaddress
import re

from core import yt_base_command, tool

# An explicit host allowlist avoids passing arbitrary private/internal endpoints to yt-dlp.
PLATFORMS = {
    "YouTube / Shorts": ("youtube.com", "youtu.be", "youtube-nocookie.com"),
    "TikTok": ("tiktok.com",),
    "Instagram / Reels": ("instagram.com",),
    "Facebook / Reels": ("facebook.com", "fb.watch"),
    "Twitch": ("twitch.tv", "clips.twitch.tv"),
    "Vimeo": ("vimeo.com",),
    "Dailymotion": ("dailymotion.com", "dai.ly"),
    "X / Twitter": ("x.com", "twitter.com"),
    "Reddit": ("reddit.com", "redd.it"),
    "SoundCloud": ("soundcloud.com",),
    "Bandcamp": ("bandcamp.com",),
    "Mixcloud": ("mixcloud.com",),
    "Internet Archive": ("archive.org",),
    "PeerTube": ("peertube.tv", "tilvids.com"),
    "Rumble": ("rumble.com",),
    "Kick": ("kick.com",),
    "Pinterest": ("pinterest.com", "pin.it"),
}
CONTAINERS = ("MP4", "MKV", "WEBM", "MP3", "M4A", "FLAC", "WAV", "OPUS")
QUALITIES = ("Najlepsza dostępna", "4320p (8K)", "2160p (4K)", "1440p (2K)", "1080p", "720p", "480p", "360p")
VIDEO = {"MP4", "MKV", "WEBM"}
AUDIO = set(CONTAINERS) - VIDEO

@dataclass(frozen=True)
class UniversalSelection:
    url: str
    folder: Path
    container: str = "MP4"
    quality: str = "1080p"
    playlist: bool = False
    subtitles: bool = False
    thumbnail: bool = False
    trim: str = ""


def platform_for(url: str) -> str:
    if not isinstance(url, str) or len(url) > 2048 or any(c.isspace() for c in url):
        raise ValueError("Nieprawidłowy adres URL.")
    try:
        u = urlsplit(url)
        host = (u.hostname or "").lower().rstrip(".")
        if u.scheme not in {"https", "http"} or not host or u.username or u.password or u.port not in (None, 80, 443):
            raise ValueError("Wymagany publiczny adres http/https bez loginu i niestandardowego portu.")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("Nie obsługujemy adresów IP.")
    except (TypeError, AttributeError, ValueError) as e:
        if isinstance(e, ValueError) and str(e) in ("Nie obsługujemy adresów IP.", "Wymagany publiczny adres http/https bez loginu i niestandardowego portu."):
            raise
        raise ValueError("Nieprawidłowy adres URL.") from e
    for name, domains in PLATFORMS.items():
        if any(host == domain or host.endswith("." + domain) for domain in domains):
            return name
    raise ValueError("Serwis nie jest na liście obsługiwanych platform.")


def requires_premium(s: UniversalSelection) -> bool:
    # A single MP4 up to 1080p or MP3 audio is available for free.
    return bool(s.playlist or s.subtitles or s.thumbnail or s.trim.strip() or
                s.container not in {"MP4", "MP3"} or
                (s.container == "MP4" and (s.quality == "Najlepsza dostępna" or
                 (re.match(r"^(\d+)p", s.quality) and int(re.match(r"^(\d+)p", s.quality).group(1)) > 1080))))


def validate(s: UniversalSelection, premium: bool) -> str:
    provider = platform_for(s.url)
    if s.container not in CONTAINERS or s.quality not in QUALITIES:
        raise ValueError("Nieznany format lub jakość.")
    if not isinstance(s.folder, Path):
        raise ValueError("Nieprawidłowy folder.")
    if not premium and requires_premium(s):
        raise PermissionError("Wybrany tryb Universal Downloader wymaga Premium.")
    if s.trim and not re.fullmatch(r"\d{2}:\d{2}:\d{2}-\d{2}:\d{2}:\d{2}", s.trim.strip()):
        raise ValueError("Zakres fragmentu: 00:00:10-00:00:30")
    return provider


def build_command(s: UniversalSelection, *, premium: bool, base=None, ffmpeg=None) -> list[str]:
    validate(s, premium)
    cmd = list(base if base is not None else yt_base_command())
    cmd += ["--yes-playlist" if s.playlist else "--no-playlist", "--newline", "--progress",
            "--progress-template", "download:PROGRESS:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
            "--print", "after_move:FILE:%(filepath)s", "--paths", str(s.folder),
            "-o", "%(title).180B [%(id)s].%(ext)s", "--continue", "--part", "--no-overwrites",
            "--retries", "5", "--fragment-retries", "5"]
    ff = ffmpeg if ffmpeg is not None else tool("ffmpeg.exe") or tool("ffmpeg")
    if s.container in AUDIO:
        if not ff: raise FileNotFoundError("Konwersja audio wymaga ffmpeg.exe.")
        cmd += ["-f", "bestaudio/best", "-x", "--audio-format", s.container.lower()]
    else:
        if not ff:
            raise FileNotFoundError("Pobieranie wideo z dźwiękiem wymaga ffmpeg.exe.")
        if s.quality == "Najlepsza dostępna":
            format_selector = "bv+ba/b"
        else:
            h = int(re.match(r"^(\d+)p", s.quality).group(1))
            format_selector = f"bv[height<={h}]+ba/b[height<={h}]/b[height<={h}]"
        cmd += ["-f", format_selector, "--merge-output-format", s.container.lower()]
        if s.container != "MKV":
            if not ff: raise FileNotFoundError("Konwersja wideo wymaga ffmpeg.exe.")
            cmd += ["--recode-video", s.container.lower()]
    if s.subtitles: cmd += ["--write-subs", "--sub-langs", "pl.*,en.*", "--convert-subs", "srt"]
    if s.thumbnail: cmd += ["--write-thumbnail"]
    if s.trim:
        if not ff: raise FileNotFoundError("Przycinanie wymaga ffmpeg.exe.")
        first, last = s.trim.split("-", 1)
        cmd += ["--download-sections", "*" + first + "-" + last, "--force-keyframes-at-cuts"]
    return cmd + ["--", s.url]


def preview_command(url: str) -> list[str]:
    platform_for(url)
    return yt_base_command() + ["--dump-single-json", "--no-playlist", "--skip-download", "--no-progress", "--", url]
