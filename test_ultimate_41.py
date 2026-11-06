import tempfile
import unittest
from pathlib import Path
from download_statistics import summarize, readable_bytes
from owner_registry import record_issue, read_registry, export_csv
from updates import newer, version_tuple

class Version41Tests(unittest.TestCase):
    def test_version_compare(self):
        self.assertTrue(newer('v5.1.0'))
        self.assertFalse(newer('v4.0.9'))
        self.assertFalse(newer('garbage'))
        self.assertEqual(version_tuple('v4.1'), (4,1,0))

    def test_statistics(self):
        entries = [{'kind':'MP4','path':'a'}, {'kind':'MP3','path':'b'}, {'kind':'MP4','path':'a'}]
        res = summarize(entries, lambda p: {'a':1000,'b':None}[p])
        self.assertEqual(res['bytes'],1000)
        self.assertEqual(res['count'],3)
        self.assertEqual(res['missing'],1)
        self.assertEqual(res['formats']['MP4'],2)
        self.assertIn('KB',readable_bytes(2024))

    def test_registry_no_plaintext_code(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'history.json'
            record_issue('SECRET-CODE', 'Test', None, path)
            self.assertNotIn('SECRET-CODE', path.read_text())
            self.assertEqual(len(read_registry(path)),1)
            self.assertEqual(read_registry(path)[0]['expires_at'],'bezterminowo')
            csv_path=Path(folder)/'history.csv'
            self.assertEqual(export_csv(csv_path,path),1)
            self.assertTrue(csv_path.exists())
