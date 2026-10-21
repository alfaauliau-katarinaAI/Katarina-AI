import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("export_website_repo", ROOT / "scripts/deployment/export_website_repo.py")
EXPORT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPORT)


class ExportWebsiteRepoTest(unittest.TestCase):
    def test_exports_only_public_site_files_with_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "site"
            report = EXPORT.export(ROOT, dest)
            self.assertTrue((dest / "website/index.html").is_file())
            self.assertTrue((dest / "functions/api/hot-news.js").is_file())
            self.assertFalse(any(name.startswith(("src/", "mt5/", "config/", "ops/")) for name in report["files"]))
            manifest = json.loads((dest / "EXPORT_MANIFEST.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["source_commit"], report["source_commit"])
            self.assertFalse(manifest["live_authorized"])
            with self.assertRaises(SystemExit):
                EXPORT.export(ROOT, dest)


if __name__ == "__main__":
    unittest.main()
