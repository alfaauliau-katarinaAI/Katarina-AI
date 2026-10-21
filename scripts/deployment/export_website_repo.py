#!/usr/bin/env python3
"""Export the public website trees into a standalone repository layout (cleanup stage 7).

Copies only Git-tracked public site files; never Python brain, MT5, VPS or private config.
The source repository is left unchanged so the current Cloudflare Pages project keeps
deploying from it until the Owner points Pages at the new repository.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
TREES = ("website/", "functions/", "sites/", "oauth_gateway/")
FILES = {
    "scripts/update_hot_news.py": "scripts/update_hot_news.py",
    ".github/workflows/katarina-hotnews.yml": ".github/workflows/katarina-hotnews.yml",
    "docs/deployment/CLOUDFLARE_PAGES_SETUP.md": "docs/CLOUDFLARE_PAGES_SETUP.md",
    "docs/SITES_RUNTIME_MONITOR.md": "docs/SITES_RUNTIME_MONITOR.md",
    "docs/STABLE_FREE_RUNTIME_MONITOR.md": "docs/STABLE_FREE_RUNTIME_MONITOR.md",
}
README = """# Katarina AI — website

Situs publik Katarina AI, dipisah dari repo `alfaauliau-katarinaAI/Katarina-AI` (otak, MT5, riset).

| Folder | Isi |
|---|---|
| `website/` | Situs statis (Cloudflare Pages, output `website`, tanpa build) |
| `functions/` | Cloudflare Pages Functions (`/api/hot-news`) |
| `sites/runtime-monitor/` | Worker monitor runtime (diisi publisher VPS, bukan repo ini) |
| `oauth_gateway/` | Gateway OAuth Node |
| `scripts/update_hot_news.py` + workflow | Pembaruan headline bersumber terjadwal |

Asal ekspor: commit `{commit}` (lihat `EXPORT_MANIFEST.json`). Panduan Pages: `docs/CLOUDFLARE_PAGES_SETUP.md`.
Tidak ada kredensial, data broker, atau kode trading di repo ini. Live trading tetap OFF.
"""
GITIGNORE = ".dev.vars\n.dev.vars.*\nnode_modules/\n.wrangler/\n.DS_Store\n"


def tracked(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], stdout=subprocess.PIPE, check=True).stdout
    return [p for p in out.decode("utf-8", "surrogateescape").split("\0") if p]


def export(root: Path, dest: Path) -> dict:
    if dest.exists() and any(dest.iterdir()):
        raise SystemExit(f"destination not empty: {dest}")
    files = {p: p for p in tracked(root) if p.startswith(TREES)}
    files.update({src: dst for src, dst in FILES.items() if (root / src).is_file()})
    commit = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], stdout=subprocess.PIPE,
                            check=True, text=True).stdout.strip()
    manifest = {}
    for src, dst in sorted(files.items()):
        target = dest / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / src, target)
        manifest[dst] = dict(source=src, sha256=hashlib.sha256(target.read_bytes()).hexdigest())
    (dest / "README.md").write_text(README.format(commit=commit), encoding="utf-8")
    (dest / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    report = dict(source_repository="alfaauliau-katarinaAI/Katarina-AI", source_commit=commit,
                  files=manifest, live_authorized=False)
    (dest / "EXPORT_MANIFEST.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dest", required=True, type=Path, help="Empty directory for the website repository")
    parser.add_argument("--repo-root", default=str(ROOT))
    args = parser.parse_args()
    report = export(Path(args.repo_root), args.dest)
    print(f"EXPORTED_WEBSITE_REPO files={len(report['files'])} commit={report['source_commit']}")


if __name__ == "__main__":
    main()
