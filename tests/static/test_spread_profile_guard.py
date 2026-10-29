"""Static guard ensuring no module in src/katarina or scripts imports spread_profile except its CLI script."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


class SpreadProfileStaticGuardTests(unittest.TestCase):
    def test_no_importer_of_spread_profile_except_cli(self):
        allowed_importer = REPO_ROOT / "scripts" / "research" / "spread_profile.py"

        violators = []
        target_dirs = [REPO_ROOT / "src" / "katarina", REPO_ROOT / "scripts"]

        for target_dir in target_dirs:
            for py_file in target_dir.rglob("*.py"):
                if py_file.resolve() == allowed_importer.resolve():
                    continue

                source = py_file.read_text(encoding="utf-8")
                try:
                    tree = ast.parse(source, filename=str(py_file))
                except SyntaxError:
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if "spread_profile" in alias.name:
                                violators.append((str(py_file.relative_to(REPO_ROOT)), alias.name))
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ""
                        if "spread_profile" in module:
                            violators.append((str(py_file.relative_to(REPO_ROOT)), module))
                        for alias in node.names:
                            if alias.name == "spread_profile" or alias.name == "build_spread_profile":
                                violators.append((str(py_file.relative_to(REPO_ROOT)), f"{module}.{alias.name}"))

        self.assertEqual(violators, [], f"Forbidden importers of spread_profile found: {violators}")


if __name__ == "__main__":
    unittest.main()
