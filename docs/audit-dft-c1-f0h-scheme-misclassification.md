# F0-H — Scheme Misclassification Finding

**Audit**: DEL-CRW-2025-2 (Crown Oil UK, 576,270 kg DEV-P100 Q3 2025)
**Trovato**: 2026-05-26 durante build parser `cert_scope_parser.py`
**Severità**: 🔴 BLOCCANTE — RTFO submission non-conformante come oggi.
**Sopprime / sostituisce**: nessun finding esistente.
**Bind a**: F0-F (scope material groups) — F0-H è scoperta collaterale.

---

## 1. Sintesi

5 dei 7 certificati ISCC oggi registrati in `certificates` come
`scheme='ISCC EU'` sono in realtà documenti **ISCC PLUS** (schema
circular plastics, non sustainability biofuel). Il mismatch è
verificabile in ~30 secondi dall'header di ciascun PDF.

Per UK RTFO, ISCC PLUS **non sostituisce** ISCC EU come voluntary
scheme qualificante. Il bundle DEL-CRW-2025-2 quindi, nel suo stato
attuale, presenta 5 supplier "ISCC-certified" con documentazione che
un verificatore DfT identificherebbe come schema sbagliato alla prima
verifica cross-check sul portale ISCC.

## 2. Dati verificabili

| Cert number | DB `scheme` | PDF schema | Holder | Note |
|---|---|---|---|---|
| CO222-00000026 | ISCC EU | **ISCC PLUS** | LITOPLAS SA | Annex I = plastiche (PP, HDPE) |
| CO222-00000027 | ISCC EU | **ISCC PLUS** | ESENTTIA | scope-block extract `Mass Balance` only |
| ES216-20249051 | ISCC EU | **ISCC PLUS** | PYRCOM | parser estrae `Mixed waste plastics` |
| US201-138762025 | ISCC EU | **ISCC PLUS** | KALTIRE | nessun material group in scope inline |
| US201-158772025 | ISCC EU | **ISCC PLUS** | EFFICIEN | parser estrae `End-of-life tyres (ELT)` |
| ES216-20254036 | ISCC EU | ISCC EU ✓ | ECOGRAS | parser estrae `Used cooking oil (UCO)` |
| EU-ISCC-Cert-NL220-2228065006 | ISCC EU | ISCC EU ✓ | UTB BV | scope-block empty (Trader scope) |

Comando di verifica:

```bash
python3 -c "
import sys; sys.path.insert(0,'backend')
from pathlib import Path
from app.services.cert_scope_parser import parse_cert_pdf
for f in [
    'supplier-q3/CO222-00000026_LITOPLAS.pdf',
    'supplier-q3/CO222-00000027_ESENTTIA.pdf',
    'supplier-q3/ES216-20249051_PYRCOM.pdf',
    'supplier-q3/US201-138762025_KALTIRE.pdf',
    'supplier-q3/US201-158772025_EFFICIEN.pdf',
    'supplier-q3/ES216-20254036_ECOGRAS.pdf',
    'utb-bv/CERTIFICATE_UTB_BV.pdf',
]:
    r = parse_cert_pdf(Path('data/certificates') / f)
    print(f, r.scheme_detected, r.material_groups)
"
```

## 3. Perché ISCC PLUS ≠ ISCC EU per RTFO

- **ISCC EU** = voluntary scheme riconosciuto dalla EU Commission sotto
  RED II Art. 30; copre sustainability + GHG saving per biofuels e
  bioliquids. RTFO accetta ISCC EU come prova di sustainability per
  RTFO certificate issuance.
- **ISCC PLUS** = voluntary scheme per circular economy, bio-circular
  materials, sustainable feedstock per applicazioni non-energetiche
  (chemicals, packaging, food). **Non** è riconosciuto sotto RED II
  Art. 30 per biofuel sustainability. Non è qualificante per RTFO.
- **ISCC CORSIA** = voluntary scheme aviation-specific; RTFO accetta
  per SAF reporting; non rilevante per DEV-P100 (road fuel).

Riferimento: ISCC System website, "Choosing the right ISCC scheme"
(https://www.iscc-system.org/about/iscc-system/).

## 4. Risk surface

### 4a. Lato audit Crown Oil

Crown Oil è il submitter ROS verso DfT. Quando Crown apre il bundle e
inizia upload dei supplier ISCC cert al loro RTFO account, il sistema
DfT verifica numero cert + scheme contro il portale ISCC. Un cert
PLUS caricato come "ISCC EU" trigger un rejection automatico o un
review escalation.

### 4b. Lato chain-of-custody

Se i 5 supplier sono effettivamente coperti via **chain ISCC EU
OisteBio downstream** (cioè OisteBio ha cert ISCC EU che assorbe la
massa upstream come mass-balance input), il loro cert PLUS è
documentazione di chain integrity ma non è il cert RTFO. Il bundle deve
mostrare il **nostro** cert ISCC EU OisteBio come copertura, e i cert
PLUS supplier come allegati di trasparenza, non come prova.

Verifica necessaria: esiste un cert ISCC EU OisteBio per la Q3 2025
processing window? Non è registrato nel DFT attualmente (controllato
2026-05-26: in `certificates` non c'è cert con holder OisteBio scheme
ISCC EU per Q3 2025).

### 4c. Lato LITOPLAS specifico

L'Annex I del cert LITOPLAS ISCC PLUS lista come input/output:

- PP (Circular BOPP) → PP (Circular BOPP Printed Packaging)
- PP (Bio Circular BOPP) → PP (Bio Circular BOPP Printed Packaging)
- PP (Circular PP. Pellets) → PP (Circular PP Packaging)
- PP (Bio Circular PP. Pellets) → PP (Bio Circular PP Packaging)
- HDPE (HDPE. Pellets) → HDPE (HDPE Packaging materials)

**Nessun ELT, nessun pyrolysis oil, nessun feedstock energetico.**
LITOPLAS è quindi, dal cert allegato, un operatore di plastic
recycling/packaging — non un fornitore di pneumatici fuori uso. Il
loro presenza come fornitore certificato nel bundle DEL-CRW-2025-2
deve essere chiarita (memo a Paolo, lettera cliente §14).

## 5. Mitigazione applicata 2026-05-26

Per il vincolo `project_iscc_audit_safety` (preservare doc IDs storici,
mai sovrascrivere compliance data silenziosamente):

1. **Nessuna modifica** ai 5 record `certificates` esistenti. Il campo
   `scheme` resta "ISCC EU".
2. **Aggiunta colonna `scheme_pdf_detected text`** via migration
   `0034_cert_scope_material_groups`. La colonna riporta lo schema
   rilevato dal parser nel PDF — independent dal valore manuale.
3. **Indice parziale `ix_certificates_scheme_mismatch`** per query
   rapide su tutti i mismatch (`WHERE scheme_pdf_detected IS NOT NULL
   AND scheme_pdf_detected <> scheme AND deleted_at IS NULL`).
4. **Lettera cliente §14** (`docs/audit-dft-c1-cliente-data-request.md`)
   chiede a Paolo: cert ISCC EU separato per i 5 supplier? Chain via
   OisteBio downstream? LITOPLAS è ELT supplier o no?
5. **No reshuffle binding `supplier_certificates`** — questo è
   pertinente a F0-H ma blocked su risposta cliente.

## 6. Azioni autonome rimanenti (no cliente)

- [ ] Backfill `scheme_pdf_detected` per i 7 cert in scope eseguendo
      il parser via `scripts/backfill_cert_scope.py` (script da scrivere,
      not in this commit).
- [ ] Backfill `scope_material_groups` + `scope_raw` stessa run.
- [ ] UI mass-balance: surface badge "scheme mismatch" su righe con
      cert dove `scheme_pdf_detected <> scheme` (gap N4 + ora N6 in
      red-team round 2 doc).
- [ ] Estensione parser per ISCC PLUS Annex I table parsing — oggi
      estrae solo se materiale è nominato inline nello scope sentence,
      manca tabellare. Bassa priorità: schema-detection già fa lavoro.

## 7. Azioni bloccate (cliente)

- [ ] Chiarimento Paolo §14 lettera (1-3 quesiti).
- [ ] Eventuale aggiunta cert ISCC EU OisteBio per Q3 2025 (se esiste).
- [ ] Eventuale soft-deprecate dei 5 cert PLUS sostituiti dal cert
      ISCC EU corretto — migration 0035 cert-scheme-correction (da
      scrivere POST risposta cliente, non pre-scritto per non condizionare
      la decisione).

## 8. Round-2 audit impact

Il red-team round 2 (`docs/audit-dft-c1-evidence-matrix.md` §9) era
stato chiuso prima della scoperta F0-H. Il verdict round 2 era già
**STILL REJECT**; F0-H non lo cambia (era già rejected), ma sposta una
voce dalla colonna "manca scope material" (F0-F, gap parser) a una
voce più grave "schema diverso da quello dichiarato in DB" (F0-H,
non-conforming documentation).

Quando si farà round 3 (post Tier C cliente), F0-H avrà uno status
distinto dal F0-F nella matrix. F0-H è risolvibile solo via risposta
cliente — non possiamo concludere autonomamente che il chain ISCC EU
OisteBio copra i 5 supplier upstream senza conferma scritta.

---

**Riferimenti**:
- `backend/app/services/cert_scope_parser.py` (parser + scheme detect)
- `backend/alembic/versions/0034_cert_scope_material_groups.py` (DB col)
- `docs/audit-dft-c1-cliente-data-request.md §14` (quesiti Paolo)
- Memory `[[project_iscc_audit_safety]]` (vincolo no overwrite)
- Memory `[[project_feedstock_elt]]` (ELT = feedstock, non plastic)
