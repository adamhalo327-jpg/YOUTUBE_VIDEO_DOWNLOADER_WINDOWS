import hashlib
import io
import json
from pathlib import Path
from unittest.mock import Mock
import pytest
from updates import newer, version_tuple, _release
from update_management import download_verified_setup

BASE='https://github.com/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS/releases/'

def test_version_check():
    assert version_tuple('v13.0.0')==(13,0,0)
    assert newer('13.0.1')
    assert not newer('12.1.2')
    assert not newer('13.0.0')
    assert not newer('xyz13.0.1abc')


def test_release_validation():
    data={'tag_name':'v13.1.0','html_url':BASE+'tag/v13.1.0','name':'Test'}
    assert _release(data)['newer'] is True
    data['html_url']='https://evil.example/foo'
    with pytest.raises(ValueError):_release(data)

class Response:
    def __init__(self,data,url='https://api.github.com/'):
        self.content=io.BytesIO(data);self.url=url
    def read(self,n=-1):return self.content.read(n)
    def __enter__(self):return self
    def __exit__(self,*args):pass

def test_download_sha256(tmp_path):
    data=b'fake installer content'
    name='YOUTUBE_VIDEO_DOWNLOADER_13_1_SETUP.exe'
    token='v13.1.0'
    prefix=BASE+'download/'+token+'/'
    setup={'name':name,'size':len(data),'browser_download_url':prefix+name}
    checksum={'name':'YVD_SETUP_SHA256.txt','browser_download_url':prefix+'YVD_SETUP_SHA256.txt'}
    release={'tag_name':token,'html_url':BASE+'tag/'+token,'assets':[setup,checksum]}
    def opener(req,timeout=0):
        url=req.full_url
        if '/api.github.com/' in url:return Response(json.dumps(release).encode())
        if url.startswith('https://api.github.com/'):return Response(json.dumps(release).encode())
        if url.endswith('YVD_SETUP_SHA256.txt'):return Response((hashlib.sha256(data).hexdigest()+'  '+name+'\n').encode(),url)
        if url.endswith('.exe'):return Response(data,url)
        raise AssertionError(url)
    result=download_verified_setup(tmp_path,opener=opener)
    assert result.read_bytes()==data
