# Questionario F0-A..H — Cliente input batched

**Audit**: DEL-CRW-2025-2 (Crown Oil UK, 576,270 kg DEV-P100, Q3 2025)
**Da**: OisteBio · Sistema Tracciabilità (Gianni)
**A**: Paolo Ughetti (CEO/Geschäftsführer)
**CC**: Hugo (operations Girardot), Ferdinando (planta), Marco (logistica)
**Data**: 2026-05-26
**Plane ticket**: _TBD — registrare ID qui dopo creazione_
**Scope**: chiude **Phase 2** del piano `docs/audit-dft-c1-action-plan-100pct.md`.
**Cosa NON è in questo questionario**: F0-F (chiuso internamente via
migration `0038_cert_reality_sync` 2026-05-26, no input cliente).

---

## Istruzioni risposta

Ogni riga ha:
- **F0-ID** — riferimento finding red-team round 2
- **Trovato** — fatto verificabile in DB / PDF / Drive oggi
- **Cosa serve** — artefatto preciso richiesto
- **Criterio accettazione** — condizione binaria di chiusura
- **Owner** — chi può fornire
- **Bloccante?** — 🔴 audit-killer / 🟡 patchable / 🟢 cosmetic

Risposta accettabile = artefatto allegato + 1 riga di nota nel ticket
Plane. **Non rispondere via email**: tutto su Plane per audit-trail.

---

## Tabella richieste

| F0 | Trovato | Cosa serve | Criterio accettazione | Owner | Severità |
|----|---------|------------|------------------------|-------|----------|
| **A** | LE5TON Q3 2025: 309 inbound rows, 0 `certificate_id`, 307/309 missing eRSV, contract = `SD` placeholder | (a) Decisione formale: rivendichiamo LE5TON 1,226,479 kg come sustainable **OR** li ri-classifichiamo non-sustainable. (b) Se sustainable: PDF dichiarazioni self-declaration ≤5 TON firmate, paper-records samples (min 5 ticket Q3) scansionati, statement paper-records firmato da Paolo. (c) Se non-sustainable: nota scritta di re-classifica + ricalcolo claimable share. | Paolo firma statement `docs/audit-dft-c1-paper-records-statement.md` + (a) + scelta documentata in `certificates.notes` | Paolo | 🔴 |
| **B** | FMS / C14: 879 Q3 input rows → 0 con `c14_value`, 41/879 (4.7 %) con `c14_analysis`, 61/879 (6.9 %) con `manuf_veg_pct` | (a) Protocollo FMS Girardot (PDF, versione + data approvazione). (b) Risultati lab C14 Q3 2025 — minimo 1 campione/mese × 3 mesi = 3 lab reports. (c) Statement scritto sul perché coverage attuale è 4.7 % (es. analisi non eseguite, batch pre-stoccaggio) | Coverage post-backfill ≥ 1 C14 result per ciascun mese Jul/Aug/Sep 2025 + protocollo allegato a `data/customs/` | Hugo (planta) + Paolo countersign | 🔴 |
| **C** | BL2 (CMDU877254433) data 2025-07-03, ma 14 container caricati 2025-07-10. BL pre-data cargo di 7 giorni. Invalid per Hague-Visby Art. III(3) | Lettera scritta CMA-CGM **OR** OisteBio shipping che spieghi discrepanza 7gg (es. BL preliminare + amendment, data load effettiva). Allegare amendment BL se esiste. | Spiegazione scritta archiviata in `data/customs/c-<id>/` + flag su shipment_leg `bl2_amendment_ref` aggiornato | Marco (logistica) + Paolo countersign | 🔴 |
| **D** | `byproduct_sale`: 0 righe attive (58 esistono, tutte soft-deleted test data 2026-05-24). Nessun ledger di vendita frazione fossile, nessuna prova di non-double-counting con syngas energy claim | Invoice / fatture vendita byproduct fossili Q3 2025 (es. char, syngas burnt-for-power non claimato). Min: 1 invoice/mese × 3 mesi = 3 PDF + dati controparte. | Backfill `byproduct_sale` con ≥3 righe attive Q3 con `invoice_pdf_ref` non-null | Paolo + Marco | 🔴 |
| **E** | ISCC registry screenshot per cert. PDFs già linkati post-0038 (16/16 active con `pdf_ref`), ma screenshot registry ISCC `https://www.iscc-system.org/certificates/all-certificates/` mancanti per verifica indipendente | Screenshot per ciascun cert Q3 attivo (16 cert): URL ISCC system + cert number + holder + valid_from/valid_to + scope text. Format: PDF print del registry page con timestamp. | Drop screenshots in `data/certificates/registry-screenshots/<cert_number>.pdf` per tutti 16 cert | Paolo (auth ISCC system) | 🟡 |
| **G** | 20/20 PoS portano GHG identici (`ghg_total = 16.95 gCO2eq/MJ`, `ghg_saving_pct = 81.96 %`). Statisticamente impossibile su 6 supplier × 74 days × 2 batch × 3 mesi. Indicates hard-coded default | (a) Working paper per-PoS GHG calc sotto RED II Annex V Part C con: feedstock supply chain (eec), processing (ep), transport (etd), credits (eccs/eccr). Min 1 paper per supplier × Q3 = 6 paper. (b) Range realistico atteso post-recalc (es. 14-22 gCO2eq/MJ). | Allegare 6 working paper PDF in `data/customs/ghg-recalc/` + UPDATE points_of_sustainability con `ghg_total` ricalcolato per PoS | Paolo (responsabile sustainability) | 🔴 |
| **H** | 5/8 cert PDF sono **ISCC PLUS** (circular plastics scheme), ma DB ha `scheme='ISCC EU'`. Cert affected: LITOPLAS (CO222-00000026), ESENTTIA (CO222-00000027), KALTIRE (US201-138762025), EFFICIEN (US201-158772025), BOLDER (US201-120372025). ISCC PLUS **non qualifica** per UK RTFO sustainability. | Per ciascun cert mismatch, scelta: (a) PDF corretto ISCC EU esiste e va sostituito — fornire PDF; (b) Supplier ha solo ISCC PLUS — re-classificare scheme in DB + downgrade RTFC eligibility; (c) Documento ISCC PLUS è downstream documentation (es. plastica output che andrà a ELT) e supplier ha ISCC EU separato — fornire ISCC EU + nota di relazione. | Decisione documentata per ciascun cert in `certificates.notes` + migration `0039_scheme_realignment` se applicabile | Paolo | 🔴 |

---

## Risk se cliente non risponde entro 2026-06-05

| F0 | Conseguenza no-response |
|----|--------------------------|
| A | LE5TON 1,226,479 kg deve essere ri-classificata non-sustainable di default. Claimable share Q3 cala drasticamente. |
| B | RTFO ELT eligibility blocca: senza C14 sostegno, DfT respinge feedstock origin claim. |
| C | BL2 14 container restano contestabili. Crown Oil potrebbe rifiutare quel sotto-bundle. |
| D | Syngas double-claim risk apertо. Auditor segnala violazione metodologia mass balance. |
| E | F0-E retrocede da PARTIAL ACCEPT a REJECT in round-3. |
| G | RED II Annex V Part C non rispettata. Bundle GHG figures contestabili. |
| H | 5 supplier su 8 documentati con schema sbagliato. Auditor cross-check ISCC portal in 30 sec, bundle respinto. |

---

## Sequencing post-risposta

1. **A + H** prima — bloccanti hard, gate per qualsiasi re-submission.
2. **B + D + G** in parallel — sostanza tecnica chain-of-custody.
3. **C + E** ultimi — patchable con statement scritto se artefatto primario non disponibile.

---

## Output verifica chiusura

Dopo risposta cliente:
- ogni F0 chiuso aggiorna `docs/audit-dft-c1-evidence-matrix.md` §9.1
- Plane ticket #<TBD> linkato in evidence matrix §10 (nuova sezione)
- Round-3 red-team pass con bundle aggiornato
- Se tutti F0 chiusi → Step 8 Statement rewrite → Step 9 Drive replace + Paolo signature → Crown Oil handover

---

**Plane ticket fields suggested**:
- Project: DFTEN
- Title: `[AUDIT-C1] F0-A..H Cliente input batched`
- Priority: Urgent
- Due date: 2026-06-05
- Assignee: Paolo Ughetti
- Watchers: Hugo, Ferdinando, Marco, Gianni
- Description: link a questo file (`docs/audit-dft-c1-f0-questionnaire.md`) + tabella sopra inline
