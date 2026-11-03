"""Portability contract for research and observer entrypoints (read-only)."""
from pathlib import Path
import subprocess
import unittest


REPO = Path(__file__).resolve().parents[2]


class WorkspacePathContractTests(unittest.TestCase):
    def test_no_retired_katarinadev_layout_in_scripts_or_source(self):
        """Cleanup B1: the VPS runtime is C:\\Katarina; C:\\KatarinaDev was retired 22 Oct."""
        tracked = subprocess.check_output(
            ["git", "-C", str(REPO), "ls-files", "scripts", "src", "katarina_pc.py"],
            text=True,
        ).splitlines()
        offenders = []
        for rel in tracked:
            p = REPO / rel
            if p.suffix.lower() not in {".py", ".ps1", ".cmd", ".bat", ".sh"}:
                continue
            txt = p.read_text(encoding="utf-8-sig", errors="replace").lower()
            if "katarinadev" in txt:
                offenders.append(rel)
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()

