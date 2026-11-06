"""Fetch an official release setup only after user confirmation and SHA256 verification."""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from updates import newer

LATEST_API='https://api.github.com/repos/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS/releases/latest'
RELEASES_PAGE='https://github.com/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS/releases/latest'
SETUP_PATTERN=re.compile(r'^YOUTUBE_VIDEO_DOWNLOADER_\d+_\d+_SETUP\.exe$')


def official_assets(opener=urlopen):
    req=Request(LATEST_API,headers={'User-Agent':'YVD-Windows-5.0','Accept':'application/vnd.github+json'})
    with opener(req,timeout=15) as res:body=res.read(256001)
    if len(body)>256000:raise ValueError('Odpowiedź GitHub jest za duża')
    payload=json.loads(body)
    if not newer(str(payload.get('tag_name',''))):
        raise ValueError('Brak wydania nowszego od wersji 5.0.')
    assets=payload.get('assets',[])
    if not isinstance(assets,list):raise ValueError('Nieprawidłowa lista plików')
    setup=next((a for a in assets if isinstance(a,dict) and SETUP_PATTERN.fullmatch(a.get('name',''))),None)
    checksum=next((a for a in assets if isinstance(a,dict) and a.get('name')=='YVD_SETUP_SHA256.txt'),None)
    if not setup or not checksum:raise ValueError('Wydanie musi zawierać Setup.exe oraz YVD_SETUP_SHA256.txt.')
    for asset in (setup,checksum):
        parsed=urlparse(asset.get('browser_download_url',''))
        if parsed.scheme!='https' or parsed.hostname!='github.com' or not parsed.path.startswith('/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS/releases/download/'):
            raise ValueError('Niezweryfikowany adres pliku wydania')
    return setup,checksum


def download_verified_setup(folder,opener=urlopen):
    setup,checks=official_assets(opener)
    max_size=1024**3
    if not 1<=int(setup.get('size',0))<=max_size:raise ValueError('Niepoprawny rozmiar instalatora.')
    with opener(Request(checks['browser_download_url'],headers={'User-Agent':'YVD-Windows-5.0'}),timeout=30) as res:
        text=res.read(4096).decode('utf-8')
    match=re.search(r'(?im)^([a-f0-9]{64})\s+\*?'+re.escape(setup['name'])+r'\s*$',text)
    if not match:raise ValueError('Brak sumy SHA256 dla instalatora')
    directory=Path(folder);directory.mkdir(parents=True,exist_ok=True)
    target=directory/setup['name'];tmp=target.with_suffix('.partial')
    digest=hashlib.sha256();size=0
    try:
        with opener(Request(setup['browser_download_url'],headers={'User-Agent':'YVD-Windows-5.0'}),timeout=60) as response, tmp.open('wb') as output:
            while True:
                chunk=response.read(1024*1024)
                if not chunk:break
                size+=len(chunk)
                if size>max_size:raise ValueError('Instalator przekroczył limit 1 GB')
                digest.update(chunk);output.write(chunk)
        if digest.hexdigest().lower()!=match[1].lower():raise ValueError('Błędna suma SHA256 instalatora.')
        tmp.replace(target)
    finally:
        tmp.unlink(missing_ok=True)
    return target
