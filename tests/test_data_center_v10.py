import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from data_center import export_backup, import_backup, diagnostics, FILES

class TestDataCenter(unittest.TestCase):
    def test_backup_roundtrip_without_secrets(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t); a=base/'a'; b=base/'b';a.mkdir()
            (a/'settings.json').write_text('{"theme":"Ciemny"}')
            (a/'history.json').write_text('[]')
            (a/'queue-v3.json').write_text('[]')
            (a/'license.json').write_text('secret')
            archive=export_backup(a,base/'copy.zip')
            with zipfile.ZipFile(archive) as z:
                self.assertEqual(set(z.namelist()),set(FILES)|{'manifest.json'})
                self.assertNotIn('license.json',z.namelist())
            self.assertEqual(len(import_backup(b,archive)),3)
            self.assertEqual(json.loads((b/'settings.json').read_text())['theme'],'Ciemny')
    def test_reject_extra_path(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'bad.zip'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('manifest.json',json.dumps({'product':'YOUTUBE VIDEO DOWNLOADER','backup_format':1}))
                z.writestr('../escape.txt','evil')
            with self.assertRaises(ValueError):import_backup(Path(t)/'out',p)
    def test_reject_non_json_before_overwrite(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'bad.zip';out=Path(t)/'out';out.mkdir()
            (out/'settings.json').write_text('{"ok":true}')
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('manifest.json',json.dumps({'product':'YOUTUBE VIDEO DOWNLOADER','backup_format':1}))
                z.writestr('settings.json','not json')
            with self.assertRaises(ValueError):import_backup(out,p)
            self.assertIn('true',(out/'settings.json').read_text())
    def test_diagnostics(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertIn('wolne_gb',diagnostics(t,t))
