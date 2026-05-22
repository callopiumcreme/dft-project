#!/usr/bin/env python3
"""Setaccia tutti i .py del progetto cercando 'ZUNIGA MARTINEZ S.A.S' (match accent/spazi tolleranti)."""
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NEEDLE_RAW = "ZUNIGA MARTINEZ S.A.S"


def norm(s: str) -> str:
    """Lowercase, strip accents, collapse whitespace/punct so 'Zúñiga Martínez S.A.S.' matches."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


needle = norm(NEEDLE_RAW)
hits = 0
files = sorted(ROOT.rglob("*.py"))
for f in files:
    if any(p in f.parts for p in ("node_modules", "site-packages", ".venv", "__pycache__")):
        continue
    try:
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        continue
    for n, line in enumerate(lines, 1):
        if needle in norm(line):
            print(f"{f.relative_to(ROOT)}:{n}: {line.strip()}")
            hits += 1

print(f"\n[{hits} match in {len(files)} file .py scansionati sotto {ROOT}]", file=sys.stderr)
sys.exit(0 if hits else 1)
