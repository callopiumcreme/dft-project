# Deeba_Audit_Submission_2026-05-27 — EN realign 2026-05-28

## Scope
Allineamento bundle EN (9 GUIDE PDF + 08_README) ai 10 edit Andrea sulla cover letter (00_COVER_LETTER.md). Cover letter NON modificata in questo round.

## 4 assi di drift corretti

1. **Audit scope window** — front cover GUIDE: aggiunto `Audit window in scope · Jan–Aug 2025 (pooled-tank)`; mantenuto `Consignment ref · DEL-CRW-2025-2`
2. **Ring-fence 73 giorni** — `04_GUIDE.md` riformulato come "73-day production window aggregating pooled-tank output, 500,410 kg post-hoc accounting allocation — NOT a physical per-day ring-fence"
3. **Residuo 75.860 kg** — `04/07/08_GUIDE.md` + `08_README.md`: rimosso "stock residual / rolls forward". Sostituito con "∆ = transload measurement variance (BL-declared ocean vs tank-side metered UTB), transload buffer fully cleared into DEL-CRW-2025-2 invoice series, no residual outside Crown supply chain"
4. **Status Punto 7** — `07_GUIDE.md`: `at_utb / delivered_uk` → `delivered_uk (POD received 2025-08-15)`

## Files patched (source MD + generator)
- `/tmp/deeba_audit_export/build_pdfs.py` (COVER_TEMPLATE cover-meta-row)
- `/tmp/deeba_audit_export/guides/{00,04,07,08}_GUIDE.md`
- `/tmp/deeba_audit_export/08_README.md`

## Files NOT touched (already coherent)
- `00_COVER_LETTER.md` (Andrea source-of-truth)
- `01,02,03,05,06_GUIDE.md`
- `06_README.md`

## Verifica
- `weasyprint` rebuild 9/9 OK
- Sweep forbidden-pattern su 9 PDF: 0 fail (no "stock residual", no "73 daily contributions", no "rolls forward", no "at_utb / delivered_uk")
- Size byte-exact match local↔Drive su tutti 9 PDF

## Drive push
`rclone copy --no-traverse --ignore-times` su `gdrive:DFT_2025/Deeba_Audit_Submission_2026-05-27/<subfolder>/` per:
- 9× `NN_GUIDE.pdf`
- `08_README.md`

Tutti "Copied (replaced existing)".

## Pending
- **IT folder** `Deeba_Audit_Submission_2026-05-27_IT/` — stale post-Andrea. Decisione utente: archive su `_archive_2026-05-28/` o lasciare. Non azionato in questo round (utente: "solo a").
