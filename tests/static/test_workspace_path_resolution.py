"""Portability contract for research and observer entrypoints (read-only)."""
from pathlib import Path
import subprocess
import unittest


REPO = Path(__file__).resolve().parents[2]
_LEGACY = "github" + "-main"
_OLD_RESEARCH = "indicator" + "-research"


class WorkspacePathContractTests(unittest.TestCase):
    def test_no_obsolete_checkout_in_active_scripts(self):
        tracked = subprocess.check_output(
            ["git", "-C", str(REPO), "ls-files", "scripts"],
            text=True,
        ).splitlines()
        offenders = []
        for rel in tracked:
            p = REPO / rel
            if p.suffix.lower() not in {".py", ".ps1", ".cmd", ".bat", ".sh"}:
                continue
            txt = p.read_text(encoding="utf-8-sig", errors="replace").lower()
            if "katarinadev" in txt and (_LEGACY in txt or _OLD_RESEARCH in txt):
                offenders.append(rel)
        self.assertEqual(offenders, [])

    def test_windows_readonly_launcher_uses_its_location(self):
        launcher = (REPO / "scripts" / "ai" / "RUN_READONLY_DECISIONS.cmd").read_text()
        self.assertIn('for %%I in ("%~dp0..\\..")', launcher)
        self.assertIn('%KATARINA_REPO%\\scripts\\ai\\run_readonly_decisions.py', launcher)
        self.assertIn("exit /b %ERRORLEVEL%", launcher)


if __name__ == "__main__":
    unittest.main()

