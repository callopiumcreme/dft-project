# Brief DFT Project — Web Developer

Ciao, devo realizzare un sistema web per tracciabilità mass balance di un impianto di pirolisi industriale. Cliente è OisteBio GmbH (Germania, tagline "Fuel for your future"), l'impianto sta a Girardot in Colombia, processa plastiche miste e produce olio pirolitico che viene esportato a raffinerie europee come biofuel. Tutto deve essere conforme a ISCC ed EU RED II, quindi audit immutabile e chiusura mass balance certificabile.

Il flusso è: arrivano carichi di plastica da fornitori (ESENTTIA, LITOPLAS, BIOWASTE), ogni carico ha certificato, contratto, eRSV, POS, trasporto (CAR/TRUCK/SPECIAL) e kg in ingresso. L'impianto lavora il materiale e produce output diviso in bucket: EU PROD (compliant export EU), PLUS PROD (premium), Carbon Black (residuo solido), Metal scrap, più percentuali H2O e Gas/Syngas, e Losses. Il dato chiave finale è OUTPUT EU Kg, il biofuel certificato per export.

C'è un laboratorio terzo (Saybolt NL) che fa analisi C14 sui campioni per verificare la frazione biogenica — solo loro possono marcare un lotto come "verified". Il sistema deve gestire upload referti e firma certifier.

Stack richiesto: Next.js 14 App Router con Tailwind e shadcn/ui per il frontend, TanStack Table per le tabelle dati e TanStack Query per le chiamate. Backend FastAPI 0.111 in Python 3.12 con SQLAlchemy 2.0. Database Postgres 16. PDF generati con WeasyPrint per i POS documents. Repo già su GitHub: `callopiumcreme/dft-project`.

Servono 4 ruoli: admin (BiNova full access), operator (operatori impianto, inseriscono carichi e produzione giornaliera), certifier (Saybolt, sign-off C14), viewer (cliente EU, read-only POS). Auth con NextAuth.

Pagine da fare: login, dashboard con KPI mese (input/output kg + % closure mass balance + alert anomalie), gestione loads (CRUD con filtri), produzione giornaliera (calcolo bucket automatico), stock (cumulato + grafico Recharts), mass balance (chiusura mensile/annuale con drill-down), POS documents (lista + genera PDF), suppliers (anagrafica), C14 analysis (upload + link a lotto), audit log immutabile.

Vincoli compliance non negoziabili: log append-only, niente UPDATE/DELETE su record certificati, mass balance closure con tolerance configurabile + alert se sforata, POS immutabile post-firma. UI italiana per operatori, inglese per documenti export.

Come sample data c'è un file Excel reale `Girardot producciòn Enero 2025.xlsx` (Google Drive ID `1FWeZs6nxmM_STzFZLGFVpPCBU877Uukw`) che mostra il bilancio YE 2024: 8.011.725 kg input contro 2.475.623 kg EU + 2.972.349 kg PLUS + 2.563.752 kg OUTPUT EU. Da lì estrai schema e validation rules.

Sprint 1 deliverable: schema Postgres con migration Alembic, seed suppliers e ruoli, auth NextAuth con 4 ruoli, CRUD loads + production, test E2E Playwright golden path.

Riferimenti tecnici: blueprint completo in `BLUEPRINT.md` nel repo, specifica ISCC su `iscc-system.org`, EU RED II Directive 2018/2001 su `ec.europa.eu`.
