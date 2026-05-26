"""Cert scope parser — extract material groups from ISCC EU cert PDFs.

Audit context: DEL-CRW-2025-2 red-team round 1 failure mode F0-F.  The
RTFO submission frames DEV-P100 as ELT-derived; that framing requires
each upstream ISCC EU cert to list "End-of-life tyres (ELT)" (or its
ISCC-EU equivalent label) in the cert's scope block.  Before this
parser, the only way to verify scope was to open every PDF by eye —
not an auditable workflow.

The parser is intentionally **conservative**:

    * It does not invent material groups not on its known-vocab list.
    * It returns *empty* (not partial) on parse failure, with the raw
      text preserved in ``scope_raw`` so an operator can re-attempt.
    * It does not modify the cert PDF or the DB.  Persistence is the
      caller's job (typically ``scripts/backfill_cert_scope.py``).

The parser is also intentionally **pdf-text-only**: it does not OCR
images, so a scanned cert PDF will yield an empty result with
``scope_raw == ""``.  All 7 in-scope certs (DEL-CRW-2025-2 audit Tier
A) are vector PDFs from the ISCC platform, so this constraint does
not bite the current consignment.

Returns:
    ParsedScope dataclass with:
        - raw: the substring of the PDF text identified as scope
          block.  May be empty if no scope block was found.
        - material_groups: list of canonical names lifted from raw.
          May be empty if raw was empty or no known group matched.
        - scheme_detected: ISCC scheme parsed from PDF header
          ("ISCC EU", "ISCC PLUS", "ISCC CORSIA") or None on no
          match.  Independent of DB scheme value — caller compares
          and surfaces mismatch as disclosure (audit F0-H).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader


# Known ISCC EU / RTFO material category labels.  Keep canonical form
# on the left; right side is the regex that catches common phrasings
# (case-insensitive, word-boundary aware).  Order matters: longer /
# more specific patterns first so they win over shorter ones.
_KNOWN_GROUPS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "End-of-life tyres (ELT)",
        re.compile(
            r"\b(?:end[\s\-]of[\s\-]life\s+tyres?|elt)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Used cooking oil (UCO)",
        re.compile(
            r"\b(?:used\s+cooking\s+oil|uco)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Animal fat category 1",
        re.compile(
            r"\banimal\s+fat[s]?\s*(?:cat(?:egory|\.)?\s*)?(?:1|i)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Animal fat category 2",
        re.compile(
            r"\banimal\s+fat[s]?\s*(?:cat(?:egory|\.)?\s*)?(?:2|ii)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Animal fat category 3",
        re.compile(
            r"\banimal\s+fat[s]?\s*(?:cat(?:egory|\.)?\s*)?(?:3|iii)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Tall oil",
        re.compile(r"\btall\s+oil\b", re.IGNORECASE),
    ),
    (
        "POME (Palm oil mill effluent)",
        re.compile(r"\b(?:pome|palm\s+oil\s+mill\s+effluent)\b", re.IGNORECASE),
    ),
    (
        "Forestry residues",
        re.compile(r"\bforestry\s+residues?\b", re.IGNORECASE),
    ),
    (
        "Agricultural residues",
        re.compile(r"\bagricultural\s+residues?\b", re.IGNORECASE),
    ),
    (
        "Lignocellulosic material",
        re.compile(r"\blignocellulosic\b", re.IGNORECASE),
    ),
    (
        "Mixed waste plastics",
        re.compile(
            r"\b(?:mixed\s+waste\s+plastics?|waste\s+plastics?)\b",
            re.IGNORECASE,
        ),
    ),
)


# Header patterns that mark the start of the scope block.  Real-world
# certs phrase this differently across versions and across schemes:
#
#   ISCC EU:
#     "Scope of certification"
#     "Add-ons / Scope"
#     "Material(s) / product(s) categories"
#     "Type of feedstock / fuel"
#
#   ISCC PLUS:
#     "The scope of the certificate includes the following chain of
#      custody options"
#     "Sustainable materials handled by the certified site"  (Annex I
#      table header)
#     "Input material Output material Add-ons"  (table column header)
#
# The parser will accept any of these and consume text up to the next
# header-like line.
_SCOPE_HEADERS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(?:scope\s+of\s+(?:the\s+)?certif(?:icate|ication)|add[\s\-]?ons?\s*[/&]\s*scope)\s*[:\-]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"materials?\s*(?:\([s]?\))?\s*[/&]?\s*products?\s*(?:\([s]?\))?\s*categor(?:y|ies)\s*[:\-]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"type\s+of\s+(?:feedstock|raw\s+material)\s*[/&]?\s*(?:fuel)?\s*[:\-]?",
        re.IGNORECASE,
    ),
    re.compile(
        r"sustainable\s+materials?\s+handled\s+by\s+the\s+certified\s+site",
        re.IGNORECASE,
    ),
    re.compile(
        r"input\s+material\s+output\s+material",
        re.IGNORECASE,
    ),
)


# Scheme header patterns — first match wins.  ISCC PLUS detection must
# precede ISCC EU detection because the string "ISCC PLUS" contains
# "ISCC" which could otherwise be mistaken for "ISCC EU" via a looser
# regex.  Order is intentional.
_SCHEME_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ISCC PLUS", re.compile(r"\bISCC\s+PLUS\b", re.IGNORECASE)),
    ("ISCC CORSIA", re.compile(r"\bISCC\s+CORSIA\b", re.IGNORECASE)),
    ("ISCC EU", re.compile(r"\bISCC\s+EU\b", re.IGNORECASE)),
)


# Pattern that signals the END of the scope block — typically the next
# section header.  Conservative: stops on common ISCC section names.
_END_HEADERS: re.Pattern[str] = re.compile(
    r"^\s*(?:"
    r"issuing\s+(?:body|date|certification\s+body)"
    r"|valid(?:ity)?(?:\s+from)?(?:\s+to)?"
    r"|date\s+of\s+(?:audit|issue)"
    r"|certificate\s+(?:number|holder)"
    r"|holder\s+of\s+the\s+certificate"
    r"|chain\s+of\s+custody"
    r")\s*[:\-]?",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass(frozen=True)
class ParsedScope:
    """Result of parsing a cert PDF's scope block."""

    raw: str = ""
    material_groups: list[str] = field(default_factory=list)
    scheme_detected: str | None = None


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract concatenated text from all pages of the PDF.

    Returns empty string on any IO or pypdf error — the parser is
    expected to handle empty input gracefully.
    """
    try:
        reader = PdfReader(str(pdf_path))
    except Exception:  # noqa: BLE001 — pypdf raises many subtypes
        return ""

    chunks: list[str] = []
    for page in reader.pages:
        try:
            chunks.append(page.extract_text() or "")
        except Exception:  # noqa: BLE001
            chunks.append("")
    return "\n".join(chunks)


def locate_scope_block(text: str) -> str:
    """Find the scope substring inside the PDF text.

    Returns empty string if no scope header was found.  Otherwise
    returns the text from the matched header up to the next section
    header, capped at 4 KB to defend against runaway captures.
    """
    if not text:
        return ""

    for header in _SCOPE_HEADERS:
        m = header.search(text)
        if not m:
            continue
        tail = text[m.end():]
        end_m = _END_HEADERS.search(tail)
        block = tail[: end_m.start()] if end_m else tail
        block = block.strip()[:4096]
        if block:
            return block
    return ""


def parse_material_groups(scope_text: str) -> list[str]:
    """Return canonical material group names found in scope_text.

    Order preserved as in ``_KNOWN_GROUPS`` (most specific first), de-
    duplicated.  Empty list on empty input or no matches.
    """
    if not scope_text:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for canonical, pattern in _KNOWN_GROUPS:
        if pattern.search(scope_text) and canonical not in seen:
            found.append(canonical)
            seen.add(canonical)
    return found


def detect_scheme(text: str) -> str | None:
    """Return the ISCC scheme name detected in the PDF text, or None.

    The first scheme pattern to match wins.  ``_SCHEME_PATTERNS`` is
    ordered so that "ISCC PLUS" / "ISCC CORSIA" match before "ISCC EU"
    — otherwise an "ISCC EU"-looser regex would steal hits on PLUS
    certs that also mention "ISCC" in a generic sentence.
    """
    if not text:
        return None
    for canonical, pattern in _SCHEME_PATTERNS:
        if pattern.search(text):
            return canonical
    return None


def parse_cert_pdf(pdf_path: Path) -> ParsedScope:
    """End-to-end: read PDF, locate scope block, extract material groups."""
    text = extract_pdf_text(pdf_path)
    raw = locate_scope_block(text)
    groups = parse_material_groups(raw)
    scheme = detect_scheme(text)
    return ParsedScope(raw=raw, material_groups=groups, scheme_detected=scheme)
