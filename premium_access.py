"""Central FREE / PREMIUM feature policy, evaluated at action time.

A signed, unexpired offline code or a validated Cloud license grants Premium.
Do not rely on disabled GUI widgets alone: enforce at scheduling/resume time.
"""
from dataclasses import dataclass
from core import PREMIUM_KINDS, QUALITY_OPTIONS

FREE_MAX_PARALLEL = 1
PREMIUM_MAX_PARALLEL = 10
FREE_MAX_FRAGMENTS = 12
FREE_MAX_HEIGHT = 1080
PREMIUM_FEATURES = (
    "4K / 8K i najlepsza jakość powyżej 1080p", "Turbo Infinity",
    "Całe playlisty i Smart Playlists", "Pobieranie 2–10 filmów równocześnie",
    "Video Studio i zaawansowana konwersja", "Harmonogram pobierania",
    "Rozszerzone statystyki i motywy", "Zaawansowane napisy"
)

@dataclass(frozen=True)
class DownloadSelection:
    kind: str
    quality: str
    fragments: int
    parallel: int
    playlist: bool = False
    playlist_items: str = ""
    skip_duplicates: bool = False
    schedule_at: str = ""
    trim_start: str = ""
    trim_end: str = ""
    premium_mode: bool = False


def quality_height(quality):
    if quality == "Najlepsza dostępna":
        return None
    import re
    m = re.match(r"^(\d+)p", quality)
    if not m:
        raise ValueError("Nieznana jakość wideo.")
    return int(m.group(1))


def paid_reason(selection: DownloadSelection):
    """Returns the exact premium feature required, or None for free tasks."""
    if selection.kind in PREMIUM_KINDS:
        return "Zaawansowana konwersja"
    if selection.kind not in ("MP4 (wideo)", "MP3 (audio)"):
        return "Format Premium"
    if selection.kind == "MP4 (wideo)":
        height = quality_height(selection.quality)
        if height is None or height > FREE_MAX_HEIGHT:
            return "Najlepsza jakość / 4K / 8K"
    if selection.parallel > FREE_MAX_PARALLEL:
        return "Pobieranie wielu filmów jednocześnie"
    if selection.fragments > FREE_MAX_FRAGMENTS or selection.premium_mode:
        return "Turbo Infinity / Turbo Pro"
    if selection.playlist or selection.playlist_items or selection.skip_duplicates:
        return "Playlisty / Smart Playlists"
    if selection.schedule_at:
        return "Harmonogram pobierania"
    if selection.trim_start or selection.trim_end:
        return "Przycinanie wideo"
    return None


def require_access(selection: DownloadSelection, premium: bool):
    if premium:
        if selection.parallel < 1 or selection.parallel > PREMIUM_MAX_PARALLEL:
            raise ValueError("Premium: do 10 równoległych pobrań.")
        return
    reason = paid_reason(selection)
    if reason:
        raise PermissionError(reason + " wymaga aktywnego kodu Premium.")


def free_quality(quality, kind="MP4 (wideo)"):
    """A safe explicit 1080p cap for legacy free tasks using 'best available'."""
    if kind == "MP4 (wideo)" and quality == "Najlepsza dostępna":
        return "1080p (Full HD)"
    return quality
