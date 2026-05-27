# Audit DFT-C1 — F0 Responses Round 1 (Paolo compilato 2026-05-26)

Fonte: `gdrive:DFT_2025/PARTICULARES/audit-dft-c1-f0-questionnaire_COMPILATO.pdf` (112 KB).

Parse + verifica autonoma + verdetto round-1 per ogni F0 (escluso F0-F chiuso via mig 0038).

---

## Sintesi

| F0 | Risposta cliente | Verifica autonoma | Verdetto round-1 | Blocker bundle? |
|----|------------------|-------------------|------------------|-----------------|
| A | Sustainable via ≤5 TON self-declaration | ⚫ **VOID 2026-05-26** — SANIMAX retired (legacy) via mig 0039 | ⚫ **VOID** | NO |
| B | Protocollo FMS v1.0 approvato 2024-06-01; "4.7%" non capito | Documento FMS richiesto + chiarire metrica 4.7% | 🟡 partial | NO |
| C | BL data indicativa, NO amendment | Framework accettato | 🟢 chiuso framework | NO |
| D | Conquer Trade buyer DEV-P200; 8 fatture pending; syngas burnt-for-power 100% interno | Schema DB previene double-claim syngas ✅; gap byproduct_sale Q3 (0 record vs 2.78M kg) | 🟡 partial | NO (gap doc, non claim) |
| E | Screenshot procedure non capito | Riformulare richiesta operativa | 🔴 non capito | NO |
| G | Default values usati; "attendiamo POSs" | Chiarire direzione: POS upstream o downstream? | 🟡 partial | NO |
| H | "ISCC PLUS accettato da RTFO" per 5 cert | Path B confermato: OisteBio site cert ISCC EU `LV227-00000597` (valid 24.10.24→23.10.25, copre Q3 2025) → output PoS sotto EU scheme. Upstream PLUS irrilevante per RTFO output classification. | 🟢 **RESOLVED Q3 2025** | NO |

**Net**: 2🟢 (F0-C framework + F0-H Q3 2025 Path B) + 3🟡 (F0-B,D,G pending cliente upload) + 1🔴-soft (F0-E riformulare) + 1⚫VOID (F0-A retired mig 0039).

**Bundle Q3 2025 release**: NO regulatory blocker. Restano solo gap doc su upload cliente (fatture Conquer, FMS doc, walkthrough, POSs direzione).

---

## F0-A — Cert SANIMAX ⚫ VOID 2026-05-26

**Status**: VOID — superseded da cliente "trash" call 2026-05-26.

**Cliente verbatim** (2026-05-26):
> "abbiamo solo i fornitori attivi, tutto il resto non esiste più... sanimax/ecodiesel e cecogras tutta sta roba va dimenticata.. trash"

**Action eseguita**: migration `0039_retire_legacy_suppliers` (apply local 2026-05-26).

- Suppliers soft-deprecated: SANIMAX (id 2), CIECOGRAS (id 4), ECODIESEL (id 6) → `deleted_at = NOW()`, `active = FALSE`
- Certificates soft-deprecated: `ES216-20258083` (SANIMAX), `ES216-20244036` (CIECOGRAS), `US201-100862024` (ECODIESEL) → `deleted_at = NOW()`, `status = 'revoked'`
- Bindings (`supplier_certificates`) LEFT IN PLACE per ISCC audit history preservation
- Audit log: 6 `soft_delete` entries (3 suppliers + 3 certs)

**Risposta Paolo F0-A originale** ("Sustainable via ≤5 TON self-declaration") **non più applicabile** — SANIMAX out of audit scope.

**Authoritative active supplier set** (post-0039) = Drive `gdrive:DFT_2025/RTFO-310825/03_supplier_evidence/certificates/` (7 ELT supplier + OisteBio own + UTB off-taker).

**Verifica DB pre-retire** (2026-05-26 head 0038):
- SANIMAX: 1532 daily_inputs total, 0 active (kg_active=0)
- CIECOGRAS: 1314 daily_inputs total, 0 active
- ECODIESEL: 0 daily_inputs ever
- Off_taker / shipment_leg references: 0

**Severità**: zero post-retire.

---

## F0-B — FMS coverage 4.7%

**Risposta Paolo**: "Protocollo FMS v1.0 approvato 2024-06-01"; "4.7%" non capito.

**Lettura**: cliente conferma esistenza protocollo, ma non riconosce metrica "4.7% coverage" dal questionario.

**Origine "4.7%"**: F0-B doc interno calcolava ratio cert-binded daily_inputs / total daily_inputs. Probabile metrica calcolata internamente, non comunicata mai a Paolo.

**Action**:
1. Richiedere upload `FMS_v1.0_2024-06-01.pdf` a Drive `F0-responses/F0-B/`
2. Riformulare domanda metrica: invece "4.7% coverage" → "elenca quali fornitori hanno cert binding completo vs partial" (linguaggio business, non ratio)

**Severità**: media (manca evidenza scritta protocollo).

---

## F0-C — BL date inconsistencies

**Risposta Paolo**: "BL date indicativa, NO amendment"

**Lettura**: Bills of Lading hanno date indicative non amendabili retroattivamente. Cliente accetta framework: discrepanze BL non sono defect ma feature operativa.

**Verdetto**: 🟢 **chiuso framework**. Da documentare in statement finale come "operational tolerance per industry practice".

**Action**: aggiornare statement § "BL date framework" — citare risposta Paolo verbatim.

**Severità**: zero post-risposta.

---

## F0-D — Plus product + syngas

**Risposta Paolo**:
1. Conquer Trade = single buyer DEV-P200 byproduct
2. 8 fatture Q3 2025 pending scan
3. Syngas burnt-for-power 100% interno, NON sale separato

**Verifica autonoma DB**:

```
Q3 2025 daily_production:
  syngas_kg = 289'347.655 (51 giorni)
  eu_prod_kg (DEV-P100) = 2'162'794.050
  plus_prod_kg (DEV-P200) = 2'784'943.136

Q3 2025 byproduct_sale:
  ZERO record
```

**Schema check**:
```sql
byproduct_sale.product_kind CHECK ∈ ('plus_oil','carbon_black','metal_scrap')
```
→ syngas **non vendibile by design** (schema-level prevention double-claim). ✅

**Gap individuato**:
- 0 record `byproduct_sale` Q3 2025 vs 2.78M kg `plus_prod_kg`
- 8 fatture Conquer Trade pending caricamento
- byproduct_buyer id=23 (CONQUERS WORLD TRADE S.A.S. Colombia) già esistente in DB

**Action**:
1. Attendere scan 8 fatture Drive `F0-responses/F0-D/`
2. Una volta ricevute → script ingest `byproduct_sale` con `buyer_id=23`
3. Cross-check `SUM(byproduct_sale.kg_net Q3)` ≈ `SUM(plus_prod_kg Q3)` (tolleranza losses/stock)
4. Verificare PYRC0M ricezione syngas burnt-for-power — Annex V counterfactual

**Memory saved**: `[[project_conquer_trade_byproduct]]` (id 23).

**Severità**: media (doc gap, non integrity claim).

---

## F0-E — ISCC procedure screenshot

**Risposta Paolo**: "Screenshot procedure non capito"

**Lettura**: domanda originale chiedeva screenshot procedurale ISCC portal — cliente non ha capito cosa screenshottare.

**Riformulazione operativa**:
> "Per ogni cert nella lista [LITOPLAS, ESENTTIA, BOLDER, KALTIRE, EFFICIEN, SANIMAX, PYRCOM]:
> 1. Apri https://www.iscc-system.org/certificates/all-certificates/
> 2. Filtra per certificate number
> 3. Screenshot pagina dettaglio cert
> 4. Salva PNG su Drive `F0-responses/F0-E/<cert_id>.png`"

**Action**: produrre `audit-dft-c1-f0-e-walkthrough.md` con step-by-step + screenshot esempio.

**Severità**: bassa (problema comunicazione, non integrity).

---

## F0-G — Default values + POS pending

**Risposta Paolo**: "Default values usati; attendiamo POSs"

**Lettura ambigua**: "attendiamo POSs" — quale direzione?
- (a) POSs upstream da fornitori (LITOPLAS etc.) → certificare lotti ELT input
- (b) POSs downstream verso Crown Oil → bundle finale RTFO submission

**Default values**: cliente conferma uso default GHG (RED Annex V default values per RCF pathway).

**Action**:
1. Richiedere chiarimento: "POSs **upstream** (da fornitori ELT) o **downstream** (a Crown Oil)?"
2. Lista esatta default values usati per ogni step pathway

**Severità**: media (impatta GHG calc + audit trail).

---

## F0-H — ISCC PLUS vs ISCC EU per RTFO **[🟢 RESOLVED Q3 2025 — 2026-05-26]**

### Resolution finale 2026-05-26

Path B confermato 4 step:

1. **Auditor esterno** (2026-05-26): "Non confondere ELT (feedstock) e DEV-P100 (output finished pyrolysis oil). DEV-P100 può essere venduto sotto ISCC EU scheme anche se feedstock ELT è certificato ISCC PLUS."
2. **Pyrum precedent** (marzo 2026): ISCC EU per thermolysis oil ELT, PLUS solo per recovered carbon black (non-fuel). Pattern PLUS/EU split per use case.
3. **OisteBio site cert verificato**: `EU-ISCC-Cert-LV227-00000597`, BM Certification Latvia, validity **24.10.2024 → 23.10.2025** → copre Q3 2025 production window completo. Annex include "Biogenic fraction of end-of-life tires → Refined oil (Tires)" GHG Actual + Waste process Yes.
4. **Agente deep research** `/tmp/dft_elt_deep_research_2026-05-26.md`: ELT biogenic route già usata in RTFO 2024 (10% UK development petrol da Polonia, 14% da SE+food PL) → pathway esiste e funziona.

**Per Q3 2025 bundle**: F0-H NON è blocker. Crown Oil scritta conferma NON necessaria — Path B chiude internamente via OisteBio EU output cert. Anche temporalmente assurdo richiedere conferma maggio 2026 per merce ago 2025 (audit già iniziato).

**Out of scope Q3 2025**:
- Forward 2026+ post-23.10.2025 cert renewal V2 (separato project planning)
- §2.2 RCF application "Fossil component of ELT" (long-track parallel, not Q3 2025)
- 5 supplier ISCC EU verification U2 (upstream scheme è internal CoC concern, output cert EU è ciò che conta per RTFO submission)

**Verdetto round-1 originale** (sezione sotto) mantenuto come record di processo: la verifica strict PLUS≠EU rimane vera, ma irrilevante per Path B dove ciò che conta è scheme dell'OUTPUT PoS.

---

### Round-1 verdetto originale (PRE-auditor input)

**Risposta Paolo verbatim** (5 occorrenze per LITOPLAS, ESENTTIA, BOLDER, KALTIRE, EFFICIEN):
> "MA PLUS E' ACCETTATO DA RTFO"

**Verifica regulatoria** (Agent ricerca primary sources 2026-05-26):

| Fonte | Verdetto |
|-------|----------|
| [UK DfT Approved Schemes List 2025-11-27](https://www.gov.uk/government/publications/use-of-voluntary-schemes-as-evidence-of-rtfo-and-saf-mandate-compliance/list-of-voluntary-schemes-approved-for-the-rtfo-and-saf-mandate) | Solo **ISCC EU** elencato. ISCC PLUS **assente**. |
| [DfT RCF Guidance Jan 2026, fn.2 p.11](https://assets.publishing.service.gov.uk/media/69a810f62e1f4fbda425228c/dft-rtfo-saf-mandate-rcfs-guidance-26.pdf) | *"Currently, there are no voluntary schemes recognized for RCF pathways"* |
| [ISCC Recognitions page](https://www.iscc-system.org/markets/recognitions/) | Solo ISCC EU citato per UK DfT. ISCC PLUS no. |

**Verdetto BINARIO**: ISCC PLUS **NON accettato** UK RTFO.

**Aggravante**: per pathway RCF (ELT) → DfT riconosce **ZERO voluntary schemes** oggi (neppure ISCC EU).

**Implicazione per i 5 cert PLUS mismatch**:
- Cert PLUS internamente utile (chain-of-custody documentation)
- **NON** sostituiscono direct evidence a DfT
- Crown Oil deve presentare comunque:
  1. Feedstock eligibility verifica RTFO Order Table 7 (o richiesta per-feedstock, mesi)
  2. Full mass-balance chain-of-custody
  3. GHG threshold counterfactual EfW
  4. Waste-hierarchy compliance

**Action immediate**:
1. **NON** chiudere F0-H sulla parola di Paolo
2. Email a Crown Oil compliance: "Confermate accettazione ISCC PLUS per i 5 cert ELT input? Se no, quale evidence richiesta?"
3. Se Crown Oil conferma NO → 5 cert vanno riclassificati come "supporting evidence only" + servono POSs/lab tests dirette feedstock
4. Bundle statement § "ISCC PLUS scope" da riscrivere con disclaimer regulatorio

**Severità**: **CRITICA — audit-killer**.

**Rischio**: se bundle submitted con claim "ISCC PLUS = RTFO compliance" → DfT cross-check 30 secondi → rejection + reputational damage.

---

## Prossimi passi (ordine priorità)

1. **F0-D fatture Conquer Trade** — attendere scan, ingest, cross-check mass-balance.
2. **F0-G chiarimento direzione POSs** — email Paolo singola domanda.
3. **F0-B FMS doc upload** + riformulare metrica.
4. **F0-E walkthrough screenshot** — produrre guida operativa.
5. **F0-C** — solo update statement (chiuso framework).
6. ~~F0-A self-decl SANIMAX~~ → ⚫ **VOID** via mig 0039 (cliente 2026-05-26).
7. ~~F0-H Crown Oil email~~ → 🟢 **RESOLVED** Q3 2025 via Path B (OisteBio EU site cert LV227-00000597 + auditor + Pyrum precedent + RTFO 2024 stats). Non-bloccante.

---

**Round-1 status**: 2🟢 + 3🟡 + 1🔴-soft + 2⚫VOID/RESOLVED.
**Bundle release**: BLOCKED su F0-H conferma Crown Oil.

Last update: 2026-05-26.
