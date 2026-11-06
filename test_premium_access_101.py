import unittest
from premium_access import DownloadSelection, require_access, paid_reason, free_quality

class PremiumAccessTests(unittest.TestCase):
    def selection(self, **options):
        base=dict(kind="MP4 (wideo)",quality="1080p (Full HD)",fragments=8,parallel=1)
        base.update(options)
        return DownloadSelection(**base)

    def test_free_video_and_audio(self):
        require_access(self.selection(),False)
        require_access(self.selection(kind="MP3 (audio)"),False)

    def test_high_res_and_best_quality(self):
        for q in ("1440p (2K)","2160p (4K)","4320p (8K)","Najlepsza dostępna"):
            with self.subTest(q=q), self.assertRaises(PermissionError):
                require_access(self.selection(quality=q),False)

    def test_bad_quality_rejected(self):
        with self.assertRaises(ValueError):paid_reason(self.selection(quality="nope"))

    def test_free_multi_blocked(self):
        with self.assertRaises(PermissionError):require_access(self.selection(parallel=2),False)
        require_access(self.selection(parallel=10),True)
        with self.assertRaises(ValueError):require_access(self.selection(parallel=11),True)

    def test_all_paid_options(self):
        for options in (dict(kind="MKV (wideo)"),dict(fragments=24),dict(premium_mode=True),
                        dict(playlist=True),dict(playlist_items="1-3"),dict(skip_duplicates=True),
                        dict(schedule_at="2030-03-01 13:00"),dict(trim_start="00:03")):
            with self.subTest(options=options),self.assertRaises(PermissionError):
                require_access(self.selection(**options),False)
            require_access(self.selection(**options),True)

    def test_quality_safe_default(self):
        self.assertEqual(free_quality("Najlepsza dostępna"),"1080p (Full HD)")

    def test_gui_enforcement_points(self):
        from pathlib import Path
        src=(Path(__file__).resolve().parents[1]/"gui.py").read_text(encoding="utf-8")
        for point in ("require_access(selection,premium)","paid_reason(self._task_selection(task))", "_has_premium()", "_change_theme", "_studio_start"):
            self.assertIn(point,src)

if __name__ == "__main__": unittest.main()
