"""Index stable reason codes: code -> area, severity, source file:line, tests (read-only).

Static AST scan of ``src/katarina`` and ``scripts``. A reason code is an UPPER_SNAKE string
literal (at least one underscore) used where Katarina reports a failure or block:

- argument of ``raise X("CODE")``;
- value of a ``reason``/``error``/``status``/``reason_code``/``blocker`` keyword or dict key;
- element of a ``blocking_reasons``/``reasons`` tuple/list keyword or dict value.

Severity follows the area (documented in docs/maintenance/REASON_CODE_INDEX.md):
P0 = risk, execution, broker clock/identity; P1 = observer/ledger/data health/persistence;
P2 = research, lab, news, monitoring, tooling. Protocol codes from
``protocol/reason_codes_v1.json`` are listed as-is; their meanings are frozen.

Usage:
  python scripts/governance/reason_code_index.py --output docs/maintenance/REASON_CODE_INDEX.md
  python scripts/governance/reason_code_index.py --find CLOCK_BROKER_IDENTITY_MISSING
No broker, network or runtime state is touched.
"""
from __future__ import annotations

import argparse
import ast
from collections import defaultdict
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CODE_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+$")
REASON_KEYS = {"reason", "error", "status", "reason_code", "blocker", "error_code", "code"}
REASON_LIST_KEYS = {"blocking_reasons", "reasons", "blockers", "issues"}
# Not failure codes: generic status words and enum-like labels that carry no error meaning.
NEUTRAL = {"LIVE_OFF", "READ_ONLY", "NOT_APPLICABLE"}
P0_PREFIXES = ("src/katarina/engines/risk", "src/katarina/engines/demo_execution", "src/katarina/engines/execution",
               "src/katarina/engines/account_risk", "src/katarina/engines/broker_risk", "src/katarina/engines/manual_risk",
               "src/katarina/engines/adaptive_risk", "src/katarina/intelligence/broker/", "src/katarina/adapters/",
               "src/katarina/governance/", "src/katarina/policies/")
P1_PREFIXES = ("src/katarina/intelligence/cognition/", "src/katarina/intelligence/operations/",
               "src/katarina/persistence/", "src/katarina/memory/", "src/katarina/core/", "src/katarina/health/",
               "src/katarina/validation/", "src/katarina/intelligence/demo/", "src/katarina/intelligence/shadow/",
               "src/katarina/engines/", "scripts/ai/")


def severity(path: str) -> str:
    if path.startswith(P0_PREFIXES):
        return "P0"
    if path.startswith(P1_PREFIXES):
        return "P1"
    return "P2"


def area(path: str) -> str:
    parts = Path(path).with_suffix("").parts
    if parts[0] == "src":
        return ".".join(parts[2:4]) if len(parts) > 3 else parts[-1]
    return "/".join(parts[:2])


def tracked(prefixes) -> list[str]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", *prefixes], stdout=subprocess.PIPE,
                         check=True, text=True).stdout
    return [p for p in out.splitlines() if p.endswith(".py") and (ROOT / p).is_file()]


PREFIX_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_$")


def _dynamic_prefix(node) -> str | None:
    """'PREFIX_' + x or f'PREFIX_{x}' -> 'PREFIX_*' (a code family such as SHADOW_EVALUATION_FAILED_<Type>)."""
    head = None
    if isinstance(node, ast.JoinedStr) and node.values:
        head = node.values[0]
    elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        head = node.left
    if isinstance(head, ast.Constant) and isinstance(head.value, str) and PREFIX_RE.match(head.value):
        return head.value + "*"
    return None


def _codes(node) -> list[tuple[str, int]]:
    if isinstance(node, ast.Constant) and isinstance(node.value, str) and CODE_RE.match(node.value) \
            and node.value not in NEUTRAL:
        return [(node.value, node.lineno)]
    prefix = _dynamic_prefix(node)
    if prefix:
        return [(prefix, node.lineno)]
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return [c for item in node.elts for c in _codes(item)]
    return []


def scan_file(path: str) -> list[tuple[str, int, str]]:
    try:
        tree = ast.parse((ROOT / path).read_text(encoding="utf-8-sig"))
    except SyntaxError:
        return []
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and isinstance(node.exc, ast.Call):
            for arg in node.exc.args[:1]:
                found += [(c, line, "raise") for c, line in _codes(arg)]
        elif isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg in REASON_KEYS or kw.arg in REASON_LIST_KEYS:
                    found += [(c, line, kw.arg) for c, line in _codes(kw.value)]
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if name in {"rejected", "_reject", "reject", "block", "_block", "fail", "_fail", "_finding", "Finding"}:
                for arg in node.args[:1]:
                    found += [(c, line, name) for c, line in _codes(arg)]
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value in REASON_KEYS | REASON_LIST_KEYS:
                    found += [(c, line, str(key.value)) for c, line in _codes(value)]
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                key = getattr(target, "attr", None) or getattr(target, "id", None)
                if isinstance(target, ast.Subscript) and isinstance(target.slice, ast.Constant):
                    key = target.slice.value
                if key in REASON_KEYS:
                    found += [(c, line, str(key)) for c, line in _codes(node.value)]
        # A code family built anywhere ("SHADOW_EVALUATION_FAILED_" + type(ex).__name__).
        if isinstance(node, (ast.BinOp, ast.JoinedStr)):
            prefix = _dynamic_prefix(node)
            if prefix:
                found.append((prefix, node.lineno, "dynamic"))
    return found


def build_index() -> dict:
    sources = tracked(["src/katarina", "scripts"])
    tests = tracked(["tests"])
    test_text = {t: (ROOT / t).read_text(encoding="utf-8", errors="replace") for t in tests}
    sites = defaultdict(set)
    for path in sources:
        if path == "scripts/governance/reason_code_index.py":
            continue
        for code, line, kind in scan_file(path):
            sites[code].add((path, line, kind))
    index = {}
    for code in sorted(sites):
        needle = code[:-2] if code.endswith("_*") else code
        covered = sorted(t for t, text in test_text.items() if needle in text)
        locations = sorted(sites[code])
        index[code] = {
            "severity": min(severity(p) for p, _, _ in locations),
            "areas": sorted({area(p) for p, _, _ in locations}),
            "sites": [f"{p}:{line}" for p, line, _ in locations],
            "tests": covered,
        }
    protocol = json.loads((ROOT / "protocol/reason_codes_v1.json").read_text(encoding="utf-8"))
    return {"codes": index, "protocol": protocol["reason_codes"], "protocol_rule": protocol["rule"]}


def render(data: dict) -> str:
    codes = data["codes"]
    by_sev = defaultdict(int)
    for row in codes.values():
        by_sev[row["severity"]] += 1
    untested = [c for c, r in codes.items() if not r["tests"]]
    lines = [
        "# Indeks reason code Katarina",
        "",
        "Dibuat ulang dengan `python scripts/governance/reason_code_index.py --output docs/maintenance/REASON_CODE_INDEX.md`",
        "(analisis statis, tanpa broker/jaringan). Cari satu kode: `python scripts/governance/reason_code_index.py --find KODE`.",
        "",
        "## Cara menelusuri error",
        "",
        "1. Ambil kode dari log/laporan (`reason`, `error`, `status`, `blocking_reasons`, pesan exception).",
        "2. Cari kode di tabel ini atau dengan `--find`: kolom **Sumber** menunjuk `file:line` yang menghasilkan kode,",
        "   kolom **Tes** menunjuk tes yang memeriksanya. Kode berakhiran `_*` adalah prefiks dinamis (mis. `SHADOW_EVALUATION_FAILED_<Tipe>`).",
        "3. Perbaikan wajib menambah/memperbarui tes yang menyebut kode itu, lalu dicatat di `docs/REPAIR_HISTORY.md` (ID temuan, commit, tes).",
        "",
        "Severity mengikuti area sumber: **P0** = risk, eksekusi, broker/jam/identitas, adapter, governance;",
        "**P1** = observer/kognisi, operasi Tahap 0, persistence/memory, demo/shadow, script runtime; **P2** = riset, lab, berita, monitoring, tooling.",
        "Pesan exception mentah tidak dicatat (hanya kode/tipe) agar kredensial tidak bocor.",
        "",
        f"Ringkasan: {len(codes)} kode — P0 {by_sev['P0']}, P1 {by_sev['P1']}, P2 {by_sev['P2']}; "
        f"{len(codes) - len(untested)} disebut di tes, {len(untested)} belum.",
        "",
        "| Kode | Sev | Area | Sumber | Tes |",
        "|---|---|---|---|---|",
    ]
    for code, row in sorted(codes.items(), key=lambda kv: (kv[1]["severity"], kv[0])):
        sites = "<br>".join(f"`{s}`" for s in row["sites"][:4]) + (f" (+{len(row['sites']) - 4})" if len(row["sites"]) > 4 else "")
        tests = "<br>".join(f"`{t}`" for t in row["tests"][:3]) + (f" (+{len(row['tests']) - 3})" if len(row["tests"]) > 3 else "")
        lines.append(f"| `{code}` | {row['severity']} | {', '.join(row['areas'])} | {sites} | {tests or '—'} |")
    lines += ["", "## Kode protokol (beku)", "", data["protocol_rule"], "",
              "| Nomor | Kode |", "|---|---|"]
    lines += [f"| {k} | `{v}` |" for k, v in sorted(data["protocol"].items(), key=lambda kv: int(kv[0]))]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--find")
    args = parser.parse_args(argv)
    data = build_index()
    if args.find:
        code = args.find.strip()
        matches = {c: r for c, r in data["codes"].items()
                   if c == code or (c.endswith("_*") and code.startswith(c[:-1]))}
        proto = [k for k, v in data["protocol"].items() if v == code]
        if not matches and not proto:
            print(json.dumps({"code": code, "status": "REASON_CODE_NOT_FOUND"}))
            return 1
        print(json.dumps({"code": code, "matches": matches, "protocol_number": proto}, indent=2))
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(data), encoding="utf-8")
    codes = data["codes"]
    print(f"REASON_CODE_INDEX codes={len(codes)} untested={sum(1 for r in codes.values() if not r['tests'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
