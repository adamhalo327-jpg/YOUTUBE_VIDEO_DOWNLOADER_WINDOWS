"""Independent, testable core of YOUTUBE VIDEO DOWNLOADER 3.0.

Downloads should only be used for videos you own or are authorized to save.
The CLI engine is distributed as a separate executable.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

APP_TITLE = "YOUTUBE VIDEO DOWNLOADER"
APP_VERSION = "4.1 — ULTIMATE EDITION"
VALID_HOSTS = frozenset({
    "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com",
    "youtu.be", "www.youtu.be", "youtube-nocookie.com", "www.youtube-nocookie.com",
})
QUALITY_OPTIONS = (
    "Najlepsza dostępna", "2160p (4K)", "1440p (2K)",
    "1080p (Full HD)", "720p (HD)", "480p", "360p",
)
KINDS = ("MP4 (wideo)", "MP3 (audio)", "MKV (wideo)", "WEBM (wideo)", "WAV (audio)")
SPEED_PROFILES = {"Standard": 4, "Szybki": 8, "Turbo": 12, "Turbo Pro 16": 16, "Turbo Pro 24": 24}
PREMIUM_SPEEDS = frozenset({"Turbo Pro 16", "Turbo Pro 24"})
PREMIUM_KINDS = frozenset({"MKV (wideo)", "WEBM (wideo)", "WAV (audio)"})
MAX_HISTORY = 3000
API_URL = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
USER_AGENT = "YouTubeVideoDownloader/2.0 (+https://github.com/yt-dlp/yt-dlp)"


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def user_data_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    return (Path(base) / "YouTubeVideoDownloader" if base else Path.home() / ".youtube_video_downloader")


def tool(name: str) -> str | None:
    """Prefer verified, user-updated yt-dlp and bundled v1-style executables."""
    if name.lower() in {"yt-dlp.exe", "yt-dlp"}:
        updated = user_data_dir() / "engine" / "yt-dlp.exe"
        if updated.is_file():
            return str(updated)
    bundled = app_root() / name
    if bundled.is_file():
        return str(bundled)
    return shutil.which(name)


def _valid_base_url(raw: str):
    try:
        parsed = urlparse(raw.strip())
        if parsed.scheme not in {"http", "https"} or parsed.hostname not in VALID_HOSTS:
            return None
        if parsed.username or parsed.password or parsed.port not in (None, 80, 443):
            return None
        return parsed
    except (ValueError, AttributeError):
        return None


def valid_video_url(value: str) -> bool:
    """Keeps the 1.0 public function working for video, live and Shorts links."""
    parsed = _valid_base_url(value)
    if not parsed:
        return False
    parts = [p for p in parsed.path.split("/") if p]
    host = parsed.hostname or ""
    if host.endswith("youtu.be"):
        return bool(parts and parts[0])
    if not parts:
        return False
    if parts[0] == "watch":
        return bool(parse_qs(parsed.query).get("v", [""])[0])
    return parts[0] in {"shorts", "live", "embed", "v"} and len(parts) >= 2


def is_playlist_url(value: str) -> bool:
    parsed = _valid_base_url(value)
    if not parsed:
        return False
    playlist_id = parse_qs(parsed.query).get("list", [""])[0]
    path = parsed.path.rstrip("/")
    return bool(playlist_id and (path == "/playlist" or valid_video_url(value)))


def valid_youtube_url(value: str) -> bool:
    return valid_video_url(value) or is_playlist_url(value)


def parse_urls(value: str) -> list[str]:
    """One URL per line; deduplicate without reordering."""
    found, seen = [], set()
    for line in value.splitlines():
        url = line.strip()
        if not url:
            continue
        if not valid_youtube_url(url):
            raise ValueError(f"Nieprawidłowy adres YouTube: {url[:100]}")
        if url not in seen:
            found.append(url)
            seen.add(url)
    if not found:
        raise ValueError("Wklej przynajmniej jeden link YouTube.")
    return found


def yt_base_command() -> list[str]:
    executable = tool("yt-dlp.exe") or tool("yt-dlp")
    if not executable:
        raise FileNotFoundError("Brak yt-dlp.exe. Rozpakuj cały artefakt z GitHub Actions.")
    cmd = [executable, "--ignore-config", "--no-warnings", "--windows-filenames", "--encoding", "utf-8"]
    ffmpeg = tool("ffmpeg.exe") or tool("ffmpeg")
    if ffmpeg:
        cmd += ["--ffmpeg-location", str(Path(ffmpeg).parent)]
    deno = tool("deno.exe") or tool("deno")
    if deno:
        cmd += ["--js-runtimes", "deno:" + deno]
    return cmd


def subtitle_langs(languages: str) -> str:
    tokens = []
    for item in languages.split(","):
        v = item.strip().lower()
        if v and not re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})?", v):
            raise ValueError("Języki napisów podaj np. pl,en lub en,es.")
        if v:
            tokens.append(re.escape(v) + ".*")
    if not tokens:
        raise ValueError("Wpisz języki napisów, np. pl,en.")
    return ",".join(tokens)


def seconds_from_clock(raw: str) -> int | None:
    """Accept empty, HH:MM:SS, MM:SS and plain seconds."""
    raw = raw.strip()
    if not raw:
        return None
    if raw.isdecimal():
        return int(raw)
    pieces = raw.split(":")
    if len(pieces) not in (2, 3) or not all(x.isdecimal() for x in pieces):
        raise ValueError("Czas podaj jako MM:SS lub HH:MM:SS, np. 01:30.")
    if any(int(x) > 59 for x in pieces[1:]):
        raise ValueError("Minuty i sekundy muszą być mniejsze niż 60.")
    secs = 0
    for x in pieces:
        secs = secs * 60 + int(x)
    return secs


def normalize_trim_range(start: str, end: str) -> str:
    a, b = seconds_from_clock(start), seconds_from_clock(end)
    if a is None and b is None:
        raise ValueError("Wpisz początek lub koniec wycinka.")
    if b is not None and b <= (a or 0):
        raise ValueError("Koniec wycinka musi być późniejszy niż początek.")
    def stamp(seconds):
        return str(seconds) if seconds is not None else "inf"
    return f"*{stamp(a or 0)}-{stamp(b)}"



def make_download_command(
    url: str,
    dest: Path,
    kind: str,
    quality: str,
    *,
    playlist: bool = False,
    subtitles: bool = False,
    languages: str = "pl,en",
    fragments: int = 8,
    trim_start: str = "",
    trim_end: str = "",
    _tool=None,
    _base_command=None,
) -> list[str]:
    """Shell-free command, retaining 1.0's 4 positional arguments."""
    if not valid_youtube_url(url):
        raise ValueError("Wklej prawidłowy link do filmu lub playlisty YouTube.")
    if playlist and not is_playlist_url(url):
        raise ValueError("Pobieranie playlisty wymaga linku z parametrem list=.")
    if kind not in KINDS or quality not in QUALITY_OPTIONS:
        raise ValueError("Nieobsługiwany format lub jakość.")
    if not isinstance(fragments, int) or fragments < 1 or fragments > 24:
        raise ValueError("Liczba równoległych fragmentów musi być w zakresie 1–24.")
    get_tool = _tool or tool
    ffmpeg = get_tool("ffmpeg.exe") or get_tool("ffmpeg")
    if kind != "MP4 (wideo)" and not ffmpeg:
        raise FileNotFoundError("MP3 wymaga ffmpeg.exe — pobierz pełną paczkę EXE.")
    if subtitles and not ffmpeg:
        raise FileNotFoundError("Konwersja napisów do SRT wymaga ffmpeg.exe.")
    cmd = (_base_command or yt_base_command)()
    cmd += [
        "--yes-playlist" if playlist else "--no-playlist",
        "--newline", "--progress",
        "--progress-template", "download:PROGRESS:%(progress._percent_str)s|%(progress._speed_str)s|%(progress._eta_str)s",
        "--print", "before_dl:ITEM:%(playlist_index)s|%(playlist_count)s|%(title)s",
        "--print", "after_move:FILE:%(filepath)s",
        "--paths", str(dest),
        "-o", "%(title).180B [%(id)s].%(ext)s",
        "--no-overwrites", "--continue", "--part", "--retries", "10", "--fragment-retries", "10",
        "--concurrent-fragments", str(fragments),
    ]
    if trim_start or trim_end:
        if not ffmpeg:
            raise FileNotFoundError("Przycinanie wymaga ffmpeg.exe.")
        cmd += ["--download-sections", normalize_trim_range(trim_start, trim_end), "--force-keyframes-at-cuts"]
    if fragments >= 16:
        cmd += ["--buffer-size", "64K", "--retry-sleep", "fragment:exp=1:15"]
    if kind in {"MP3 (audio)", "WAV (audio)"}:
        codec = "mp3" if kind == "MP3 (audio)" else "wav"
        cmd += ["-f", "bestaudio/best", "--extract-audio", "--audio-format", codec]
        if codec == "mp3":
            cmd += ["--audio-quality", "0"]
    else:
        if quality == "Najlepsza dostępna":
            fmt = "bv*[ext=mp4]+ba[ext=m4a]/bv*+ba/b[ext=mp4]/b"
        else:
            height = int(re.search(r"\d+", quality).group())
            fmt = (f"bv*[height<={height}][ext=mp4]+ba[ext=m4a]/"
                   f"bv*[height<={height}]+ba/b[height<={height}]")
        if kind == "MP4 (wideo)":
            cmd += ["-f", fmt, "--merge-output-format", "mp4"]
            if ffmpeg:
                cmd += ["--recode-video", "mp4"]
        elif kind in {"MKV (wideo)", "WEBM (wideo)"}:
            if quality == "Najlepsza dostępna":
                alt_fmt = "bv*+ba/b"
            else:
                alt_fmt = f"bv*[height<={height}]+ba/b[height<={height}]"
            container = "mkv" if kind == "MKV (wideo)" else "webm"
            cmd += ["-f", alt_fmt, "--merge-output-format", container, "--recode-video", container]
    if subtitles:
        cmd += ["--write-subs", "--write-auto-subs", "--sub-langs", subtitle_langs(languages), "--convert-subs", "srt"]
    cmd += ["--", url.strip()]
    return cmd


def metadata_command(url: str, playlist: bool) -> list[str]:
    if not valid_youtube_url(url):
        raise ValueError("Nieprawidłowy link YouTube.")
    cmd = yt_base_command() + ["--dump-single-json", "--skip-download", "--no-progress"]
    if playlist:
        if not is_playlist_url(url):
            raise ValueError("Ten adres nie zawiera playlisty.")
        cmd += ["--yes-playlist", "--flat-playlist", "--playlist-end", "30"]
    else:
        cmd += ["--no-playlist"]
    return cmd + ["--", url.strip()]


def parse_progress(line: str) -> dict | None:
    if line.startswith("PROGRESS:"):
        fields = line[len("PROGRESS:"):].split("|", 2)
        if len(fields) != 3:
            return None
        num = re.search(r"([\d.,]+)\s*%", fields[0])
        try:
            pct = max(0.0, min(100.0, float(num.group(1).replace(",", ".")))) if num else 0
        except ValueError:
            pct = 0
        return {"type": "progress", "percent": pct, "speed": fields[1].strip(), "eta": fields[2].strip()}
    if line.startswith("ITEM:"):
        a = line[5:].split("|", 2)
        if len(a) == 3:
            return {"type": "item", "index": a[0], "total": a[1], "title": a[2].strip()}
    if line.startswith("FILE:"):
        return {"type": "file", "path": line[5:].strip()}
    return None


_file_lock = threading.RLock()


def load_json(path: Path, default):
    with _file_lock:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return default


def save_json(path: Path, value) -> None:
    """Atomic JSON persistence so crashes won't corrupt history/settings."""
    with _file_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix=".ytvd-", suffix=".json", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(value, f, ensure_ascii=False, indent=2)
            os.replace(temp, path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)


class History:
    def __init__(self, path: Path | None = None):
        self.path = path or user_data_dir() / "history.json"
        self.lock = threading.RLock()

    def all(self) -> list[dict]:
        with self.lock:
            data = load_json(self.path, [])
            return data if isinstance(data, list) else []

    def add(self, entry: dict) -> None:
        with self.lock:
            entries = self.all()
            entries.insert(0, {"date": time.strftime("%Y-%m-%d %H:%M:%S"), **entry})
            save_json(self.path, entries[:MAX_HISTORY])

    def clear(self) -> None:
        with self.lock:
            save_json(self.path, [])


def safe_thumbnail_url(url: str) -> bool:
    try:
        x = urlparse(url)
        if x.scheme != "https" or x.username or x.password or x.port not in (None, 443):
            return False
        host = (x.hostname or "").lower()
        return host == "ytimg.com" or host.endswith(".ytimg.com") or host == "ggpht.com" or host.endswith(".ggpht.com")
    except ValueError:
        return False


def fetch_thumbnail(url: str) -> bytes:
    if not safe_thumbnail_url(url):
        raise ValueError("Miniatura pochodzi spoza serwera obrazów YouTube.")
    req = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(req, timeout=12) as resp:
        content = resp.read(3 * 1024 * 1024 + 1)
    if len(content) > 3 * 1024 * 1024:
        raise ValueError("Miniatura przekracza 3 MB.")
    return content


def verify_sha256(path: Path, expected: str) -> bool:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().lower() == expected.lower()


def parse_sha256_sums(contents: str, filename: str = "yt-dlp.exe") -> str | None:
    for line in contents.splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64})\s+\*?" + re.escape(filename), line.strip())
        if match:
            return match.group(1).lower()
    return None


def update_engine(*, force: bool = False) -> str:
    """Update standalone yt-dlp.exe via the official release and a SHA256 checksum.

    Called from a background thread only. Rolls back to bundled engine on failure.
    Never runs a downloaded file before verification.
    """
    engine_dir = user_data_dir() / "engine"
    engine_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = engine_dir / "version.json"
    installed = engine_dir / "yt-dlp.exe"
    state = load_json(metadata_path, {})
    if not isinstance(state, dict):
        state = {}
    if not force and time.time() - float(state.get("checked_at", 0)) < 24 * 3600:
        return f"Silnik sprawdzony wcześniej: {state.get('tag', 'wersja dołączona')}."
    req = Request(API_URL, headers={"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"})
    with urlopen(req, timeout=15) as response:
        release = json.load(response)
    tag = release.get("tag_name", "")
    assets = release.get("assets", [])
    exe = next((a for a in assets if a.get("name") == "yt-dlp.exe"), None)
    if not exe or not tag:
        raise RuntimeError("Brak oficjalnego pliku yt-dlp.exe w najnowszym wydaniu.")
    digest_field = exe.get("digest") or ""
    expected = digest_field[7:] if re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest_field) else None
    if not expected:
        sums = next((a for a in assets if a.get("name") == "SHA2-256SUMS"), None)
        if not sums:
            raise RuntimeError("Brak sumy kontrolnej aktualizacji; pliku nie pobrano.")
        sums_url = sums["browser_download_url"]
        if not sums_url.startswith("https://github.com/yt-dlp/yt-dlp/releases/download/"):
            raise RuntimeError("Niezweryfikowane źródło sum kontrolnych.")
        with urlopen(Request(sums_url, headers={"User-Agent": USER_AGENT}), timeout=20) as response:
            expected = parse_sha256_sums(response.read(1024 * 1024).decode("utf-8"))
    if not expected:
        raise RuntimeError("Nie można potwierdzić sumy SHA256 aktualizacji.")
    url = exe["browser_download_url"]
    if not url.startswith("https://github.com/yt-dlp/yt-dlp/releases/download/"):
        raise RuntimeError("Niezweryfikowany adres aktualizacji.")
    if installed.is_file() and state.get("tag") == tag and verify_sha256(installed, expected):
        save_json(metadata_path, {"tag": tag, "checked_at": time.time()})
        return f"Silnik jest aktualny ({tag})."
    tmp = engine_dir / "yt-dlp.download"
    try:
        with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=45) as r, tmp.open("wb") as f:
            total = 0
            while True:
                block = r.read(512 * 1024)
                if not block:
                    break
                total += len(block)
                if total > 150 * 1024 * 1024:
                    raise RuntimeError("Plik aktualizacji przekroczył bezpieczny limit.")
                f.write(block)
        if not verify_sha256(tmp, expected):
            raise RuntimeError("Błędna suma SHA256 pobranego silnika. Aktualizacja przerwana.")
        os.replace(tmp, installed)
        save_json(metadata_path, {"tag": tag, "checked_at": time.time()})
        return f"Silnik zaktualizowany do {tag}."
    finally:
        if tmp.exists():
            tmp.unlink()
