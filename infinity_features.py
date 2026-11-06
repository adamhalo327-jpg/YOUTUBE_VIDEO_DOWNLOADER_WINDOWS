"""Pure feature helpers for 5.0: scheduling, adaptive Turbo and safe playlist parsing."""
import datetime as dt
import re

def schedule_date(value: str, now=None) -> str:
    if not value.strip():
        return ""
    try:
        date=dt.datetime.strptime(value.strip(), "%Y-%m-%d %H:%M")
    except ValueError as ex:
        raise ValueError('Harmonogram podaj jako RRRR-MM-DD GG:MM.') from ex
    if date <= (now or dt.datetime.now()):
        raise ValueError('Harmonogram musi być w przyszłości.')
    return date.isoformat(timespec='minutes')

def is_due(value: str, now=None) -> bool:
    if not value:
        return True
    try:
        return dt.datetime.fromisoformat(value) <= (now or dt.datetime.now())
    except ValueError:
        return False

def playlist_indices(value: str) -> str:
    """yt-dlp safe subset of indices or bounded ranges, no arbitrary extra arguments."""
    if not value.strip():
        return ''
    bits=value.replace(' ', '').split(',')
    if len(bits)>100:
        raise ValueError('Za dużo pozycji.')
    for bit in bits:
        m=re.fullmatch(r'(\d{1,5})(?:-(\d{1,5}))?',bit)
        if not m or int(m[1])<1 or (m[2] and (int(m[2])<int(m[1]) or int(m[2])-int(m[1])>500)):
            raise ValueError('Pozycje podaj np. 1,3,5-10.')
    return ','.join(bits)

def turbo_fragments(profile: str, previous_mib_s: float=0.0) -> int:
    """Conservative adaptive fragment count; actual network may not support concurrency."""
    if profile!='Infinity Auto':
        raise ValueError('Nieznany profil Turbo Infinity.')
    return 8 if previous_mib_s < 2 else (16 if previous_mib_s < 8 else 32)

def readable_speed(raw):
    """Parse yt-dlp style KiB/s / MiB/s / GiB/s to MiB/s."""
    m=re.search(r'(\d+(?:\.\d+)?)\s*(B|KiB|MiB|GiB|KB|MB|GB)/s',str(raw),re.I)
    if not m:return 0.0
    multipliers={'B':1/1048576,'KIB':1/1024,'MIB':1,'GIB':1024,'KB':1/1000,'MB':1.048576,'GB':1048.576}
    return round(float(m[1])*multipliers[m[2].upper()],3)
