"""No desktop window needed: check actual title-bar implementation."""
import ast
import unittest
from pathlib import Path


class TitleBarTests(unittest.TestCase):
    def test_windows_title_has_no_version(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / "gui.py").read_text(encoding="utf-8"))
        window = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "UltraDownloader")
        init = next(node for node in window.body if isinstance(node, ast.FunctionDef) and node.name == "__init__")
        titles = [node for node in ast.walk(init) if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Attribute) and node.func.attr == "title"]
        self.assertEqual(len(titles), 1)
        self.assertEqual(len(titles[0].args), 1)
        self.assertIsInstance(titles[0].args[0], ast.Name)
        self.assertEqual(titles[0].args[0].id, "APP_TITLE")

    def test_edition_banner_is_in_app(self):
        source = (Path(__file__).resolve().parents[1] / "gui.py").read_text(encoding="utf-8")
        self.assertIn('"AUTO UPDATE CENTER 13.0"', source)

if __name__ == "__main__":
    unittest.main()
