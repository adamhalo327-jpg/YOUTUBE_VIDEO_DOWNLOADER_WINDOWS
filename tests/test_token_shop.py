import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from token_shop import CloudTokenShop, PACKAGES

class CloudWalletTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.cloud=type('Cloud',(),{'settings':{'server':'https://cloud.example.workers.dev','device':'a'*32}})()
        self.wallet=CloudTokenShop(Path(self.tmp.name)/'wallet.json',self.cloud)
    def tearDown(self):self.tmp.cleanup()
    def test_no_local_balance_or_mint(self):
        self.assertFalse(hasattr(self.wallet,'earn'))
        self.assertEqual(self.wallet.balance,0)
        self.assertFalse(self.wallet.premium())
    def test_registration_and_remote_balance(self):
        def fake(server,path,payload,token=None):
            if path=='/wallet/register':return {'wallet_token':'yvdw-'+'b'*64}
            if path=='/wallet/status':return {'balance':120,'premium_until':None,'active':False}
            raise AssertionError(path)
        with patch('token_shop.request_json',side_effect=fake):
            self.wallet.refresh()
        self.assertEqual(self.wallet.balance,120)
        self.assertFalse(self.wallet.premium())
        disk=json.loads(self.wallet.path.read_text())
        self.assertNotIn('balance',disk)
        self.assertNotIn('premium_until',disk)
    def test_paid_entitlement_from_server_only(self):
        def fake(server,path,payload,token=None):
            if path=='/wallet/register':return {'wallet_token':'yvdw-'+'b'*64}
            if path=='/wallet/buy':return {'balance':0,'premium_until':'2099-01-01T00:00:00Z','active':True}
            raise AssertionError(path)
        with patch('token_shop.request_json',side_effect=fake):self.wallet.buy('STARTER')
        self.assertTrue(self.wallet.premium())
        self.assertEqual(PACKAGES['ULTRA']['tokens'],1500)
    def test_no_wallet_token_in_public_json_balance(self):
        self.assertNotIn('balance', vars(self.wallet).get('_secret',''))
    def test_empty_server_fails_closed(self):
        self.cloud.settings['server']=''
        with self.assertRaises(ValueError):self.wallet.refresh()
    def test_cannot_spend_unknown_package(self):
        with self.assertRaises(ValueError):self.wallet.buy('CUSTOM')
    def test_credential_tied_to_server(self):
        self.wallet._server='https://first.example.workers.dev'
        self.wallet._secret='yvdw-'+'b'*64
        with self.assertRaises(ValueError):self.wallet.refresh()
    def test_fails_closed_without_cloud(self):
        with patch('token_shop.request_json',side_effect=OSError('offline')):
            with self.assertRaises(OSError):self.wallet.buy('STARTER')
        self.assertFalse(self.wallet.premium())
if __name__=='__main__':unittest.main()
