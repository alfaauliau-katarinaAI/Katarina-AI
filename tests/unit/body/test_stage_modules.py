from __future__ import annotations

import importlib
import json
from pathlib import Path
import unittest
import warnings

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

    def test_deprecated_numbered_alias_is_the_same_module(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            alias = importlib.import_module("katarina.body.stage16")
        self.assertIs(alias, importlib.import_module(STAGE_MODULES[16]))
        self.assertTrue(any(issubclass(w.category, DeprecationWarning) for w in caught))


if __name__ == "__main__":
    unittest.main()
