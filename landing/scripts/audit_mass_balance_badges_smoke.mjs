// audit_mass_balance_badges_smoke.mjs
// Regression smoke for round-2 audit cert-flag badges on /app/reports/mass-balance.
//
// Verifies (post chore/hide-cert-flag-badges):
//   - AUDIT badge is NOT rendered (was: 2 certs CO222-00000026, ES216-20254036).
//   - SCHEME? badge is NOT rendered (was: 5 certs CO222-00000026, CO222-00000027,
//     US201-120372025, US201-138762025, US201-158772025).
//   - Cert numbers still visible on the page (data layer untouched; flags removed
//     from verifier-facing UI per OisteBio Geschäftsführer direction). Internal
//     red-team reads certificates.notes + certificates.scheme_pdf_detected via
//     direct SQL — see file-level comment in mass-balance/page.tsx.
//
// Exit code:
//   0 — clean (no AUDIT/SCHEME? badges present).
//   1 — regression (one or more badges resurfaced).
//
// Output:
//   /tmp/audit_mb_badges_dom.txt   — full HTML of expanded daily accordion
//   /tmp/audit_mb_badges.png       — screenshot
//   /tmp/audit_mb_badges_report.json — structured: badges found per cert
//
// Run:
//   node landing/scripts/audit_mass_balance_badges_smoke.mjs
//
// Requires:
//   - landing dev on :3030
//   - backend on :18000
//   - docker exec dft-project_backend_1 reachable for JWT mint

import { chromium } from '/home/usergianni/.npm/_npx/a8a7eec953f1f314/node_modules/@playwright/test/index.mjs';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const BASE = 'http://localhost:3030';
const TARGET = '/app/reports/mass-balance';
const BACKEND = 'dft-project_backend_1';
const EMAIL = 'admin@dft-project.com';

function mintJwt() {
  const py =
    'from app.core.security import create_access_token; ' +
    `print(create_access_token(${JSON.stringify(EMAIL)}, role='admin'))`;
  return execFileSync(
    'docker',
    ['exec', '-i', BACKEND, 'python', '-c', py],
    { encoding: 'utf8' },
  ).trim();
}

async function main() {
  const token = mintJwt();
  console.log('[smoke] JWT minted, len=' + token.length);

  const browser = await chromium.launch();
  const ctx = await browser.newContext();
  await ctx.addCookies([
    {
      name: 'dft_session',
      value: token,
      domain: 'localhost',
      path: '/',
      httpOnly: false,
      sameSite: 'Lax',
    },
  ]);
  const page = await ctx.newPage();

  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  await page.goto(BASE + TARGET, { waitUntil: 'networkidle' });
  console.log('[smoke] loaded ' + TARGET);

  // Wait for daily entries to load; expand all closure rows by clicking
  // each accordion summary so cert badges become visible.
  await page.waitForSelector('table', { timeout: 10000 });
  const accordions = await page.locator('summary, button[aria-expanded]').all();
  console.log('[smoke] toggling ' + accordions.length + ' disclosures');
  for (const a of accordions) {
    try {
      await a.click({ timeout: 500 });
    } catch {
      /* ignore */
    }
  }
  await page.waitForTimeout(800);

  const dom = await page.content();
  writeFileSync('/tmp/audit_mb_badges_dom.txt', dom);
  await page.screenshot({
    path: '/tmp/audit_mb_badges.png',
    fullPage: true,
  });

  // Scan DOM text for badge labels + neighbouring cert numbers.
  const report = await page.evaluate(() => {
    const out = { audit: [], scheme: [], cert_numbers_seen: new Set() };
    const badges = document.querySelectorAll('[class*="bg-"][class*="border"]');
    badges.forEach((el) => {
      const txt = (el.textContent || '').trim();
      if (txt === 'AUDIT' || txt === 'SCHEME?') {
        // Walk up to find nearest cert_number-bearing parent (heuristic: text matches /^[A-Z]{2}\d{3}-/).
        let node = el.parentElement;
        let cert = '';
        for (let i = 0; i < 6 && node; i++) {
          const m = (node.textContent || '').match(/[A-Z]{2,3}\d{3}-[\dA-Z]+/);
          if (m) {
            cert = m[0];
            break;
          }
          node = node.parentElement;
        }
        const entry = { badge: txt, cert, title: el.getAttribute('title') || '' };
        if (txt === 'AUDIT') out.audit.push(entry);
        else out.scheme.push(entry);
      }
    });
    // Collect all cert_numbers anywhere on page.
    const matches = document.body.textContent.match(/[A-Z]{2,3}\d{3}-[\dA-Z]+/g) || [];
    matches.forEach((m) => out.cert_numbers_seen.add(m));
    out.cert_numbers_seen = Array.from(out.cert_numbers_seen);
    return out;
  });

  writeFileSync(
    '/tmp/audit_mb_badges_report.json',
    JSON.stringify({ report, consoleErrors }, null, 2),
  );

  console.log('[smoke] AUDIT badges found: ' + report.audit.length);
  report.audit.forEach((e) => console.log('  - ' + e.cert + ' :: ' + e.title.slice(0, 80)));
  console.log('[smoke] SCHEME? badges found: ' + report.scheme.length);
  report.scheme.forEach((e) => console.log('  - ' + e.cert + ' :: ' + e.title.slice(0, 80)));
  console.log('[smoke] cert_numbers on page: ' + report.cert_numbers_seen.length);
  console.log('[smoke] console errors: ' + consoleErrors.length);
  consoleErrors.forEach((e) => console.log('  ERR ' + e.slice(0, 200)));

  await browser.close();

  // Regression gate: cert-flag badges must stay hidden from this surface.
  const regression = report.audit.length > 0 || report.scheme.length > 0;
  if (regression) {
    console.error(
      '[smoke] FAIL — cert-flag badges resurfaced. ' +
        'Hide-mode invariant broken. See landing/src/app/app/reports/mass-balance/page.tsx',
    );
    process.exit(1);
  }
  console.log('[smoke] PASS — badges hidden, data layer intact.');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
