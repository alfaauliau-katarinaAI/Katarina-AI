"""Connectivity contract: every katarina module imports and every script import resolves (read-only)."""
from pathlib import Path
import ast
import json
import os
import subprocess
import sys
import unittest


REPO = Path(__file__).resolve().parents[2]

# Runs in a fresh interpreter so module side effects (sys.modules aliases, warnings)
# never leak into the rest of the static suite.
_IMPORT_ALL = r"""
import importlib, json, pkgutil, warnings
warnings.simplefilter("ignore")
import katarina
failed = {}
count = 0
for info in pkgutil.walk_packages(katarina.__path__, "katarina."):
    count += 1
    try:
        importlib.import_module(info.name)
    except Exception as exc:
        failed[info.name] = f"{type(exc).__name__}: {exc}"
print(json.dumps({"count": count, "failed": failed}))
"""


def _run_isolated(code):
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"))
    out = subprocess.run(
        [sys.executable, "-c", code],
        cwd=REPO, env=env, capture_output=True, text=True, timeout=300, check=True,
    )
    return json.loads(out.stdout.strip().splitlines()[-1])


def _katarina_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8-sig"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "katarina":
                    yield alias.name, None
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            if node.module.split(".")[0] == "katarina":
                for alias in node.names:
                    yield node.module, alias.name


class ModuleConnectivityTests(unittest.TestCase):
    def test_every_katarina_module_imports(self):
        result = _run_isolated(_IMPORT_ALL)
        self.assertGreater(result["count"], 0)
        self.assertEqual(result["failed"], {})

    def test_script_imports_resolve(self):
        tracked = subprocess.check_output(
            ["git", "-C", str(REPO), "ls-files", "scripts", "katarina_pc.py"],
            text=True,
        ).splitlines()
        wanted = sorted({
            (module, name)
            for rel in tracked if rel.endswith(".py")
            for module, name in _katarina_imports(REPO / rel)
        })
        check = (
            "import importlib, importlib.util, json, warnings\n"
            "warnings.simplefilter('ignore')\n"
            f"wanted = {wanted!r}\n"
            "missing = []\n"
            "for module, name in wanted:\n"
            "    try:\n"
            "        mod = importlib.import_module(module)\n"
            "    except Exception as exc:\n"
            "        missing.append(f'{module}: {type(exc).__name__}')\n"
            "        continue\n"
            "    if not name or name == '*' or hasattr(mod, name):\n"
            "        continue\n"
            "    try:\n"
            "        found = importlib.util.find_spec(f'{module}.{name}') is not None\n"
            "    except ModuleNotFoundError:\n"
            "        found = False\n"
            "    if not found:\n"
            "        missing.append(f'{module}.{name}')\n"
            "print(json.dumps({'count': len(wanted), 'failed': sorted(set(missing))}))\n"
        )
        result = _run_isolated(check)
        self.assertGreater(result["count"], 0)
        self.assertEqual(result["failed"], [])


if __name__ == "__main__":
    unittest.main()
