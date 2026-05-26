// audit_paper_records_banner_smoke.mjs
// Regression smoke for round-3 audit finding N6:
// SyntheticRenderBanner must render inside the eRSV modal for entries dated
// inside the paper-records window. After Step 1 the window starts on
// 2025-01-01, so a January row triggers the banner; February is the legacy
// positive case kept as a regression guard.
//
// Verifies:
//   - /app/inputs/20997 (2025-01-02) — ErsvLink click opens modal, banner present.
//   - /app/inputs/21211 (2025-02-01) — same assertion, banner still works for Feb.
//
// Exit code:
//   0 — both rows show the banner.
//   1 — either row missing the banner.
//
// Output:
//   /tmp/audit_pr_banner_<id>_dom.txt   — modal HTML capture
//   /tmp/audit_pr_banner_<id>.png       — fullpage screenshot
//   /tmp/audit_pr_banner_report.json    — structured report

import { chromium } from '/home/usergianni/.npm/_npx/a8a7eec953f1f314/node_modules/@playwright/test/index.mjs';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const BASE = 'http://localhost:3030';
const BACKEND = 'dft-project_backend_1';
const EMAIL = 'admin@dft-project.com';

const TARGETS = [
  { id: 20997, date: '2025-01-02', label: 'JAN-2025' },
  { id: 21211, date: '2025-02-01', label: 'FEB-2025' },
];

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

async function probeOne(ctx, { id, date, label }) {
  const page = await ctx.newPage();
  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });

  await page.goto(`${BASE}/app/inputs/${id}`, { waitUntil: 'networkidle' });

  // Click first ErsvLink trigger on the page. ErsvLink renders a <button>
  // with aria-label="Open eRSV <number>"; the displayed text is the eRSV
  // number itself (not the literal "eRSV"), so we select by aria-label.
  const trigger = page.locator('button[aria-label^="Open eRSV"]').first();
  await trigger.click({ timeout: 5000 });

  // ErsvModal opens immediately on click but renders the banner only after
  // its async fetchErsvMetadata + fetchErsvHtml Promise.all resolves
  // (state.kind === 'ready' — see landing/src/components/ersv/ersv-modal.tsx
  // lines 110-112). The initial DOM shows "Loading eRSV…" with no banner
  // and no DialogDescription; both appear together once the fetch resolves.
  // So we wait directly on the banner OR on the error state (in case the
  // backend returned 404, which would never render the banner).
  let bannerCount = 0;
  let modalHtml = '';
  let waitErr = null;
  try {
    // First confirm the modal portal mounted at all.
    await page.waitForSelector('[role="dialog"]', { timeout: 5000 });
    // Then wait for the ready-state branch — either the banner itself
    // (positive path) or an error message (negative path so we don't hang).
    await page.waitForFunction(
      () => {
        const banner = document.querySelector(
          '[role="note"][aria-label="Synthetic-rendering disclosure"]',
        );
        const dialog = document.querySelector('[role="dialog"]');
        if (!dialog) return false;
        // Error branch text is rendered with class text-accent inside the modal.
        const errorEl = dialog.querySelector('p.text-accent');
        return Boolean(banner) || Boolean(errorEl);
      },
      { timeout: 15000 },
    );
    bannerCount = await page.locator('[role="note"][aria-label="Synthetic-rendering disclosure"]').count();
    modalHtml = await page.content();
  } catch (e) {
    waitErr = e instanceof Error ? e.message : String(e);
    modalHtml = await page.content();
  }

  writeFileSync(`/tmp/audit_pr_banner_${id}_dom.txt`, modalHtml);
  await page.screenshot({ path: `/tmp/audit_pr_banner_${id}.png`, fullPage: true });
  await page.close();

  return { id, date, label, bannerCount, consoleErrors, waitErr };
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

  const results = [];
  for (const t of TARGETS) {
    const r = await probeOne(ctx, t);
    console.log(`[smoke] ${r.label} (id=${r.id} date=${r.date}) banner_count=${r.bannerCount}`);
    if (r.waitErr) console.log('  WAIT ' + r.waitErr.slice(0, 200));
    if (r.consoleErrors.length) {
      r.consoleErrors.slice(0, 5).forEach((e) => console.log('  ERR ' + e.slice(0, 200)));
    }
    results.push(r);
  }

  writeFileSync('/tmp/audit_pr_banner_report.json', JSON.stringify({ results }, null, 2));
  await browser.close();

  const fail = results.some((r) => r.bannerCount < 1);
  if (fail) {
    console.error('[smoke] FAIL — banner missing on at least one in-window row');
    process.exit(1);
  }
  console.log('[smoke] PASS — banner renders for all in-window rows');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
