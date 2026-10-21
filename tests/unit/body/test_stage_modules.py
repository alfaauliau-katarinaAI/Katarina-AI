from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest

from katarina.body import STAGE_MODULES

ROOT = Path(__file__).resolve().parents[3]


class StageModuleNamingTests(unittest.TestCase):
    def test_mapping_matches_numbered_manifests_and_specs(self):
        self.assertEqual(sorted(STAGE_MODULES), list(range(11, 41)))
        for stage, module in STAGE_MODULES.items():
            manifest = json.loads((ROOT / f"config/stages/stage{stage:02d}.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["implementation_module"], module)
            spec = importlib.import_module(module).Component.SPEC
            self.assertEqual((spec.stage, spec.implementation_module), (stage, module))

    def test_numbered_aliases_are_removed(self):
        for stage in STAGE_MODULES:
            self.assertFalse((ROOT / f"src/katarina/body/stage{stage}.py").exists())


if __name__ == "__main__":
    unittest.main()
