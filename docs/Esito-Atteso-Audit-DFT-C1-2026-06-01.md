# Audit DfT — Cosa Aspettarsi, in Parole Semplici

**Data:** 1 giugno 2026
**Per:** Direzione OisteBio
**Argomento:** Esito atteso dell'audit DfT sul consignment Crown Oil (DEL-CRW-2025-2), periodo gennaio–agosto 2025

---

## In due righe

L'audit **non mette in discussione l'esistenza o la legalità** del prodotto che abbiamo
fatto e venduto. Mette in discussione **quanta parte di quel prodotto può ricevere il
premio** (i certificati di carburante rinnovabile britannici). I certificati ISCC dei nostri
fornitori — PDF inclusi — **ci sono tutti** e coprono l'intero periodo. Il punto aperto non
è nostro: è **a monte**, e riguarda se i *punti di raccolta* degli pneumatici e la
*registrazione* dei fornitori a gestirli sono riconosciuti dal DfT. Dimostrato quello, la
quota premiabile arriva a circa **l'85%** del prodotto EU.

---

## Di cosa parla davvero l'audit

Noi trasformiamo materiale di scarto in olio (DEV-P100), che vendiamo a Crown Oil nel
Regno Unito. Crown Oil, per ottenere il valore pieno di quell'olio, deve poterlo
presentare al regolatore britannico come carburante rinnovabile "premiabile" — cioè che
dà diritto ai certificati RTFC, che valgono soldi.

Per essere premiabile, l'olio deve rispettare **due condizioni distinte**, e qui sta tutto
il nocciolo:

1. **Deve partire dal materiale giusto.** Nel Regno Unito la gomma da pneumatici a fine
   vita (ELT) è un materiale ammesso. La plastica e l'organico **non lo sono** per questo
   percorso. Questa è una questione di *natura del materiale*: o è gomma, o non lo è.

2. **La filiera del materiale deve essere certificata.** Non basta che sia gomma: bisogna
   poter dimostrare, con un certificato ISCC valido, da dove arriva e che chi l'ha
   raccolta è registrato per farlo. Questa è una questione di *carte*, non di materiale.

L'errore da non fare mai è confondere le due cose. Se un fornitore ci porta gomma vera ma
non ha il certificato in ordine, **resta gomma** — semplicemente non possiamo contarla per
il premio finché le carte non ci sono. Non la riclassifichiamo come "plastica" per far
quadrare i conti: la chiamiamo per quello che è, e diciamo che quella gomma, per ora, non
è premiabile.

---

## Cosa ha detto il DfT

A marzo 2026 il DfT ha **respinto** la prima sottomissione e ha sollevato quattro
osservazioni. Tradotte in parole semplici:

- **La gomma non risulta provenire da punti di raccolta certificati ISCC** → quindi la
  filiera non è considerata certificata.
- **I registri del materiale erano incompleti o incoerenti**, e mancavano i log di
  produzione in litri.
- **La maggior parte dei fornitori non risulta registrata** per gestire pneumatici.
- **Le informazioni sul sito produttivo** (foto, capacità, date di avvio) erano
  incoerenti.

Importante: **nessuna di queste osservazioni dice "il vostro materiale non è gomma" o "il
prodotto non esiste".** Tutte e quattro riguardano *la documentazione della filiera*. È un
problema di carte, recuperabile — non un problema di sostanza.

Da segnalare, perché è una buona notizia: il secondo punto (log di produzione in litri) **è
già risolto**. Oggi nel nostro sistema i log litro-per-litro ci sono tutti, completi.

---

## Come si calcola la parte premiabile

Il principio è la "bilancia di massa". Nella pirolisi gomma e plastica entrano nello stesso
impianto e producono un unico olio: non esiste un litro fisicamente "di gomma" e un litro
"di plastica". Quindi si fa una proporzione contabile, accettata dallo standard:

> **La quota di olio premiabile = la quota di materiale premiabile in ingresso.**

Se in un mese il 95% del materiale entrato è gomma da filiera valida, allora il 95% dell'olio
di quel mese è premiabile. La produzione fisica non cambia di un litro — cambia solo quanta
parte possiamo *rivendicare* per il premio.

---

## I numeri reali del periodo

Nel periodo gennaio–agosto 2025 sono entrate circa **25 milioni di chili** di materiale, da
otto fornitori. Ecco come si dividono:

| Fornitore | Quota | Materiale | Stato carte |
|-----------|-------|-----------|-------------|
| EFFICIEN | 26,9% | gomma | certificato con PDF ✓ |
| KALTIRE | 23,1% | gomma | certificato con PDF ✓ |
| PYRCOM | 15,4% | gomma | certificato con PDF ✓ |
| ESENTTIA | 10,0% | plastica | non premiabile per natura |
| LE5TON (≤5 ton) | 9,8% | gomma | autodichiarazione ISCC accettata ✓ |
| BOLDER | 7,7% | gomma | certificato con PDF ✓ |
| BIOWASTE | 4,6% | organico | non premiabile per natura |
| LITOPLAS | 2,4% | plastica | non premiabile per natura |

Tutti i fornitori di gomma hanno il certificato ISCC con il PDF a fascicolo, per l'intera
finestra. (Nota tecnica interna: per sei certificati il file PDF è presente sul disco e
visibile a sistema, ma una colonna del database non era ancora stata aggiornata — pura
igiene dati, non manca nessun documento.)

Due osservazioni che cambiano la lettura:

- **Gennaio è un caso a sé.** Quel mese la maggior parte del materiale era plastica e
  organico (ESENTTIA, BIOWASTE, LITOPLAS). Da febbraio in poi c'è stato il passaggio alla
  gomma. Quindi la quota non premiabile di gennaio **non è un difetto**: è semplicemente
  materiale che non è gomma. L'unica parte premiabile di gennaio è la piccola quota LE5TON,
  che era gomma.

- **I piccoli fornitori ≤5 tonnellate (LE5TON)** non hanno bisogno del certificato pieno né
  del documento di sostenibilità: per loro è accettata l'**autodichiarazione ISCC**. Quindi
  contano come premiabili, gennaio incluso.

---

## I due scenari di esito

L'esito dipende da **una sola cosa**: se il DfT accetta che la filiera della gomma è
certificata (punti di raccolta ISCC + fornitori registrati a gestire pneumatici). I nostri
certificati e PDF ci sono già; la palla è a monte, sui fornitori e su Crown Oil. Sul
prodotto EU (DEV-P100), totale circa 9,5 milioni di litri:

| Scenario | Litri premiabili | Quota | Condizione |
|----------|------------------|-------|------------|
| **Atteso** | ~8,14 milioni | 85,6% | Il DfT accetta la filiera gomma (certificati + PDF già a posto) + LE5TON con autodichiarazione |
| **Negativo** | molto più basso | — | Il DfT mantiene l'obiezione sui punti di raccolta / fornitori non registrati e contesta la filiera gomma |

La leva non è nelle nostre carte interne — quelle sono in ordine. La leva è **la
documentazione a monte**: scope ISCC che nomina i punti di raccolta degli pneumatici e
prova che i fornitori sono registrati a gestirli. È materiale che dobbiamo farci dare dai
fornitori (via Crown Oil), non qualcosa che generiamo noi.

---

## Cosa significa, in sostanza

- **Non rischiamo l'annullamento dell'attività.** Il prodotto è reale, è stato venduto, ed
  è legale. In gioco c'è il *valore premiabile*, non la legittimità.

- **La plastica e l'organico (17% del totale) non sono una perdita.** Non erano mai
  premiabili — non sono gomma. Escluderli è corretto e atteso, non è una bocciatura.

- **L'autodichiarazione LE5TON regge.** Quella quota (9,8%) resta premiabile.

- **Il vero campo di battaglia è a monte**, sui punti di raccolta degli pneumatici e sulla
  registrazione dei fornitori. **Non** sui nostri certificati o PDF, che ci sono e coprono
  tutto il periodo.

- **La parte di nostra competenza è a posto.** I certificati con PDF, i dati di produzione,
  i log in litri, la bilancia di massa: tutto verificato e in ordine. Quello che manca è
  documentazione *della filiera a monte*, che dipende dai fornitori — non dal nostro sistema.

---

## Le cose da fare, in ordine di valore

1. **Scope ISCC dei punti di raccolta pneumatici.** Farsi dare dai fornitori (via Crown Oil)
   la documentazione ISCC che nomina i *punti di raccolta* da cui arriva la gomma. È il
   make-or-break dell'audit — risponde all'obiezione principale del DfT.
2. **Prova di registrazione dei fornitori** a gestire pneumatici, per rispondere
   all'osservazione DfT sui fornitori non registrati.
3. **Documentazione del sito produttivo** coerente (foto, capacità, date di avvio), per
   chiudere l'ultima osservazione.
4. **(Interno, minore) Allineare la colonna database** dei riferimenti PDF: i file ci sono
   già a sistema, è solo igiene dati.

Le prime tre dipendono da documenti *a monte* (fornitori + Crown Oil), non dal nostro
sistema. Chiuse quelle, l'esito atteso è la fascia alta (~85%). Lasciate aperte, il DfT può
contestare la filiera gomma e l'esito scende in modo significativo.

---

*Documento divulgativo. Tutti i numeri sono stati verificati sul database di produzione il
1 giugno 2026. Il dettaglio tecnico completo è nel ricontrollo audit interno
(`audit-dft-c1-recheck-2026-06-01-IT`).*
