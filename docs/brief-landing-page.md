# Brief Landing Page — OisteBio GmbH

## Cliente

**OisteBio GmbH** (Germania)
**Tagline:** "Fuel for your future"
**Logo:** anello dorato + testo nero/blu/arancio
**Palette suggerita:**
- Oro/Bronzo (logo): `#B87E2A` circa
- Blu chiaro: `#5BC4D9` circa
- Arancio: `#E89540` circa
- Nero/grigio scuro testi

## Scopo

Sito vetrina pubblico → presenta soluzione DFT (mass balance + tracciabilità ISCC per impianti pirolisi) a clienti potenziali (operatori impianti biofuel, raffinerie EU, certificatori).

**NON è il login app.** App live su subdomain dedicato (es. `app.oistebio.com`), landing su root (`oistebio.com`).

## Audience

1. **Operatori impianto** — vogliono vedere se risolve problema mass balance/audit
2. **Compliance officer** — cercano conformità ISCC + RED II
3. **Decision maker** (CEO/CTO) — vogliono valore business + ROI
4. **Raffinerie EU** — buyer biofuel, vogliono garanzia tracciabilità

## Tono

Tecnico-professionale, non marketing fluff. Numeri reali (es. "8M kg tracciati 2024"). No claim non verificabili.

## Sezioni

### 1. Hero
- Logo OisteBio
- Headline: "Fuel for your future"
- Subhead: "Tracciabilità ISCC + EU RED II per export biofuel da pirolisi"
- CTA primario: "Request demo"
- CTA secondario: "Technical docs"
- Visual: dashboard mockup + foto impianto Girardot

### 2. Problema
3 pain point operatori:
- Mass balance manuale Excel = errori + audit failure
- C14 lab esterno scollegato da gestionale
- POS docs export EU rigenerati a mano = lentezza + rischio compliance

### 3. Soluzione
4 feature chiave:
- **Tracciabilità carico-per-carico** (timestamp, supplier, certificato, eRSV, POS)
- **Mass balance automatico** con closure mensile/annuale e tolerance check
- **Integrazione lab terzo** (C14 Saybolt NL, sign-off digitale)
- **Audit immutabile** append-only conforme ISCC

### 4. Compliance
Loghi/badge: ISCC EU, EU RED II Directive 2018/2001
Frase: "Audit-ready certifier"

### 5. Stack tecnico (sezione developer/CTO)
Next.js + FastAPI + Postgres — open source, self-host o managed

### 6. Case study
**Girardot, Colombia** — impianto pirolisi OisteBio
8.011.725 kg input 2024 → 2.563.752 kg OUTPUT EU certificato
Suppliers: ESENTTIA, LITOPLAS, BIOWASTE

### 7. Pricing
Placeholder o "Contattaci" finché modello non definito

### 8. FAQ
- Quanto tempo deploy? — 2-4 settimane
- On-premise o cloud? — entrambi
- Esiste API? — sì, REST
- Multi-impianto? — roadmap
- Lingue? — IT/EN

### 9. Footer
Contatti OisteBio GmbH (sede DE), privacy GDPR, terms, link app login, social (LinkedIn)

## Stack landing

Diverso da app, ottimizzato SEO + speed:
- **Next.js 14** (stesso ecosystem, SSG)
- **Tailwind + shadcn/ui** (coerenza visuale con app)
- **MDX** per blog/docs futuri
- **Plausible** o **Umami** analytics (no Google, GDPR-friendly per cliente DE)
- **Vercel** o stesso server FastAPI

## Branding

- Font: sans-serif moderno (Inter, Geist, Manrope)
- Logo OisteBio in header sticky
- Tagline "Fuel for your future" prominente in hero
- Palette ispirata al logo (oro + blu + arancio su sfondo bianco/nero)
- Animazione subtle anello dorato (parallax o lottie)

## SEO

Keyword target (EN primary):
- "mass balance pyrolysis software"
- "ISCC compliance biofuel"
- "EU RED II tracking system"
- "pyrolysis plant management"
- "biofuel traceability software"

Lingua: **EN primary** (mercato EU + global), DE + IT secondarie (cliente tedesco, impianto colombiano-italiano).

## Performance

- Lighthouse > 95
- LCP < 1.5s
- No tracker pesanti
- Image optimization next/image
- GDPR cookie banner minimale

## Deliverable

1. Hero + 8 sezioni responsive
2. Form contatto (no DB, → email/Resend a OisteBio)
3. Blog MDX scaffold (vuoto, post futuri)
4. Sitemap + robots.txt + Open Graph
5. Cookie banner GDPR
6. Deploy Vercel o Hetzner
7. Lighthouse report > 95
8. Tema dark mode opzionale

## Asset richiesti
- Logo OisteBio HD (vector preferito) — già fornito JPEG
- Foto impianto Girardot (chiedi BiNova/Andrea)
- Screenshot dashboard app (quando pronta)
- Testimonial + foto team OisteBio (opzionale)
- Hero photography pirolisi/biofuel/sostenibilità

## Repo
Separato: `callopiumcreme/oistebio-website` (consigliato) o subfolder `marketing/` nel repo app `dft-project`.

## Domain

Da definire con cliente:
- `oistebio.com` (probabile primary)
- `oistebio.de` (DE locale)
- App: `app.oistebio.com`
