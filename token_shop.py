"""Cloudflare D1 authoritative token wallet client. No local balance or purchase rights.

IMPORTANT: an untrusted Windows client cannot prove a real download to the server.
The server limits abuse, but this is a loyalty beta, not money or a fraud-proof currency.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import threading
import time
import uuid
from pathlib import Path
from cloud_license import request_json

PACKAGES = {
    'STARTER': {'tokens': 100, 'days': 1},
    'PRO': {'tokens': 500, 'days': 7},
    'ULTRA': {'tokens': 1500, 'days': 30},
}
TOKEN_PER_DOWNLOAD = 10
DAILY_CAP = 100

class CloudTokenShop:
    def __init__(self, path: Path, cloud):
        self.path=Path(path)
        self.cloud=cloud
        self._lock=threading.RLock()
        self._balance=0
        self._until=None
        self._validated=0.0
        self._server=''
        self._secret=''
        self._load()

    def _load(self):
        try:
            data=json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data,dict):raise ValueError('Invalid wallet state')
            self._server=str(data.get('server',''))
            self._secret=str(data.get('wallet_token',''))
            if self._secret and (not self._secret.startswith('yvdw-') or len(self._secret)!=69):
                raise ValueError('Invalid wallet token')
        except FileNotFoundError:pass
        except Exception as exc:raise ValueError('Portfel wymaga naprawy; nie nadpisano danych') from exc

    def _save(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        tmp=self.path.with_suffix('.tmp')
        with tmp.open('w',encoding='utf-8') as stream:
            json.dump({'server':self._server,'wallet_token':self._secret},stream)
            stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,self.path)
        if os.name!='nt':
            os.chmod(self.path,0o600)

    def _server_now(self):
        server=self.cloud.settings.get('server','')
        if not server:raise ValueError('Ustaw najpierw adres Premium Cloud w zakładce Cloud')
        return server

    def _ensure(self):
        server=self._server_now()
        if self._secret and self._server!=server:
            raise ValueError('Portfel jest powiązany z innym serwerem; nie nadpisuj jego danych')
        if not self._secret:
            result=request_json(server,'/wallet/register',{'device':self.cloud.settings['device']})
            secret=result.get('wallet_token','')
            if not secret.startswith('yvdw-') or len(secret)!=69:
                raise ValueError('Serwer nie utworzył poprawnego portfela')
            self._server=server;self._secret=secret;self._save()
        return server

    def _call(self,path,values=None):
        with self._lock:
            server=self._ensure()
            payload={'device':self.cloud.settings['device'],**(values or {})}
            result=request_json(server,path,payload,token=self._secret)
            if 'balance' in result:
                self._balance=max(0,int(result['balance']))
                raw=result.get('premium_until')
                try:self._until=dt.datetime.fromisoformat(raw.replace('Z','+00:00')) if raw else None
                except (ValueError,AttributeError):self._until=None
                self._validated=time.monotonic()
            return result

    def refresh(self):return self._call('/wallet/status')

    @property
    def balance(self):return self._balance

    def premium_until(self):return self._until

    def premium(self):
        # Fail-closed: never grant token-Premium solely from a local file or stale cache.
        return bool(self._until and time.monotonic()-self._validated<120
                    and self._until>dt.datetime.now(dt.timezone.utc))

    def start(self,url):
        result=self._call('/wallet/start',{'url':url})
        return result.get('ticket')

    def complete(self,ticket):
        if not ticket:return {'awarded':0,'reason':'Brak zgłoszenia pobierania'}
        return self._call('/wallet/complete',{'ticket':ticket})

    def buy(self,name):
        if name not in PACKAGES:raise ValueError('Nieznany pakiet')
        result=self._call('/wallet/buy',{'package':name,'request_id':str(uuid.uuid4())})
        if result.get('error'):raise ValueError(result['error'])
        if not self._until:raise ValueError('Serwer nie potwierdził zakupu')
        return self._until
