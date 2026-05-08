# Sprint 3 — Frontend dashboard integrato

**Stato:** Pianificato
**Data avvio prevista:** 2026-05-08
**Obiettivo:** Estendere `landing/` (Next.js 14) con area protetta `/app/*` per visualizzazione dati DB, mantenendo deploy unificato su `oistebio.usenexos.com`.

---

## 1. Approccio architetturale

**Decisione**: single Next.js app. NO progetto frontend separato. Riusiamo `landing/` come app unica.

**Razionale**:
- Landing già rodata (Next 14 App Router, Tailwind, TypeScript, deploy PM2 + nginx + LE).
- Single domain → no CORS, single build pipeline, single PM2 process.
- Marketing e dashboard condividono primitives UI, layout shell, fonts, design tokens.
- Login dalla landing → flow utente naturale per cliente.

**Struttura route Next.js**:

```
landing/src/app/
├── (marketing)/            # pubblico — esistente
│   ├── page.tsx            # /
│   └── blog/               # /blog/*
├── login/
│   └── page.tsx            # /login (pubblico)
├── (app)/                  # PROTETTO — middleware enforcement
│   ├── layout.tsx          # sidebar nav + topbar user menu
│   ├── page.tsx            # /app — dashboard home (KPI)
│   ├── reports/
│   │   ├── mass-balance/   # /app/reports/mass-balance
│   │   ├── by-supplier/    # /app/reports/by-supplier
│   │   └── closure-status/ # /app/reports/closure-status
│   ├── suppliers/          # /app/suppliers (read-only Sprint 3)
│   ├── certificates/
│   └── contracts/
├── api/
│   ├── contact/            # esistente
│   └── auth/
│       ├── login/route.ts  # POST → forward a FastAPI /auth/login → set httpOnly cookie
│       ├── logout/route.ts # clear cookie
│       └── me/route.ts     # GET → forward /auth/me con cookie
└── middleware.ts           # protegge /app/*, redirect /login?next=
```

**Sicurezza auth**:
- JWT salvato in **httpOnly + Secure + SameSite=Lax cookie** (no localStorage — XSS-safe).
- Cookie inviato come `Authorization: Bearer ${jwt}` solo dai route handler server-side, mai esposto al client JS.
- Middleware Next legge cookie, valida `exp` claim, redirect se mancante/scaduto.
- Backend FastAPI accessibile via `BACKEND_URL` env var, mai chiamato direttamente dal browser.

**Backend connection**:
- Dev: `BACKEND_URL=http://localhost:18000` (Docker port mapping)
- Prod: `BACKEND_URL=http://127.0.0.1:8000` (stesso host Hetzner) o subdomain dedicato con TLS

---

## 2. Stack additions

| Lib | Motivo |
|-----|--------|
| shadcn/ui | UI primitives (Tailwind-native, Radix-based — `Button`, `Input`, `Form`, `Table`, `Card`, `Toast`, `Dialog`, `Select`) |
| react-hook-form | Form state |
| zod | Schema validation (riusabile client + API route handlers) |
| @tanstack/react-table v8 | Tabelle filtrate/ordinate |
| @tanstack/react-query v5 | Cache + revalidation client-side per dati interattivi |
| recharts | Grafici (line, bar, pie) |
| jose | JWT verify nel middleware (lightweight, edge-compatible) |
| date-fns | Formattazione date |

Già presenti: `@radix-ui/react-accordion`, `@radix-ui/react-label`, `@radix-ui/react-slot`, `class-variance-authority`, `clsx`, `lucide-react`, `tailwind-merge`.

---

## 3. Issues Plane (DFTEN-72..81)

### S3-1: Setup shadcn/ui + base UI primitives
**Scope**: Install shadcn/ui CLI, init `components.json`, generare componenti base in `src/components/ui/`: `button`, `input`, `label`, `form`, `card`, `table`, `dialog`, `dropdown-menu`, `select`, `toast`, `badge`. Verifica integrazione con design tokens esistenti (`var(--bg)`, `var(--ink)`, etc).
**Acceptance**: pagina `/dev/ui-test` (rimossa pre-merge) renderizza tutti i primitives senza regressione su `/`.

### S3-2: API client lib + tipi backend
**Scope**: Creare `src/lib/api.ts` typed fetch wrapper. Genera types dal backend OpenAPI (`/openapi.json`) via `openapi-typescript`. Helper functions: `apiGet<T>(path, opts)`, `apiPost<T,B>(path, body)`, `apiPatch`, `apiDelete`. Auth header injection automatica via cookie reading (server-only). Error handling: throw tipizzato `ApiError(status, code, detail)`.
**Acceptance**: tipi generati per `/reports/*`, `/suppliers`, `/daily-inputs`, `/daily-production`, `/auth/*`. `apiGet('/health')` testato.

### S3-3: Auth flow login/logout
**Scope**: Pagina `/login` form (RHF + zod schema email/password). Route handler `/api/auth/login/route.ts` POST → forward a `${BACKEND_URL}/auth/login` → ricevi JWT → set cookie httpOnly Secure SameSite=Lax con `Max-Age` da JWT exp. `/api/auth/logout/route.ts` POST → cookie clear. `/api/auth/me` GET proxy con cookie.
**Acceptance**: login con `admin@dft.test / admin` → cookie set → redirect `/app`. Logout → cookie cleared → redirect `/`. Cookie marcato HttpOnly verificato in DevTools.

### S3-4: Middleware route protection
**Scope**: `landing/middleware.ts` matcher `/app/:path*`. Legge cookie `dft_session`, verifica JWT con `jose.jwtVerify` usando JWT_SECRET env. Se mancante/invalido/scaduto → 302 `/login?next=${pathname}`. Se valido → next() con header `x-user-role` per RSC.
**Acceptance**: GET `/app/dashboard` senza cookie → 302 `/login`. Con cookie valido → 200. Con cookie scaduto → 302 `/login` + cookie cleared.

### S3-5: Dashboard layout shell
**Scope**: `(app)/layout.tsx` con sidebar fissa left (logo + nav: Dashboard, Reports submenu, Anagrafiche submenu) + topbar (breadcrumb + user dropdown con email + logout). Responsive: sidebar collassabile su mobile (sheet Radix). Design coerente con landing (font + colors).
**Acceptance**: navigazione tra `/app`, `/app/reports/mass-balance`, `/app/suppliers` mantiene layout. Logout funzionante.

### S3-6: Dashboard home — KPI cards
**Scope**: `(app)/page.tsx` server component. Fetch `/reports/mass-balance/daily?limit=30` + `/reports/closure-status?date_from=...`. Render 4 KPI cards (`<Card>`): Input totale ultimi 30g, Output totale, Closure % media, Alert count (giorni `bucket=alert`). Sotto: sparkline Recharts input vs output (line chart).
**Acceptance**: pagina render <500ms con dati seed. Card formattate con thousand separator IT.

### S3-7: Report mass balance daily/monthly
**Scope**: `(app)/reports/mass-balance/page.tsx` con tab switch daily/monthly. Date range picker (default ultimi 30g). TanStack Table v8: colonne dinamiche da schema `MassBalanceDailyRow`/`MassBalanceMonthlyRow`. Sticky header, sorting, paginazione 50 righe/pagina. Pulsante "Export CSV" client-side.
**Acceptance**: filtri date funzionanti, ordinamento per ogni colonna, CSV scarica con encoding UTF-8 BOM (compatibile Excel).

### S3-8: Report by-supplier (chart + table)
**Scope**: `(app)/reports/by-supplier/page.tsx`. Date range picker. Pie chart Recharts (% input per fornitore — top 7 + "Altri" aggregato). Sotto, tabella ranking con `supplier_code`, `supplier_name`, `total_input_kg`, `entries`, `days`. Click su slice pie → highlight riga tabella.
**Acceptance**: chart renderizza con dati seed, hover tooltip mostra valore + %.

### S3-9: Report closure-status (semaforo)
**Scope**: `(app)/reports/closure-status/page.tsx`. Date range picker. Tabella con colonne `day`, `input_kg`, `output_kg`, `closure_diff_pct`, `bucket`. Bucket renderizzato come `<Badge>` colorato (ok=green, warn=yellow, alert=red, no_input/no_output=gray). Filtro per bucket.
**Acceptance**: ogni bucket ha colore distinto e label IT (`Ok` / `Attenzione` / `Allerta` / `Nessun input` / `Nessun output`).

### S3-10: Anagrafiche read-only viewer
**Scope**: `(app)/suppliers/page.tsx`, `(app)/certificates/page.tsx`, `(app)/contracts/page.tsx`. Liste TanStack Table con search box + filtri base. Solo read — CRUD posticipato a Sprint 4. Link a `/app/suppliers/[id]` con detail view (read-only).
**Acceptance**: tutte le tre pagine listano dati seed correttamente, link detail funzionanti.

---

## 4. Out of scope (rimandato Sprint 4+)

- CRUD anagrafiche (suppliers/contracts/certificates) — solo read in Sprint 3
- Form daily_inputs / daily_production data entry
- Bulk paste from Excel
- PDF generation
- Audit log viewer admin
- i18n IT/EN switcher (UI EN-only per Sprint 3, IT solo per labels report già localizzate)
- Dark mode
- Mobile responsive avanzato (basic only)
- E2E Playwright tests

---

## 5. Definition of Done — Sprint 3

- [ ] Tutti i 10 issue chiusi in Plane
- [ ] `npm run build` zero errori TypeScript
- [ ] `npm run lint` zero warnings
- [ ] Login + logout end-to-end testato manualmente
- [ ] 4 pagine report renderizzano dati reali da backend
- [ ] Middleware protegge `/app/*` correttamente
- [ ] Landing pubblica `/` non rotta da modifiche
- [ ] Commit puliti, no `.env` né `node_modules` committati
- [ ] Aggiornato `CLAUDE.md` con stato sprint
- [ ] Smoke test deploy locale: `landing/` build + start su port 3020 → `/login` → `/app`

---

## 6. Dipendenze

- Backend running su `localhost:18000` (Docker compose backend service)
- DB con seed Sprint 1 (utente `admin@dft.test` con password set)
- Materialized views populated (eseguire `POST /admin/refresh-mvs` se vuote)
- Variabili env in `landing/.env.local`:
  ```
  BACKEND_URL=http://localhost:18000
  JWT_SECRET=<stesso secret backend>
  COOKIE_SECRET=<random 32+ chars>
  ```

---

## 7. Rischi

| Rischio | Mitigazione |
|---------|-------------|
| JWT_SECRET disallineato backend/frontend | Documentare in `.env.example`, validate in middleware startup |
| Conflitto routing landing vs `/app` | Prefisso route group `(app)` non genera segment URL, `/app` solo via `app/(app)/page.tsx` esplicito |
| TanStack Query SSR hydration mismatch | Usare server prefetch + `HydrationBoundary` per pagine con dati iniziali |
| Bundle size esplode con shadcn + recharts + tanstack | Monitor `next build` output, lazy-load chart components con `dynamic()` |
| Deploy prod richiede env vars nuovi | Update memory `reference_oistebio_landing.md` con BACKEND_URL prod + JWT_SECRET sync procedure |
