# DFT-C1 Auto-Audit Round-5 — Closure verdict

**Data:** 2026-05-27
**Stato:** ✅ **PASS**
**Trigger:** 0041 applicato LOCAL chiude C11; Round-4 lasciava 1 FAIL (C11) + 1 DEFERRED (C16).

---

## Matrice finale 16 criteri

| # | Criterio | Round-4 | Round-5 | Evidenza |
|---|----------|---------|---------|----------|
| C1  | Migration head | ✅ 0040 | ✅ **0041** | `alembic current` = `0041_byproduct_dev_p200_schema (head)` |
| C2  | Mass balance Jan-Aug | ✅ | ✅ | 0 righe delta > 1 kg su 194 giorni |
| C3  | C14 fragments wipeout | ✅ | ✅ | 0 c14_analysis residual |
| C4  | Backup 0040 popolato | ✅ | ✅ | 98 righe in `_backup_c14_analysis_pre_0040` |
| C5  | Legacy suppliers retired | ✅ | ✅ | 5/5 soft-del (SANIMAX/CIECOGRAS/ECODIESEL + 2 E2E test) |
| C6  | Legacy certs retired | ✅ | ✅ | 3/3 status='revoked' + soft-del |
| C7  | daily_inputs supplier orphans | ✅ | ✅ | 0 orfane Jan-Aug |
| C8  | daily_inputs cert orphans | ✅ | ✅ | 0 orfane Jan-Aug |
| C9  | Crown Oil attivo | ✅ | ✅ | id=59, deleted_at=NULL |
| C10 | Conquer attivo | ✅ | ✅ | id=23, deleted_at=NULL |
| C11 | byproduct_sale CHECK ammette dev_p200 | ❌ FAIL | ✅ **PASS** | CHECK = `('plus_oil','carbon_black','metal_scrap','dev_p200')` |
| C12 | Audit log 0039 | ✅ | ✅ | 6 entries |
| C13 | Audit log 0040 | ✅ | ✅ | 98 entries kind='c14_parse_fragment_cleanup' |
| C14 | Daily production coverage 8 mesi | ✅ | ✅ | 194 giorni |
| C15 | No duplicate prod_date | ✅ | ✅ | 0 duplicati |
| C16 | Driver/cedula/plate schema | ⏸️ DEFERRED | ⏸️ DEFERRED | colonne assenti, attesa risposte cliente B1-B4 |

**Score Round-5: 15 PASS / 0 FAIL / 1 DEFERRED su 16.**

---

## Cambiamenti dal Round-4

1. **0041_byproduct_dev_p200_schema** applied LOCAL 2026-05-27
   - DROP+CREATE CHECK `byproduct_sale_product_kind_check` includendo `dev_p200`
   - +4 col: `price_amount` (numeric 14,2), `currency` (text), `pricing_method` (text), `incoterm` (text)
   - audit_log id=876 action='update' kind='byproduct_dev_p200_schema_extend'
   - **Note**: `action='update'` invece di 'schema_extend' perché audit_log CHECK rifiuta — vedere memoria `project_audit_log_action_check`

2. **Risposte cliente Round-2 ricevute** (A1-A4)
   - A1: product_kind = `dev_p200`
   - A2: zero quality grade in fattura (esplicito)
   - A3: USD / brent_monthly_avg / EXW_GIRARDOT
   - A4: invoice_number = filename stem `CONQ-2025-NNNN`

3. **B1-B4 (DRIVERS) ancora pending** → C16 resta DEFERRED

---

## DEFERRED definition (regola applicata)

Da Round-4 final recommendation:
> Core RTFO submission package: 95% pronto (manca solo Conquer byproduct
> evidence che NON è parte del Crown Oil bundle — è side-track separato
> per audit completezza)

**Quindi:** DEFERRED = "non blocker per Crown Oil bundle, attesa input esterno". Non conta come FAIL. Auto-audit PASS soglia = `0 FAIL outstanding`.

C16 resta DEFERRED in maniera explicit-by-design fino a:
- (i) ricezione DRIVERS.xlsx pulito (PYRCOM cedula prefix corretti)
- (ii) conferma B3+B4 (1:1 mapping + ordering rule)

---

## Cosa NON è scope auto-audit

I 6 punti `AGGIORNAMENTI PROGETTO DFT.docx` (rename DEV-P100→P200, C14 % EU, magazzino display, BL check, cover letter byproducts, BNOVA rename) sono **nuova roadmap cliente, NON gap audit DFT-C1**. Da triagiare separatamente, fuori da questo verdict.

---

## Outcome operativo

- ✅ Auto-audit DFT-C1 PASS — bundle Crown Oil release UNBLOCKED
- ⏸️ C16 driver schema rimane in attesa input cliente (no urgenza audit)
- 📋 Pending non-audit: #80 statement rewrite, #85 FMS, #88 BL date, #92 RCF — separate da DFT-C1
