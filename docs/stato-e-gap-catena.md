# DFT — Visione d'insieme & Gap Analysis catena di custodia

> **Scopo:** capire dove siamo, cosa copre il sistema oggi e cosa manca rispetto alla catena fisica/documentale reale ELT → Girardot → Crown Oil UK.
> **Data:** 2026-05-22 · **Branch:** `main` · **Ambiente live:** https://oistebio.usenexos.com

---

## 1. La catena reale (fisica + documentale)

```
 [A] FORNITORE ELT (Colombia)                       [F] UTB BV — Dordrecht (NL)
     eRSV inbound + Certificato ISCC + PoS               travaso ISO→ISO
                 │                                        23.000 kg  →  27.000 kg
                 ▼                                        (ottimizzazione costi)
 [B] GIRARDOT — ricezione                                       │
     daily_inputs (data/ora, peso, cert, PoS)                   ▼
                 │                                       [G] USCITA UE → UK
                 ▼                                            MRN + BL (Rotterdam → UK)
 [C] GIRARDOT — lavorazione (pirolisi)                          │
     daily_production (DEV-P100 ~30%, DEV-P200, co-prod)        ▼
                 │                                       [H] CONSEGNA Crown Oil — Bury (UK)
                 ▼                                            commercial invoice + batch docs
 [D] VENDITA UE → Crown Oil
     (frazione EU certificata)
                 │
                 ▼
 [E] EXPORT Colombia → Cartagena
     eRSV OUTBOUND OisteBio → porto
     Port RSV + BL transoceanico (Cartagena → Rotterdam)
```

Sequenza completa: **A → B → C → D → E → (transoceanico) → F → G → H**.

---

## 2. Cosa copre il sistema OGGI

| Nodo | Documento / dato | Stato nel sistema | Dove |
|------|------------------|-------------------|------|
| **[A]** Fornitore | eRSV inbound | ✅ `daily_inputs.ersv_number` + renderer eRSV (HTML/PDF) | `routers/ersv.py`, `services/ersv_renderer.py` |
| **[A]** Fornitore | Certificato ISCC EU | ✅ tabella `certificates` + `supplier_certificates` (M2M) | `models/certificate.py` |
| **[A]** Fornitore | PoS (proof of sustainability) | ⚠️ **parziale** — link al certificato sì, ma nessun archivio documento PoS per lotto | — |
| **[B]** Girardot ricezione | data/ora, peso (car/truck/special), cert, contratto | ✅ `daily_inputs` (total_input_kg generated) | `models/daily_input.py` |
| **[C]** Girardot lavorazione | output DEV-P100/P200 + carbon black, syngas, H₂O, scarti | ✅ `daily_production` + densità kg↔litri | `models/daily_production.py`, migr. 0005 |
| **[C]** | chiusura mass-balance giornaliera/mensile | ✅ MV `mv_mass_balance_*` + report | `routers/reports.py` |
| **[C]** | C14 biogenico | ✅ `daily_inputs.c14_value / c14_analysis` | — |
| **tutti** | audit trail (chi/quando/cosa) | ✅ `audit_log` immutabile + export | `models/audit.py`, `routers/admin.py` |

**Confine effettivo del sistema oggi:** finisce a **[C]** — output di produzione. Tutto ciò che è a valle è descritto solo a parole nella nota chain-of-custody (`docs/rtfo-chain-of-custody-note-EN.md`), **non è modellato come dato**.

---

## 3. Cosa MANCA — la gamba a valle (D → H)

Nessuna di queste entità esiste in DB, API o frontend. Esistono solo come prosa nella nota CoC e nel bundle `deliverables/RTFO-310825/.../transport/transport_note.md`.

| # | Nodo | Documento mancante | Impatto |
|---|------|--------------------|---------|
| **G1** | **[D]** Vendita | Entità **off-taker Crown Oil** (anagrafica buyer, contratto di fornitura UK) | Nessun legame output→buyer; Crown Oil non è un record |
| **G2** | **[E]** Export | **eRSV OUTBOUND** OisteBio → porto + **Port RSV Cartagena** | L'eRSV in app è solo *inbound* (fornitore→Girardot). Il documento d'uscita è un tipo distinto, non esiste |
| **G3** | **[E]** Export | **Bill of Lading transoceanico** (Cartagena → Rotterdam) | Nessun modello BL; vettore/nave/voyage solo in nota testuale |
| **G4** | **[F]** UTB BV | **Nodo repackaging Dordrecht**: travaso **ISO 23.000 kg → ISO 27.000 kg** | **Punto critico ISCC mass-balance**: la continuità di massa nel travaso non è tracciata. Serve evidenza che la massa entrata = massa uscita nel cambio packaging |
| **G5** | **[G]** Uscita UK | **MRN** (export/customs UK) + **BL Rotterdam → UK** | Nessuna entità doganale; MRN non compare in nessun file |
| **G6** | **[H]** Consegna | **Consegna Crown Oil Bury** + **commercial invoice** | Nessun record consegna finale |
| **G7** | trasversale | Entità **batch / consignment** che leghi `daily_production` (output) → spedizione → travaso → consegna | Senza questa, **impossibile la ricostruzione end-to-end** che la nota CoC dichiara |

### Il gap strutturale (la radice)

Tutti i G1–G7 discendono da un'unica mancanza: **non esiste l'oggetto "lotto/spedizione di prodotto finito"**. Il sistema sa quanto si produce al giorno, ma non sa *come quel prodotto diventa una spedizione*, attraversa i nodi logistici e arriva a Bury. La catena è spezzata esattamente al passaggio **produzione → primo documento d'uscita**.

---

## 4. Mappa stato per documento (sintesi)

```
A  eRSV inbound .............. ✅
A  Cert ISCC ................. ✅
A  PoS ....................... ⚠️  (link sì, archivio doc no)
B  ricezione Girardot ........ ✅
C  produzione ................ ✅
C  mass-balance / C14 ........ ✅
─────────────  CONFINE SISTEMA ATTUALE  ─────────────
D  off-taker Crown Oil ....... ❌
E  eRSV OUTBOUND ............. ❌
E  Port RSV Cartagena ........ ❌
E  BL transoceanico .......... ❌
F  UTB BV repackaging 23k→27k  ❌  ← critico mass-balance
G  MRN uscita UK ............. ❌
G  BL Rotterdam → UK ......... ❌
H  consegna Crown Oil Bury ... ❌
*  batch/consignment link .... ❌  ← gap strutturale radice
```

---

## 5. Cosa servirebbe per chiudere (proposta minima, non over-engineering)

Per coprire la gamba a valle senza stravolgere il modello:

1. **`consignment`** (lotto prodotto finito): id, prod_date range, kg/litri DEV-P100, link a `daily_production`.
2. **`off_taker`**: anagrafica buyer (Crown Oil Ltd, Bury UK) — già previsto Sprint 5 (migr. 0011).
3. **`shipment_leg`** (gamba logistica): consignment_id, tipo nodo (port_rsv / BL_ocean / repack_utb / MRN / delivery), riferimento documento, peso in/out, data. Una riga per nodo E→H.
4. **eRSV outbound**: estendere il renderer eRSV con un tipo `direction = outbound` oppure documento separato per l'uscita verso Cartagena.
5. **Vincolo mass-balance sul travaso UTB BV**: check kg_in (ISO 23k) = kg_out (ISO 27k) nel nodo `repack_utb`, con tolleranza, per preservare la continuità ISCC.

Con `consignment` + `shipment_leg` la ricostruzione end-to-end diventa una query, e la nota CoC smette di essere solo prosa.

---

## 6. Riepilogo in una riga

> **Monte e impianto (A–C) modellati e live. Tutta la logistica a valle (D–H) — eRSV outbound, Cartagena, BL, travaso UTB BV 23k→27k, MRN, consegna Bury — è solo documentale, non è dato.** Manca l'oggetto `consignment`/`shipment_leg` che lega produzione → spedizione → consegna. Quello è il buco.
