#!/usr/bin/env python3
"""Post-sprint smoke test for chain-of-custody UI (consignment c-1 / DEL-CRW-2025-2).

Mints a short-TTL admin JWT against the local landing JWT_SECRET, drops it into
a headless Chromium session as the ``dft_session`` cookie, and walks the
chain-of-custody surfaces that the E8 sprint touched:

  - /app/logistics                 — index list (consignment table)
  - /app/logistics/1               — consignment detail (chain summary,
                                     production links, PoS, shipment legs)

For each page we capture a full-page PNG screenshot, dump the rendered HTML,
and assert on a few canonical phrases that should be present after the sprint
work (DEL-CRW-2025-2 code, status pill, section headings). Any missing assert
is reported but does not abort — we want the full screenshot set even when a
single page regresses.

Read-only. No POST. No state mutation. Smoke-only.

Run::

    python scripts/smoke_chain_of_custody.py \\
        --base-url http://localhost:3030 \\
        --consignment-id 1 \\
        --out-root data/smoke
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import UTC, datetime, timedelta
from pathlib import Path

from jose import jwt
from playwright.sync_api import Page, sync_playwright

JWT_SECRET = os.environ.get(
    "JWT_SECRET",
    "cdb019dcb566c80353b0a838dd5218b59d9fb13ed7f6c4b4e6783d701abaaaab",
)
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:18000")
SESSION_COOKIE = "dft_session"
ADMIN_EMAIL = "admin@dft-project.com"

# Sample document refs for c-1 (DEL-CRW-2025-2). Discovered via direct DB
# query 2026-05-25 — see chain-of-custody backfill notes.
C1_PROBES = [
    ("chain_summary", "/consignments/1/chain-summary", "application/json"),
    ("bl_pdf", "/consignments/1/bl/CMDU856254189.pdf", "application/pdf"),
    ("customs_pdf", "/consignments/1/customs/25NL7STGMQMBRL6DA7.pdf", "application/pdf"),
    ("invoice_pdf", "/consignments/1/invoices/OIS-INV250023.pdf", "application/pdf"),
    ("pos_pdf", "/consignments/1/pos/OISCRO-0013-25.pdf", "application/pdf"),
    ("delivery_uk_pdf", "/consignments/1/delivery-uk.pdf", "application/pdf"),
]


def mint_token(email: str, role: str, ttl_minutes: int = 30) -> str:
    exp = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
    return jwt.encode(
        {"sub": email, "role": role, "exp": exp},
        JWT_SECRET,
        algorithm="HS256",
    )


def probe_backend(token: str, name: str, path: str, expect_ct: str) -> dict[str, object]:
    """Hit a backend endpoint with Bearer token; assert status 200 + Content-Type."""
    url = BACKEND_URL.rstrip("/") + path
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 — local dev only
            ct = resp.headers.get("Content-Type", "")
            length = int(resp.headers.get("Content-Length") or 0)
            magic = resp.read(8) if expect_ct == "application/pdf" else b""
            ok = (
                resp.status == 200
                and expect_ct in ct
                and (expect_ct != "application/pdf" or magic.startswith(b"%PDF-"))
            )
            return {
                "name": name,
                "url": url,
                "status": resp.status,
                "content_type": ct,
                "length": length,
                "pdf_magic_ok": magic.startswith(b"%PDF-") if expect_ct == "application/pdf" else None,
                "ok": ok,
            }
    except urllib.error.HTTPError as e:
        return {"name": name, "url": url, "status": e.code, "error": e.reason, "ok": False}
    except Exception as e:  # noqa: BLE001
        return {"name": name, "url": url, "error": repr(e), "ok": False}


def check_phrases(html: str, phrases: list[str]) -> dict[str, bool]:
    norm = re.sub(r"\s+", " ", html)
    return {p: (p in norm) for p in phrases}


def smoke_page(
    page: Page,
    url: str,
    out_dir: Path,
    name: str,
    expect: list[str],
) -> dict[str, object]:
    page.goto(url, wait_until="networkidle", timeout=30_000)
    # Give client islands a beat to hydrate.
    page.wait_for_timeout(1_000)
    html = page.content()
    title = page.title()
    final_url = page.url
    png_path = out_dir / f"{name}.png"
    html_path = out_dir / f"{name}.html"
    page.screenshot(path=str(png_path), full_page=True)
    html_path.write_text(html, encoding="utf-8")
    checks = check_phrases(html, expect)
    return {
        "url": url,
        "final_url": final_url,
        "title": title,
        "screenshot": str(png_path),
        "html": str(html_path),
        "html_bytes": len(html),
        "checks": checks,
        "all_passed": all(checks.values()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="http://localhost:3030")
    ap.add_argument("--consignment-id", type=int, default=1)
    ap.add_argument(
        "--out-root",
        type=Path,
        default=Path("data/smoke"),
        help="output root; sub-dir named with UTC date + consignment id",
    )
    ap.add_argument(
        "--admin-email",
        default=ADMIN_EMAIL,
        help="JWT sub claim; must match a real users.email row",
    )
    args = ap.parse_args()

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out_root / f"chain-of-custody_c-{args.consignment_id}_{stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    token = mint_token(args.admin_email, "admin", ttl_minutes=30)
    base = args.base_url.rstrip("/")
    host = base.split("://", 1)[1].split(":", 1)[0]

    pages_spec = [
        (
            "01_logistics_list",
            f"{base}/app/logistics",
            ["Consignments", "DEL-CRW-2025-2"],
        ),
        (
            "02_logistics_detail",
            f"{base}/app/logistics/{args.consignment_id}",
            [
                "DEL-CRW-2025-2",
                # Sprint-touched sections — verify section headings render.
                "DEV-P100",
                "Crown Oil",
                # Shipment legs are the chain-of-custody payload.
                "CMDU856254189",
                "JLY001-JLY020",
                "UTB-2025-Q3-CONSOLIDATED",
            ],
        ),
    ]

    results: list[dict[str, object]] = []
    probe_results: list[dict[str, object]] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
        )
        context.add_cookies(
            [
                {
                    "name": SESSION_COOKIE,
                    "value": token,
                    "domain": host,
                    "path": "/",
                    "httpOnly": True,
                    "secure": False,
                    "sameSite": "Lax",
                }
            ]
        )
        page = context.new_page()

        for name, url, expect in pages_spec:
            print(f"→ {name}: {url}")
            try:
                res = smoke_page(page, url, out_dir, name, expect)
            except Exception as e:  # noqa: BLE001
                res = {"url": url, "error": repr(e)}
                print(f"  ERROR: {e!r}")
            results.append({"name": name, **res})

        browser.close()

    # Backend artefact probes (auth-gated endpoints touched by sprint).
    print()
    for name, path, expect_ct in C1_PROBES:
        print(f"→ probe {name}: {path}")
        r = probe_backend(token, name, path, expect_ct)
        if not r.get("ok"):
            print(f"  ✗ {r}")
        probe_results.append(r)

    # Markdown report.
    report = out_dir / "REPORT.md"
    lines = [
        "# Chain-of-custody smoke run",
        "",
        f"- generated: `{stamp}`",
        f"- consignment_id: `{args.consignment_id}`",
        f"- base_url: `{base}`",
        f"- admin: `{args.admin_email}` (role=admin, 30-min token)",
        "",
    ]
    all_ok = True
    for r in results:
        lines.append(f"## {r.get('name')}")
        if "error" in r:
            all_ok = False
            lines.append(f"- ❌ ERROR: `{r['error']}`")
            lines.append("")
            continue
        lines.append(f"- URL: `{r['url']}`")
        lines.append(f"- final URL: `{r['final_url']}`")
        lines.append(f"- title: `{r['title']}`")
        lines.append(f"- HTML bytes: {r['html_bytes']}")
        lines.append("- assertions:")
        for phrase, ok in r["checks"].items():
            mark = "✓" if ok else "✗"
            if not ok:
                all_ok = False
            lines.append(f"  - {mark} `{phrase}`")
        lines.append(f"- screenshot: `{Path(str(r['screenshot'])).name}`")
        lines.append("")
    lines.append("## Backend artefact probes (auth-gated endpoints)")
    lines.append("")
    for r in probe_results:
        mark = "✓" if r.get("ok") else "✗"
        if not r.get("ok"):
            all_ok = False
        size_part = f", {r['length']:_} bytes" if "length" in r else ""
        ct_part = f", `{r['content_type']}`" if "content_type" in r else ""
        err_part = f" — ERROR: `{r['error']}`" if "error" in r else ""
        lines.append(
            f"- {mark} **{r['name']}** — HTTP `{r.get('status','?')}`"
            f"{ct_part}{size_part}{err_part}"
        )
        lines.append(f"  - `{r['url']}`")
    lines.append("")
    lines.append(f"## Overall: {'✅ PASS' if all_ok else '❌ FAIL'}")
    lines.append("")
    report.write_text("\n".join(lines), encoding="utf-8")

    # Machine-readable copy for diffing across runs.
    (out_dir / "REPORT.json").write_text(
        json.dumps(
            {
                "generated": stamp,
                "consignment_id": args.consignment_id,
                "base_url": base,
                "ui": results,
                "probes": probe_results,
                "ok": all_ok,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print()
    print(f"out_dir: {out_dir}")
    print(f"report : {report}")
    print(f"status : {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
