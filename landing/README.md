# DFT — Landing

Public marketing site for the **DFT Project** — mass balance and traceability
software for industrial pyrolysis plants exporting biofuel under
ISCC EU and EU RED II.

This repository is **only the marketing site** (`dft-project.com`).
The application itself lives on a separate subdomain
(`app.dft-project.com`) and a separate codebase (`callopiumcreme/dft-project`).

---

## Stack

- **Next.js 14** · App Router · static where possible
- **TypeScript** · strict
- **Tailwind CSS** + shadcn/ui (custom-tuned to the DFT palette)
- **MDX** for the journal/blog (no `gray-matter`, minimal frontmatter reader)
- **Resend** for the contact form (no DB)
- **Umami** for analytics (self-hosted, optional via env)
- **Lucide** icons
- Editorial typography: **Fraunces** (display) · **Instrument Sans** (body) · **JetBrains Mono** (data)

## Design direction

Refined minimal · audit-grade · paper/parchment palette
(warm cream, deep olive, audit-stamp rust). Hairline rules,
tabular numerals, hash-chain mentality. No marketing fluff,
real numbers, no claims that can't survive a certifier conversation.

## Getting started

```bash
pnpm install   # or npm install / yarn / bun
cp .env.example .env.local
pnpm dev
```

Open http://localhost:3000.

### Environment variables

See `.env.example`. The contact form falls back to `console.info` when
`RESEND_API_KEY` is unset, so you can run the site end-to-end without
provisioning email in dev.

| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_SITE_URL` | Canonical site URL used in metadata, sitemap, OG |
| `RESEND_API_KEY` | API key for contact email delivery |
| `CONTACT_FROM` | `From:` header (must be a verified Resend domain) |
| `CONTACT_TO` | Inbox that receives leads |
| `NEXT_PUBLIC_UMAMI_SRC` | Umami script URL (optional) |
| `NEXT_PUBLIC_UMAMI_ID` | Umami site ID (optional) |

## Project structure

```
src/
├── app/
│   ├── api/contact/route.ts   # POST /api/contact → Resend
│   ├── blog/                  # MDX-backed journal
│   ├── globals.css            # design tokens, base typography, paper grain
│   ├── layout.tsx             # fonts, metadata, analytics
│   ├── opengraph-image.tsx    # dynamic OG card (edge runtime)
│   ├── page.tsx               # landing
│   ├── robots.ts
│   └── sitemap.ts
├── components/                # Hero, Problem, Solution, …, Footer
│   └── ui/                    # button, input, textarea, label, accordion
├── lib/
│   ├── blog.ts                # filesystem MDX reader
│   └── utils.ts               # cn()
mdx-components.tsx             # editorial MDX overrides
content/blog/*.mdx             # blog posts
```

## Adding a blog post

Create `content/blog/your-slug.mdx`:

```mdx
---
title: "Your title here"
date: "2026-05-07"
excerpt: "One-sentence summary."
---

Markdown / MDX content…
```

Posts are sorted by `date` desc and exposed at `/blog/your-slug`.

## Deployment

Two recommended targets:

### Vercel

The default. `next build` produces a static-first site; only `/api/contact`
and `/opengraph-image` run on the edge.

```bash
vercel
```

### Hetzner / self-hosted (with the rest of the stack)

```bash
pnpm build
pnpm start
```

Run behind nginx + Let's Encrypt on the same Hetzner host that runs the rest
of the DFT services. **Never** point this build to the production app DB —
the landing has no reason to touch it.

## Performance budget

Targets enforced by the brief:

- Lighthouse > 95 across all four categories
- LCP < 1.5s
- No third-party trackers (Umami only, optional, deferred)
- All fonts via `next/font` with `display: swap`
- All icons tree-shaken via `lucide-react` + `optimizePackageImports`

Run a Lighthouse pass after changes:

```bash
pnpm build && pnpm start
# in another terminal
npx lighthouse http://localhost:3000 --view --preset=desktop
```

## Internationalisation

The brief asks for English-primary, Italian-secondary. The current build is
English-only (Sprint 1 deliverable). When adding IT, prefer `next-intl` or
the App Router `[locale]` segment over runtime translation libs — keeps the
SEO and the bundle clean.

## License

© DFT Project. All rights reserved.
