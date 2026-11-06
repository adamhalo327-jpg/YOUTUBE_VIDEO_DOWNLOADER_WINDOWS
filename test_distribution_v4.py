"""Static distribution checks; do not require Windows GUI or Inno compiler."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DistributionV4Tests(unittest.TestCase):
    def test_original_modules_and_owner_panel_retained(self):
        for file in ('app.py','core.py','gui.py','licensing.py','tools/issue_premium_code.py','tools/premium_generator_gui.py'):
            with self.subTest(file=file):
                self.assertTrue((ROOT / file).is_file())

    def test_title_and_banner(self):
        code=(ROOT / 'gui.py').read_text(encoding='utf-8')
        tree=ast.parse(code)
        cls=next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name=='UltraDownloader')
        init=next(x for x in cls.body if isinstance(x, ast.FunctionDef) and x.name=='__init__')
        windows_titles=[x for x in ast.walk(init) if isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='title']
        self.assertEqual(len(windows_titles), 1)
        self.assertEqual(ast.unparse(windows_titles[0]), 'self.title(APP_TITLE)')
        self.assertIn('AUTO UPDATE CENTER 13.0',code)

    def test_installer_contains_folder_and_uninstall(self):
        script=(ROOT / 'installer/YOUTUBE_VIDEO_DOWNLOADER.iss').read_text(encoding='utf-8')
        for text in ('PrivilegesRequired=lowest', 'recursesubdirs createallsubdirs','UninstallDisplayIcon', 'userprograms','userdesktop','YOUTUBE_VIDEO_DOWNLOADER.exe'):
            with self.subTest(text=text): self.assertIn(text,script)
        self.assertNotIn('UninstallDelete',script)

    def test_workflow_has_three_artifacts(self):
        workflow=(ROOT / '.github/workflows/build-13-0.yml').read_text(encoding='utf-8')
        for item in ('workflow_dispatch:', 'push:', 'python -m unittest discover -s tests -v', 'YVD_13_0_PORTABLE_WINDOWS','YVD_13_0_INSTALLER_WINDOWS', 'YVD_13_0_PREMIUM_OWNER_WINDOWS','YVD_13_0_ADMIN_CENTER_WINDOWS','--onedir','Inno Setup','_internal', 'YOUTUBE_VIDEO_DOWNLOADER_13_0_SETUP.exe'):
            with self.subTest(item=item): self.assertIn(item,workflow)

    def test_no_owner_key_in_repo(self):
        self.assertFalse(list(ROOT.rglob('*.pem')))

if __name__=='__main__': unittest.main()
