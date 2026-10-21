import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("runtime_import_map", ROOT / "scripts/governance/runtime_import_map.py")
MAP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAP)


class RuntimeImportMapTest(unittest.TestCase):
    def build(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, text in files.items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text(text, encoding="utf-8")
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            return MAP.build(root)["modules"]

    def test_categories_follow_reachability(self):
        modules = self.build({
            "src/katarina/__init__.py": "",
            "src/katarina/live.py": "from . import helper\n",
            "src/katarina/helper.py": "",
            "src/katarina/lab.py": "",
            "src/katarina/tested.py": "",
            "src/katarina/orphan.py": "",
            "scripts/ai/run_contextual_market_observer.py": "from katarina.live import x\n",
            "scripts/research/study.py": "import katarina.lab\n",
            "tests/test_tested.py": "from katarina import tested\n",
        })
        self.assertEqual(modules["katarina.live"]["category"], "A")
        self.assertEqual(modules["katarina.helper"]["category"], "A")
        self.assertEqual(modules["katarina.lab"]["category"], "C")
        self.assertEqual(modules["katarina.tested"]["category"], "B")
        self.assertEqual(modules["katarina.orphan"]["category"], "D")

    def test_launcher_and_config_registry_edges(self):
        modules = self.build({
            "src/katarina/__init__.py": "",
            "src/katarina/registry.py": "import importlib\ndef load(name):\n    return importlib.import_module(name)\n",
            "src/katarina/stage11.py": "",
            "config/stages/stage11.json": '{"implementation_module": "katarina.stage11"}',
            "scripts/body/audit.py": "from katarina import registry\n",
            "START.bat": "python scripts\\body\\audit.py\n",
        })
        self.assertEqual(modules["katarina.stage11"]["category"], "A")
        self.assertIn("ops", modules["katarina.stage11"]["via"])


if __name__ == "__main__":
    unittest.main()
