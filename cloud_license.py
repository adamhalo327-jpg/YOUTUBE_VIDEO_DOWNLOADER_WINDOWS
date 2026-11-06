"""Client for optional Cloudflare Worker Premium Cloud server.
No administrator secrets or private license signing keys are bundled in EXE.
Cloud grants require live server validation: no offline bypass.
"""
import json
import re
import secrets
import threading
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from pathlib import Path
from core import load_json,save_json,user_data_dir

MAX_RESPONSE=131072

def normalize_server(raw):
    u=urlsplit(str(raw).strip())
    if u.scheme!='https' or not u.hostname or u.username or u.password or u.query or u.fragment or u.port not in (None,443):
        raise ValueError('Serwer Premium Cloud musi mieć bezpieczny adres HTTPS.')
    return 'https://'+u.hostname+(u.path.rstrip('/') if u.path and u.path!='/' else '')

def request_json(server,path,data=None,token=None,opener=urlopen):
    base=normalize_server(server)
    if path not in ('/health','/activate','/validate','/admin/issue','/admin/list','/admin/revoke','/admin/extend','/admin/stats','/wallet/register','/wallet/status','/wallet/start','/wallet/complete','/wallet/buy'):
        raise ValueError('Nieznana operacja API')
    payload=json.dumps(data or {}).encode('utf-8') if data is not None else None
    headers={'User-Agent':'YVD-5.0','Accept':'application/json'}
    if payload is not None:headers['Content-Type']='application/json'
    if token:headers['Authorization']='Bearer '+token
    req=Request(base+path,data=payload,headers=headers,method='POST' if payload is not None else 'GET')
    try:
        with opener(req,timeout=12) as resp:
            body=resp.read(MAX_RESPONSE+1)
    except HTTPError as exc:
        raw=exc.read(8192)
        try: detail=json.loads(raw).get('error','HTTP '+str(exc.code))
        except (ValueError,AttributeError): detail='HTTP '+str(exc.code)
        raise ValueError(str(detail)[:220]) from exc
    if len(body)>MAX_RESPONSE:raise ValueError('Odpowiedź serwera jest zbyt duża.')
    obj=json.loads(body)
    if not isinstance(obj,dict):raise ValueError('Niepoprawna odpowiedź serwera')
    return obj

class CloudLicense:
    def __init__(self, directory=None):
        self.path=Path(directory or user_data_dir())/'premium-cloud.json'
        s=load_json(self.path,{})
        self.settings=s if isinstance(s,dict) else {}
        self.settings.setdefault('device',secrets.token_hex(16))
        self._active=False
        self._lock=threading.Lock()
        self._save()
    def _save(self):save_json(self.path,self.settings)
    def configure(self,server):
        new=normalize_server(server)
        if new!=self.settings.get('server'):
            self.settings.pop('token',None)
        self.settings['server']=new;self._save()
        with self._lock:self._active=False
    def activate(self,code):
        server=self.settings.get('server','')
        with self._lock:self._active=False
        result=request_json(server,'/activate',{'code':code.strip(),'device':self.settings['device']})
        if not result.get('active') or not result.get('token'):
            raise ValueError(result.get('error','Serwer nie aktywował kodu.'))
        self.settings['token']=result['token'];self._save()
        with self._lock:self._active=True
        return result
    def validate(self):
        try:
            if not self.settings.get('token') or not self.settings.get('server'):
                result={'active':False,'error':'Brak licencji Cloud'}
            else:
                result=request_json(self.settings['server'],'/validate',
                  {'device':self.settings['device'],'token':self.settings['token']})
        except Exception as exc:
            result={'active':False,'error':'Brak połączenia z serwerem: '+str(exc)[:110]}
        with self._lock:self._active=bool(result.get('active'))
        return result
    def premium(self):
        with self._lock:return self._active
    def deactivate(self):
        self.settings.pop('token',None);self._save()
        with self._lock:self._active=False
