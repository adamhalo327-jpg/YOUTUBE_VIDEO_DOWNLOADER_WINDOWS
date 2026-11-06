"""Bezpieczne lokalne kopie danych (bez licencji i kluczy prywatnych)."""
from pathlib import Path
import datetime as dt
import json
import shutil
import zipfile

FILES = ("settings.json", "history.json", "queue-v3.json")
MAX_BYTES = 16 * 1024 * 1024

def diagnostics(data_folder, download_folder, tool_names=("yt-dlp.exe", "ffmpeg.exe", "ffprobe.exe", "deno.exe")):
    home = Path(data_folder)
    folder = Path(download_folder)
    try:
        total, used, free = shutil.disk_usage(folder if folder.exists() else folder.parent)
    except OSError:
        total = free = 0
    return {
        "wolne_gb": round(free / (1024 ** 3), 2),
        "dysk_gb": round(total / (1024 ** 3), 2),
        "dane": {f: (home / f).exists() for f in FILES},
        "narzedzia": {name: bool(shutil.which(name)) for name in tool_names},
    }

def _valid_document(name, content):
    if len(content) > MAX_BYTES:
        raise ValueError("Plik kopii przekracza limit 16 MB.")
    data = json.loads(content)
    if name == "settings.json" and not isinstance(data, dict):
        raise ValueError("Nieprawidłowe ustawienia.")
    if name in ("history.json", "queue-v3.json") and not isinstance(data, list):
        raise ValueError("Nieprawidłowa historia/kolejka.")
    return data

def export_backup(data_folder, destination):
    home = Path(data_folder)
    target = Path(destination)
    if target.suffix.lower() != ".zip":
        raise ValueError("Kopia musi być archiwum ZIP.")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as z:
        manifest = {"product": "YOUTUBE VIDEO DOWNLOADER", "backup_format": 1,
                    "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "note": "Bez kluczy licencji i ustawień Premium Cloud"}
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False))
        for name in FILES:
            f = home / name
            if f.is_file():
                content = f.read_bytes()
                _valid_document(name, content)
                z.writestr(name, content)
    return target

def import_backup(data_folder, source):
    """Weryfikuje CAŁĄ kopię przed zapisaniem i zachowuje pliki .before-v10."""
    home = Path(data_folder)
    pending = {}
    with zipfile.ZipFile(source) as z:
        names = z.namelist()
        if len(names) != len(set(names)) or any(n not in (*FILES, "manifest.json") for n in names):
            raise ValueError("Kopia zawiera nieznane lub powtarzające się pliki.")
        manifest = json.loads(z.read("manifest.json"))
        if manifest.get("product") != "YOUTUBE VIDEO DOWNLOADER" or manifest.get("backup_format") != 1:
            raise ValueError("Nieprawidłowy format kopii.")
        for name in FILES:
            if name in names:
                info=z.getinfo(name)
                if info.file_size > MAX_BYTES:
                    raise ValueError("Plik w kopii przekracza limit.")
                content=z.read(name)
                _valid_document(name, content)
                pending[name] = content
    home.mkdir(parents=True, exist_ok=True)
    for name, content in pending.items():
        destination = home / name
        if destination.exists():
            shutil.copy2(destination, home / (name + ".before-v10"))
        temp=home/(name+".importing")
        temp.write_bytes(content)
        temp.replace(destination)
    return sorted(pending)
