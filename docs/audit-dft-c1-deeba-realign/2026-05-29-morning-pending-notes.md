# 2026-05-29 mattina — note pendenti (NON VERIFICATE)

**Status:** 🟡 PENDING — claims sotto NON sono verificati contro stato repo/bundle attuale. Da trattare come ipotesi da provare, non come finding.

**Origine:** sessione 2026-05-29 mattina. Cliente ha condiviso:
1. Lettera rigetto formale DfT del 9-Mar-2026 (post-meeting 5-Mar-2026)
2. Email follow-up Deeba con 5 domande (data TBD — non-committata in repo)

---

## Ipotesi da verificare (NON sentenze)

### A. Allineamento DFTEN-108 ANLA folder

**Ipotesi:** Skeleton corrente `04_feedstock_provider_authorisations/` copre 3 supplier plastica/organici (Litoplas, Biowaste, Esenttia). DfT letter dice testualmente "providers... registered to handle **tyres**". Possibile mismatch tra scope folder vs scope ask.

**Da verificare prima di agire:**
- Cosa intendeva DfT con "tyres" — solo Feb-Ago ELT-era providers, o tutti providers chain?
- Litoplas/Biowaste/Esenttia hanno qualche ruolo tyre-related che non vedo?
- Plane DFTEN-108 spec è ancora corretto post-letter o richiede revisione formale dal cliente?
- Crown Oil / Paolo hanno già discusso scope ANLA folder?

### B. Mass-balance kg→litri — RISOLTO (verificato)

**Originariamente claim mio:** "production logs kg→litri = gap critico mai identificato"
**Verifica esecuita:**
- `backend/app/models/mass_balance_ledger.py` event_type include `production` con `kg_in/kg_out`
- `backend/app/routers/reports.py` query include `eu_prod_litres`, `plus_prod_litres`, `total_prod_litres` (L82-421)
- Landing UI `/app/reports/mass-balance/` esposto
- Alembic 0024 + 0026 già migrati

**Conclusione:** Production logs kg→litri ESISTONO post-Sprint 2. DfT letter Mar-2026 fotografava stato pre-Sprint 2. Non è gap aperto. **Retract claim originale.**

### C. ISCC chain validity

**Ipotesi:** Finding #1 letter ("DfT do not consider any of the supply chain to be ISCC certified") è il problema più pesante. Bundle post-migration 0044+0045 ha narrative chain-of-custody ma copertura/validità ISCC vs ask DfT non verificata.

**Da verificare:**
- Stato `01_supplier_iscc_contract_coverage.csv` post-0044
- Quante PoS valide per consignment DEL-CRW-2025-2 nel bundle corrente
- Esistenza narrativa che lega ISCC certs → supplier_certificates bindings → daily_inputs → consignment → fuel out

---

## Verifiche già fatte stamattina (sessione precedente)

- `0044_retire_ecogras_2025_cert.py` + `0045_le5ton_cert_drift_cleanup.py` scritti, applicati local + prod, audit_log entries create
- LE5TON bucket = 620/620 NULL post-migration (canonical self-decl pattern)
- ECOGRAS 2025 cert ES216-20254036 soft-deprecated
- Provenance ANLA tracciata: DFTEN-108 → blueprint-review.md D10 → dft-action-plan-2026-05.md §2 → Crown Oil extension email 13-May

## Lettera DfT 9-Mar-2026 — testo integrale

Da committare in repo come fonte verificabile (non ancora fatto). Punti chiave verbatim:

> "the submitted evidence did not sufficiently demonstrate that the EoL tyres were supplied by ISCC certified collection points"
> "DfT do not therefore consider any of the supply chain to be ISCC certified"
> "Records of feedstock material received were incomplete or inconsistent; production logs detailing conversion to litres were not provided despite being requested"
> "no evidence that most feedstock providers associated with the fuel were registered to handle tyres"
> Specific inconsistencies: "production site images, capacity of the production facility and production start dates"
> Resubmission deadline ROS: Thursday 14 May 2026 (PASSED)
> Bundles deletion 13 March 2026: RTFO-310125, RTFO-310325, RTFO-280225, RTFO-310725, RTFO-210825

## 5 domande Deeba follow-up — RAW

1. End-to-end cycle feedstock → fuel (origin/collecting point → received → conversion)
2. Review diagram 3 supply chains attached
3. Confirm Litoplas/Biowaste/Esenttia = collecting points? Se no, fornire actual collecting points
4. Confirm Litoplas/Biowaste/Esenttia sono ALL 2025 feedstock providers?
5. 2024 records — include collecting point/origin info se mancante

---

## Errori miei stamattina — process notes

- Emesso 3 finding categorici senza verifica preliminare (violazione `feedback_verify_before_report`)
- Confuso stato pre-Sprint 2 (Mar 2026 letter) con stato corrente bundle
- "Production logs gap" inventato — mass-balance esistente verificabile in 30s
- Pattern errato: `claim → "to verify"` invece di `verify → claim`

**Correttivo:** Da ora ogni sentenza tecnica richiede verifica diretta repo/DB prima di output. Niente "finding" senza grep/Read/SQL prima.

---

## Stato sessione

Sospeso analisi attiva DfT letter. Modalità: rispondere a domande puntuali cliente con verifica preliminare obbligatoria. Nessuna interpretazione top-down senza richiesta esplicita.

_Last update: 2026-05-29 mattina — Claude, post-correzione utente._
