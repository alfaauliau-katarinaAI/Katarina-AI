#!/usr/bin/env python3
"""Static map of which src/katarina modules are reachable from which entry points.

Read-only: parses tracked Python with ``ast`` and scans launchers/workflows as
text. Nothing is imported or executed. Categories per module:

A  reachable from a runtime/operational entry point or a workflow-invoked script
B  reachable only from tests
C  reachable only from scripts that nothing operational invokes (research etc.)
D  not reachable from any root

Edges: ``import``/``from`` statements (relative included, parent packages
implied), literal ``importlib.import_module``/``__import__`` names, string
literals naming a module or a tracked script path, unique script basenames in
string literals, and modules named in ``config/**/*.json`` from any module that
calls ``import_module`` with a non-literal argument (the body stage registry).
Dynamic names built at runtime beyond that are not seen; treat D as a candidate
list to verify, not as proof of disuse.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict, deque
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SKIP_PREFIXES = ("archive/",)
RUNTIME_ENTRIES = (
    "katarina_pc.py",
    "scripts/ai/run_contextual_market_observer.py",
    "scripts/ai/run_independent_demo_worker.py",
    "scripts/ai/publish_runtime_monitor.py",
    "scripts/ai/run_hf_archive_sync.py",
)
LAUNCHER_SUFFIXES = (".yml", ".yaml", ".bat", ".cmd", ".ps1", ".sh", ".service", ".timer", ".json")
LAUNCHER_PREFIXES = (".github/", "scripts/", "ops/", "config/", "sites/")
BRAIN_CAPABILITIES = (  # former versioned "brain" modules, renamed in cleanup stage 3
    "katarina.intelligence.cognition.unified_brain",
    "katarina.intelligence.cognition.adaptive_observation",
    "katarina.intelligence.cognition.market_decision",
    "katarina.intelligence.perception.screening",
    "katarina.intelligence.cognition.observer",
)
CATEGORY_TITLES = {
    "A": "dipakai runtime/operasional atau workflow",
    "B": "hanya dipakai tests",
    "C": "hanya dipakai script non-operasional (riset dll.)",
    "D": "tidak terjangkau dari root mana pun",
}
_MODULE_RE = re.compile(r"\bkatarina(?:\.[A-Za-z_][A-Za-z0-9_]*)+")


def tracked(root: Path) -> list[str]:
    out = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], stdout=subprocess.PIPE, check=True).stdout
    return [p for p in out.decode("utf-8", "surrogateescape").split("\0")
            if p and not p.startswith(SKIP_PREFIXES) and (root / p).is_file()]


def module_name(path: str) -> str:
    parts = list(PurePosixPath(path).with_suffix("").parts)
    if parts[0] == "src":
        parts = parts[1:]
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


class Graph:
    def __init__(self, root: Path, files: list[str]):
        self.root = root
        self.py = sorted(f for f in files if f.endswith(".py"))
        self.by_module = {module_name(f): f for f in self.py}
        names = defaultdict(list)
        for f in self.py:
            names[PurePosixPath(f).name].append(f)
        self.unique_basenames = {n: v[0] for n, v in names.items() if len(v) == 1}
        self.config_modules = self._config_modules(files)
        self.edges = {f: self._edges(f) for f in self.py}

    def _config_modules(self, files):
        found = set()
        for f in files:
            if f.startswith("config/") and f.endswith(".json"):
                text = (self.root / f).read_text(encoding="utf-8", errors="ignore")
                found.update(self._resolve(m) for m in _MODULE_RE.findall(text))
        found.discard(None)
        return found

    def _resolve(self, name):
        """Longest module prefix of a dotted name, plus its parent packages."""
        parts = name.split(".")
        for end in range(len(parts), 0, -1):
            candidate = ".".join(parts[:end])
            if candidate in self.by_module:
                return self.by_module[candidate]
        return None

    def _with_parents(self, target):
        out = {target}
        parts = module_name(target).split(".")
        for end in range(1, len(parts)):
            parent = self.by_module.get(".".join(parts[:end]))
            if parent:
                out.add(parent)
        return out

    def _edges(self, path):
        try:
            tree = ast.parse((self.root / path).read_bytes(), filename=path)
        except SyntaxError:
            return set()
        own = module_name(path).split(".")
        package = own if path.endswith("__init__.py") else own[:-1]
        here = PurePosixPath(path).parent
        names, dynamic = [], False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    keep = package[:len(package) - node.level + 1]
                    base = ".".join(keep + ([base] if base else []))
                names.append(base)
                names += [f"{base}.{a.name}" if base else a.name for a in node.names]
            elif isinstance(node, ast.Call) and getattr(node.func, "attr", getattr(node.func, "id", "")) in ("import_module", "__import__"):
                arg = node.args[0] if node.args else None
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    names.append(arg.value)
                else:
                    dynamic = True
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value
                names += _MODULE_RE.findall(value)
                for ref in re.findall(r"[A-Za-z0-9_./\\-]+\.py\b", value):
                    ref = ref.replace("\\", "/").lstrip("./")
                    if ref in self.by_module.values() or ref.startswith("src/"):
                        names.append(module_name(ref))
                    elif ref in self.unique_basenames:
                        names.append(module_name(self.unique_basenames[ref]))
        out = set()
        for name in names:
            target = self._resolve(name)
            if target is None and name and "." not in name:
                sibling = str(here / f"{name}.py")
                # Scripts and tests put script folders on sys.path and import by bare name.
                target = sibling if sibling in self.by_module.values() else self.unique_basenames.get(f"{name}.py")
            if target and target != path:
                out |= self._with_parents(target)
        if dynamic and path.startswith("src/"):
            for target in self.config_modules:
                out |= self._with_parents(target)
        out.discard(path)
        return out

    def reach(self, roots):
        seen, queue = set(roots), deque(roots)
        while queue:
            for nxt in self.edges.get(queue.popleft(), ()):
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        return seen


def launcher_roots(root: Path, files: list[str], graph: Graph):
    """Python files a non-Python launcher names by repo path (either separator)."""
    workflow, ops = set(), set()
    targets = [f for f in graph.py if not f.startswith(("tests/", "src/"))]
    for f in files:
        if not f.endswith(LAUNCHER_SUFFIXES) or not (f.startswith(LAUNCHER_PREFIXES) or "/" not in f):
            continue
        if f == "ops/deployment/release-manifest.json":
            continue
        text = (root / f).read_text(encoding="utf-8", errors="ignore").replace("\\", "/")
        bucket = workflow if f.startswith(".github/workflows/") else ops
        for target in targets:
            if target in text or ("/" not in target and re.search(rf"(?<![\w/]){re.escape(target)}", text)):
                bucket.add(target)
        if f.startswith(".github/workflows/"):
            for name in _MODULE_RE.findall(text) + re.findall(r"\bscripts(?:\.\w+)+", text):
                target = graph._resolve(name)
                if target:
                    bucket.add(target)
    return workflow, ops


def build(root: Path):
    files = tracked(root)
    graph = Graph(root, files)
    workflow, ops = launcher_roots(root, files, graph)
    runtime = {f for f in RUNTIME_ENTRIES if f in graph.py}
    tests = {f for f in graph.py if f.startswith("tests/")}
    research = {f for f in graph.py if f.startswith("scripts/research/")}
    scripts = {f for f in graph.py if not f.startswith(("src/", "tests/"))} - runtime - workflow - ops - research
    reached = {name: graph.reach(sorted(group)) for name, group in (
        ("runtime", runtime), ("ops", ops), ("workflow", workflow),
        ("research", research), ("scripts", scripts), ("tests", tests))}
    importers = defaultdict(set)
    for src, dsts in graph.edges.items():
        for dst in dsts:
            importers[dst].add(src)
    modules = {}
    for f in graph.py:
        if not f.startswith("src/katarina/"):
            continue
        via = [k for k, v in reached.items() if f in v]
        if {"runtime", "ops", "workflow"} & set(via):
            category = "A"
        elif {"research", "scripts"} & set(via):
            category = "C"
        elif "tests" in via:
            category = "B"
        else:
            category = "D"
        direct = sorted(importers[f])
        modules[module_name(f)] = dict(
            path=f, category=category, via=via,
            src_importers=[module_name(p) for p in direct if p.startswith("src/")],
            other_importers=[p for p in direct if not p.startswith("src/")])
    return dict(roots=dict(runtime=sorted(runtime), ops=sorted(ops), workflow=sorted(workflow)),
                modules=modules)


def render(report) -> str:
    modules = report["modules"]
    counts = defaultdict(int)
    for row in modules.values():
        counts[row["category"]] += 1
    lines = [
        "# Peta modul runtime `src/katarina`",
        "",
        "Dibuat otomatis oleh `scripts/governance/runtime_import_map.py` (analisis statis, tanpa",
        "menjalankan kode). Jangan disunting manual; jalankan ulang:",
        "",
        "```bash",
        "python scripts/governance/runtime_import_map.py --output docs/maintenance/RUNTIME_MODULE_MAP.md",
        "```",
        "",
        "Kolom *via* menyebut kelompok root yang menjangkau modul: `runtime` (entry point utama),",
        "`ops` (dipanggil launcher .bat/.ps1/.sh/service/config), `workflow` (dipanggil",
        "`.github/workflows`), `research` (`scripts/research`), `scripts` (script lain yang tidak",
        "dipanggil apa pun), `tests`. Import dinamis di luar registry stage tidak terlihat, jadi",
        "kategori D adalah kandidat untuk dicek manual, bukan bukti tidak terpakai.",
        "",
        "## Ringkasan",
        "",
        "| Kategori | Arti | Jumlah |",
        "|---|---|---|",
    ]
    lines += [f"| {c} | {CATEGORY_TITLES[c]} | {counts[c]} |" for c in "ABCD"]
    ci_only = sum(1 for r in modules.values() if r["category"] == "A" and not {"runtime", "ops"} & set(r["via"]))
    lines += ["", f"Total modul: {len(modules)}. Dari kategori A, {ci_only} hanya terjangkau lewat "
              "workflow (CI/riset terjadwal), bukan entry point runtime atau launcher.",
              "", "## Root yang dipakai", ""]
    for name, roots in report["roots"].items():
        lines.append(f"- **{name}** ({len(roots)}): " + ", ".join(f"`{r}`" for r in roots))
    lines += ["", "## Otak canonical dan bekas otak berversi", "",
              "| Modul | Kategori | via | Diimpor modul src |", "|---|---|---|---|"]
    for name in BRAIN_CAPABILITIES:
        row = modules.get(name)
        if row:
            src = ", ".join(f"`{m}`" for m in row["src_importers"]) or "—"
            lines.append(f"| `{name}` | {row['category']} | {', '.join(row['via']) or '—'} | {src} |")
    for category in "ABCD":
        rows = sorted((n, r) for n, r in modules.items() if r["category"] == category)
        lines += ["", f"## {category} — {CATEGORY_TITLES[category]} ({len(rows)})", "",
                  "| Modul | via | Importir src | Importir lain |", "|---|---|---|---|"]
        for name, row in rows:
            lines.append(f"| `{name}` | {', '.join(row['via']) or '—'} | "
                         f"{len(row['src_importers'])} | {len(row['other_importers'])} |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--output", help="Markdown report path")
    parser.add_argument("--json", help="Optional JSON report path")
    args = parser.parse_args()
    report = build(Path(args.repo_root).resolve())
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(render(report), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    counts = defaultdict(int)
    for row in report["modules"].values():
        counts[row["category"]] += 1
    print("RUNTIME_IMPORT_MAP " + " ".join(f"{c}={counts[c]}" for c in "ABCD"))


if __name__ == "__main__":
    main()
