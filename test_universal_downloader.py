import unittest
from pathlib import Path
from universal_downloader import UniversalSelection, platform_for, validate, build_command, preview_command, PLATFORMS

class UniversalTests(unittest.TestCase):
    def s(self, **kw):
        return UniversalSelection('https://www.youtube.com/watch?v=abc123', Path('/tmp/out'), **kw)

    def test_platforms(self):
        examples = {'TikTok':'https://www.tiktok.com/@a/video/123','Instagram / Reels':'https://www.instagram.com/reel/xyz/',
                    'Twitch':'https://www.twitch.tv/videos/123', 'Reddit':'https://www.reddit.com/r/test/comments/123',
                    'Kick':'https://kick.com/video/123', 'YouTube / Shorts':'https://youtu.be/abc'}
        for name, url in examples.items():
            with self.subTest(name=name): self.assertEqual(platform_for(url), name)
    def test_reject_local_and_bad(self):
        for url in ('http://localhost/','http://127.0.0.1/','http://192.168.1.10/','file:///etc/passwd',
                    'https://youtube.com.evil.com/watch?v=abc', 'https://user:pwd@youtube.com/watch?v=abc',
                    'https://youtube.com:8080/watch?v=abc', 'https://example.org/movie', 'https://youtube.com/\n--exec=bad'):
            with self.subTest(url=url): self.assertRaises(ValueError, platform_for, url)
    def test_free_mp4(self):
        validate(self.s(), False)
        self.assertIn('--no-playlist', build_command(self.s(),premium=False,base=['yt-dlp'],ffmpeg='ffmpeg'))
    def test_free_mp3(self):
        validate(self.s(container='MP3'), False)
    def test_premium_gates(self):
        for x in ({'container':'FLAC'},{'quality':'2160p (4K)'},{'playlist':True},{'subtitles':True},{'trim':'00:00:01-00:00:09'}):
            with self.subTest(x=x): self.assertRaises(PermissionError,validate,self.s(**x),False)
            validate(self.s(**x),True)
    def test_args_and_audio(self):
        cmd = build_command(self.s(container='FLAC'),premium=True,base=['yt-dlp'],ffmpeg='ffmpeg')
        self.assertEqual(cmd[-2:],['--',self.s().url]);self.assertIn('flac',cmd)
    def test_no_ffmpeg_for_audio(self):
        self.assertRaises(FileNotFoundError,build_command,self.s(container='WAV'),premium=True,base=['yt-dlp'],ffmpeg='')
    def test_invalid_trim(self):
        self.assertRaises(ValueError,validate,self.s(trim='abc'),True)

if __name__ == '__main__': unittest.main()
