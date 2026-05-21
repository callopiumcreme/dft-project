"""Convert supplier contract docx files to PDF for RTFO bundle.

Pipeline: mammoth (docx → HTML) → weasyprint (HTML → PDF).
Pure-Python, no LibreOffice/Office dependency.

Sources (7 contracts):
- /tmp/contracts_src/*.docx              — 3 signed originals (Esenttia, Biowaste, Litoplas)
- deliverables/contracts_2025/*.docx     — 4 generated drafts (Bolder, Efficien, KalTire, Pyrcom)

Output: deliverables/RTFO-310825/03_supplier_evidence/contracts/<filename>.pdf
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import mammoth
from weasyprint import HTML

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "deliverables" / "RTFO-310825" / "03_supplier_evidence" / "contracts"

SOURCES = [
    Path("/tmp/contracts_src/Neumaticos-Esenttia 2025.docx"),
    Path("/tmp/contracts_src/Neumaticos Biowaste 2025.docx"),
    Path("/tmp/contracts_src/Neumaticos-litoplast_2025.docx"),
    REPO_ROOT / "deliverables/contracts_2025/Tyres-Bolder_Industries_2025.docx",
    REPO_ROOT / "deliverables/contracts_2025/Tyres-Efficien_Technology_2025.docx",
    REPO_ROOT / "deliverables/contracts_2025/Tyres-Kal_Tire_Recycling_Chile_2025.docx",
    REPO_ROOT / "deliverables/contracts_2025/Neumaticos-Pyrcom_2025.docx",
]

PDF_CSS = """
@page {
    size: A4;
    margin: 18mm 20mm;
    @bottom-left {
        content: "OisteBio GmbH · supplier contract · RTFO-310825";
        font-family: "Helvetica", "Arial", sans-serif;
        font-size: 8pt;
        color: #555;
    }
    @bottom-right {
        content: "Page " counter(page) " of " counter(pages);
        font-family: "Helvetica", "Arial", sans-serif;
        font-size: 8pt;
        color: #555;
    }
}
html, body {
    font-family: "Helvetica", "Arial", sans-serif;
    font-size: 10pt;
    line-height: 1.45;
    color: #111;
}
h1, h2, h3 { font-weight: bold; }
h1 { font-size: 13pt; margin: 8pt 0 6pt 0; }
h2 { font-size: 11pt; margin: 8pt 0 4pt 0; text-transform: uppercase; }
p  { margin: 0 0 6pt 0; }
table { width: 100%; border-collapse: collapse; margin: 4pt 0 8pt 0; }
table td, table th { padding: 3pt 6pt; vertical-align: top; }
strong { font-weight: bold; }
"""


def docx_to_html(docx_path: Path) -> str:
    with open(docx_path, "rb") as fh:
        result = mammoth.convert_to_html(fh)
    return result.value


def render_pdf(docx_path: Path, out_pdf: Path) -> None:
    html_body = docx_to_html(docx_path)
    full_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{docx_path.stem}</title>
<style>{PDF_CSS}</style>
</head>
<body>
{html_body}
</body>
</html>"""
    HTML(string=full_html).write_pdf(target=str(out_pdf))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for src in SOURCES:
        if not src.exists():
            print(f"MISSING: {src}")
            continue
        out_pdf = OUT_DIR / f"{src.stem}.pdf"
        render_pdf(src, out_pdf)
        sha = hashlib.sha256(out_pdf.read_bytes()).hexdigest()
        size_kb = out_pdf.stat().st_size / 1024
        print(f"OK {out_pdf.name}  {size_kb:.1f} KB  sha={sha[:16]}...")


if __name__ == "__main__":
    main()
