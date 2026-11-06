"""Auto Update Center 4.0. Streams installer, checks SHA256 and asks before launching."""
from __future__ import annotations
import hashlib
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request,urlopen
from updates import check_release, newer

SETUP_PATTERN=re.compile(r'^YOUTUBE_VIDEO_DOWNLOADER_\d+_\d+(?:_\d+)?_SETUP\.exe$')
MAX_SETUP_SIZE=1024**3


def _url_good(url,asset=False):
    p=urlparse(url)
    base='/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS/releases/download/'
    if p.scheme!='https' or p.hostname!='github.com' or p.username or p.password or p.query or p.fragment or not p.path.startswith(base):
        raise ValueError('Niezweryfikowany adres pliku aktualizacji')
    return url


def official_assets(opener=urlopen):
    release=check_release(opener)
    if not release['newer']:raise ValueError('Brak wydania nowszego od 13.0.0')
    tag=release['tag']
    # Prefer file with version encoded in name, but allow patch builds reusing major.minor name.
    ver=tag.lstrip('vV').split('.')
    expected=f"YOUTUBE_VIDEO_DOWNLOADER_{ver[0]}_{ver[1]}_SETUP.exe"
    candidates=[a for a in release['assets'] if isinstance(a,dict) and SETUP_PATTERN.fullmatch(str(a.get('name','')))]
    setup=next((a for a in candidates if a.get('name')==expected), None)
    checksum=next((a for a in release['assets'] if isinstance(a,dict) and a.get('name')=='YVD_SETUP_SHA256.txt'),None)
    if not setup or not checksum:raise ValueError('Brak Setup.exe lub YVD_SETUP_SHA256.txt w wydaniu')
    for a in (setup,checksum):
        url=_url_good(str(a.get('browser_download_url','')))
        if f'/releases/download/{tag}/' not in url:raise ValueError('Pliki z różnych wydań')
    return setup,checksum


def _open(opener,url,timeout):
    req=Request(_url_good(url),headers={'User-Agent':'YVD-Update-Center-13'})
    return opener(req,timeout=timeout)


def _read_response(resp, max_bytes):
    data=resp.read(max_bytes+1)
    if len(data)>max_bytes:raise ValueError('Odpowiedź przekroczyła dozwolony rozmiar')
    return data


def download_verified_setup(folder,opener=urlopen,progress=None,cancel=None):
    """Downloads official signed-by-hash GitHub asset; never runs it. Progress callable(done,total)."""
    setup,checks=official_assets(opener)
    size=int(setup.get('size') or 0)
    if not 1<=size<=MAX_SETUP_SIZE:raise ValueError('Błędny rozmiar instalatora')
    with _open(opener,checks['browser_download_url'],30) as res:
        content=_read_response(res,4096).decode('utf-8-sig')
    match=re.search(r'(?im)^([a-f0-9]{64})\s+\*?'+re.escape(setup['name'])+r'\s*$',content)
    if not match:raise ValueError('Brak poprawnej sumy SHA256 dla instalatora')
    dest=Path(folder);dest.mkdir(parents=True,exist_ok=True)
    target=dest/setup['name']
    # Never overwrite a pre-existing downloaded file without verification.
    temp=target.with_suffix('.partial')
    if target.is_file() and target.stat().st_size==size:
        h=hashlib.sha256()
        with target.open('rb') as fh:
            for chunk in iter(lambda:fh.read(1024*1024),b''):h.update(chunk)
        if h.hexdigest().lower()==match.group(1).lower():
            if progress:progress(size,size)
            return target
    digest=hashlib.sha256();count=0
    try:
        with _open(opener,setup['browser_download_url'],90) as response,temp.open('wb') as f:
            for chunk in iter(lambda:response.read(256*1024),b''):
                if cancel is not None and cancel.is_set():raise InterruptedError('Pobieranie anulowane')
                count+=len(chunk)
                if count>MAX_SETUP_SIZE or count>size:raise ValueError('Nieprawidłowy rozmiar pobierania')
                digest.update(chunk);f.write(chunk)
                if progress:progress(count,size)
        if count!=size:raise ValueError('Niepełny plik instalatora')
        if digest.hexdigest().lower()!=match.group(1).lower():raise ValueError('Nieprawidłowa suma SHA256 instalatora')
        temp.replace(target)
        return target
    finally:
        temp.unlink(missing_ok=True)
