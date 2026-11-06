import datetime as dt
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from infinity_features import schedule_date, is_due, playlist_indices, turbo_fragments, readable_speed
from cloud_license import CloudLicense, normalize_server, request_json
from video_studio import studio_command, concat_mp4
from core import make_download_command, SPEED_PROFILES
from updates import newer

class InfinityFeatureTests(unittest.TestCase):
    def test_playlist_selection(self):
        self.assertEqual(playlist_indices('1, 3,5-10'),'1,3,5-10')
        for text in ('0','1-0','a','1;rm','1--3','3-2','1-9999'):
            with self.subTest(value=text),self.assertRaises(ValueError):playlist_indices(text)
    def test_schedule_future(self):
        now=dt.datetime(2026,11,6,12,0)
        self.assertEqual(schedule_date('2026-11-06 12:30',now),'2026-11-06T12:30')
        self.assertFalse(is_due('2026-11-06T12:30',now))
        self.assertTrue(is_due('2026-11-06T12:30',now+dt.timedelta(hours=1)))
    def test_schedule_past_rejected(self):
        with self.assertRaises(ValueError):schedule_date('2020-01-01 08:00',dt.datetime(2026,1,1))
    def test_turbo(self):
        self.assertEqual([turbo_fragments('Infinity Auto',i) for i in (0,3,9)],[8,16,32])
        self.assertEqual(SPEED_PROFILES['Infinity Auto'],32)
    def test_speed(self):
        self.assertEqual(readable_speed('2.00MiB/s'),2)
        self.assertEqual(readable_speed('1024KiB/s'),1)
        self.assertEqual(readable_speed('N/A'),0)
    def test_command_playlist_selection(self):
        def mock_base():return ['yt-dlp']
        def mock_tool(name):return 'ffmpeg' if name.startswith('ffmpeg') else 'yt-dlp'
        cmd=make_download_command('https://www.youtube.com/playlist?list=PLabcd',Path('Downloads'),'MP4 (wideo)','720p (HD)',playlist=True,playlist_items='2-5',skip_duplicates=True,_tool=mock_tool,_base_command=mock_base)
        self.assertIn('--playlist-items',cmd)
        self.assertIn('2-5',cmd)
        self.assertIn('--download-archive',cmd)
        with self.assertRaises(ValueError):make_download_command('https://www.youtube.com/watch?v=abcdef',Path('Downloads'),'MP4 (wideo)','720p (HD)',playlist_items='2-5',_tool=mock_tool,_base_command=mock_base)
    def test_cloud_https(self):
        self.assertEqual(normalize_server('https://example.workers.dev/'),'https://example.workers.dev')
        for raw in ('http://example.com','file:///tmp/x','https://a:b@example.com','https://example.org:8080/'):
            with self.subTest(raw=raw),self.assertRaises(ValueError):normalize_server(raw)
    def test_cloud_token_not_granted_offline(self):
        with tempfile.TemporaryDirectory() as td:
            client=CloudLicense(td)
            self.assertFalse(client.premium())
            client.configure('https://example.workers.dev')
            with patch('cloud_license.request_json',side_effect=OSError('Offline')):
                self.assertFalse(client.validate()['active'])
            self.assertFalse(client.premium())
    def test_cloud_activate_and_validate(self):
        with tempfile.TemporaryDirectory() as td:
            client=CloudLicense(td)
            client.configure('https://example.workers.dev')
            with patch('cloud_license.request_json',return_value={'active':True,'token':'token123'}):
                self.assertTrue(client.activate('YVD5-code')['active'])
            self.assertTrue(client.premium())
            with patch('cloud_license.request_json',return_value={'active':False}):
                self.assertFalse(client.validate()['active'])
            self.assertFalse(client.premium())
    def test_studio_command(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'in.mp4';f.write_bytes(b'video')
            with patch('video_studio.tool',return_value='ffmpeg'):
                cmd=studio_command(f,Path(td)/'out.mp3','MP3','00:30','01:00')
            self.assertIn('libmp3lame',cmd)
            self.assertIn('-ss',cmd)
    def test_merge_requires_two_files(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):concat_mp4([Path(td)/'a.mp4'],Path(td)/'out.mp4')
    def test_update_version(self):
        self.assertTrue(newer('v12.2.0'))
        self.assertFalse(newer('v12.1.0'))
        self.assertFalse(newer('v10.0.0'))
    def test_cloud_secret_not_in_source(self):
        root=Path(__file__).resolve().parents[1]
        self.assertFalse(list(root.rglob('*.pem')))
        self.assertNotIn('ADMIN_TOKEN=',(root/'cloud_worker/wrangler.toml.example').read_text())
        self.assertIn('secret put ADMIN_TOKEN',(root/'cloud_worker/wrangler.toml.example').read_text())

class ReleaseUpdateSafetyTests(unittest.TestCase):
    def test_requires_newer_release_and_checksum(self):
        from update_management import official_assets
        import io
        def opener(req,timeout):
            return io.BytesIO(json.dumps({'tag_name':'v4.1.0','assets':[]}).encode())
        with self.assertRaisesRegex(ValueError,'nowszego'):
            official_assets(opener)

    def test_invalid_release_asset_rejected(self):
        from update_management import official_assets
        import io
        def opener(req,timeout):
            data={'tag_name':'v12.2.0','assets':[{'name':'YOUTUBE_VIDEO_DOWNLOADER_5_1_SETUP.exe','browser_download_url':'https://evil.invalid/trap','size':1000},{'name':'YVD_SETUP_SHA256.txt','browser_download_url':'https://github.com/adamhalo327-jpg/YOUTUBE_VIDEO_DOWNLOADER_WINDOWS/releases/download/v5.1/YVD_SETUP_SHA256.txt'}]}
            return io.BytesIO(json.dumps(data).encode())
        with self.assertRaisesRegex(ValueError,'Niezweryfikowany'):
            official_assets(opener)
