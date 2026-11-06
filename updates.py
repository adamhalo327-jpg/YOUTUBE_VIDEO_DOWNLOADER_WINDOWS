"""Update Center 4.0: GitHub release version detection (never executes downloads)."""
from __future__ import annotations
import json
import re
from urllib.request import Request, urlopen
from urllib.parse import urlparse

OWNER="adamhalo327-jpg"
REPO="YOUTUBE_VIDEO_DOWNLOADER_WINDOWS"
ROOT=f"https://github.com/{OWNER}/{REPO}"
RELEASES_API=f"https://api.github.com/repos/{OWNER}/{REPO}/releases/latest"
RELEASES_LIST_API=f"https://api.github.com/repos/{OWNER}/{REPO}/releases?per_page=15"
RELEASES_WEB=f"{ROOT}/releases/latest"
CURRENT_VERSION="13.0.0"


def version_tuple(value):
    match=re.fullmatch(r"v?(\d{1,3})\.(\d{1,3})(?:\.(\d{1,3}))?",str(value).strip(), re.IGNORECASE)
    if not match:raise ValueError("Niepoprawny numer wersji")
    return tuple(int(n or 0) for n in match.groups())


def newer(tag,current=CURRENT_VERSION):
    try:return version_tuple(tag)>version_tuple(current)
    except ValueError:return False


def _get_json(url,opener=urlopen,max_bytes=1_000_000):
    req=Request(url,headers={"Accept":"application/vnd.github+json","User-Agent":"YVD-Update-Center-13"})
    with opener(req,timeout=15) as resp:
        effective=getattr(resp,'url',url)
        if urlparse(effective).hostname!='api.github.com' or urlparse(effective).scheme!='https':
            raise ValueError('Niebezpieczne przekierowanie API')
        payload=resp.read(max_bytes+1)
    if len(payload)>max_bytes:raise ValueError('Przekroczono rozmiar odpowiedzi API')
    return json.loads(payload)


def _release(data):
    if not isinstance(data,dict):raise ValueError('Niepoprawne dane wydania')
    tag=str(data.get('tag_name',''))
    version_tuple(tag)
    url=str(data.get('html_url',''))
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname!='github.com' or not parsed.path.startswith(ROOT.replace('https://github.com','')+'/releases/tag/'):
        raise ValueError('Niezweryfikowany link wydania')
    return {'tag':tag,'url':url,'newer':newer(tag),'name':str(data.get('name') or tag)[:180],
            'notes':str(data.get('body') or '')[:8000], 'published_at':data.get('published_at'),
            'prerelease':bool(data.get('prerelease')), 'draft':bool(data.get('draft')),
            'assets':data.get('assets') if isinstance(data.get('assets'),list) else []}


def check_release(opener=urlopen):
    d=_get_json(RELEASES_API,opener)
    release=_release(d)
    if release['draft'] or release['prerelease']:raise ValueError('Najnowsze wydanie nie jest stabilne')
    return release


def release_history(opener=urlopen):
    data=_get_json(RELEASES_LIST_API,opener)
    if not isinstance(data,list):raise ValueError('Nieprawidłowa lista wydań')
    out=[]
    for item in data[:15]:
        try:
            v=_release(item)
            if not v['draft'] and not v['prerelease']:out.append(v)
        except ValueError:continue
    return out
