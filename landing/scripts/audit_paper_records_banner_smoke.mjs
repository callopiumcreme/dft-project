// audit_paper_records_banner_smoke.mjs
// Regression smoke for round-3 audit findings N6 + N7:
//
//   N6 — SyntheticRenderBanner must render inside the eRSV modal for entries
//        dated inside the paper-records window (2025-01-01 → 2025-08-31).
//
//   N7 — Personal-data fields (driver, cédula, placa, hora de salida, báscula
//        operator) inside the iframe must render the literal marker
//        ``[Paper record — Girardot archive]`` rather than any synthetic
//        plausible Colombian name. The marker is the verifier-facing signal
//        that the cell is bound to the paper archive; emitting a synthetic
//        name (e.g. ``Carlos Ramírez Gómez``) would re-introduce the
//        symbolic-data trap that N7 closes.
//
// Verifies (in order):
//   1. /app/inputs/20997 (2025-01-02) and /app/inputs/21211 (2025-02-01)
//      open ErsvModal on first ErsvLink click.
//   2. SyntheticRenderBanner is present (N6).
//   3. iframe srcDoc body contains the marker text at least 4× (the four
//      personal-data <td> cells in the Transporte block) (N7).
//   4. iframe body does NOT contain any of the known synthetic-name
//      fragments from the legacy generator pool (N7).
//
// Exit code:
//   0 — every assertion green on both rows.
//   1 — any assertion fails on any row.
//
// Output:
//   /tmp/audit_pr_banner_<id>_dom.txt    — outer modal HTML capture
//   /tmp/audit_pr_banner_<id>_iframe.txt — iframe body innerText capture
//   /tmp/audit_pr_banner_<id>.png        — fullpage screenshot
//   /tmp/audit_pr_banner_report.json     — structured report

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

  // ---- N7 — assert the marker reached the iframe body ---------------------
  // The eRSV iframe uses srcDoc, so the iframe lives at the modal's
  // <iframe> element; Playwright exposes its document via contentFrame().
  let iframeBody = '';
  let markerCount = 0;
  let forbiddenHits = [];
  const PAPER_RECORD_MARKER = '[Paper record — Girardot archive]';
  // Sample of plausible Colombian names + plate prefixes from the legacy
  // ersv_pool generator. If any of these survives into an in-window
  // iframe body, Step 2 has regressed.
  const FORBIDDEN = [
    'Carlos Ramírez',
    'José Luis Hernández',
    'Andrés Felipe Torres',
    'Juan Pablo Restrepo',
    'Diego Alejandro Vargas',
    'Luis Fernando Marín',
    'Hernán Darío Quintero',
    'Sergio Mauricio Patiño',
    'Óscar Iván Castaño',
    'Edwin Mauricio López',
    'Mario Andrés Sepúlveda',
    'Wilson Alberto Cárdenas',
  ];
  try {
    const iframeEl = await page.waitForSelector('[role="dialog"] iframe', { timeout: 5000 });
    const frame = await iframeEl.contentFrame();
    if (frame) {
      // srcDoc renders synchronously but the body innerHTML is observable
      // via DOM query — no extra wait needed.
      iframeBody = await frame.evaluate(() => document.body ? document.body.innerHTML : '');
      // Count marker occurrences (string contains, not regex — marker has
      // em-dash U+2014 + brackets that need no escaping).
      let idx = 0;
      while ((idx = iframeBody.indexOf(PAPER_RECORD_MARKER, idx)) !== -1) {
        markerCount += 1;
        idx += PAPER_RECORD_MARKER.length;
      }
      forbiddenHits = FORBIDDEN.filter((n) => iframeBody.includes(n));
    }
  } catch (e) {
    waitErr = waitErr || (e instanceof Error ? e.message : String(e));
  }

  writeFileSync(`/tmp/audit_pr_banner_${id}_dom.txt`, modalHtml);
  writeFileSync(`/tmp/audit_pr_banner_${id}_iframe.txt`, iframeBody);
  await page.screenshot({ path: `/tmp/audit_pr_banner_${id}.png`, fullPage: true });
  await page.close();

  return { id, date, label, bannerCount, markerCount, forbiddenHits, consoleErrors, waitErr };
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
    console.log(
      `[smoke] ${r.label} (id=${r.id} date=${r.date}) ` +
        `banner_count=${r.bannerCount} marker_count=${r.markerCount} ` +
        `forbidden=${r.forbiddenHits.length}`,
    );
    if (r.waitErr) console.log('  WAIT ' + r.waitErr.slice(0, 200));
    if (r.forbiddenHits.length) {
      console.log('  LEAK ' + r.forbiddenHits.join(', '));
    }
    if (r.consoleErrors.length) {
      r.consoleErrors.slice(0, 5).forEach((e) => console.log('  ERR ' + e.slice(0, 200)));
    }
    results.push(r);
  }

  writeFileSync('/tmp/audit_pr_banner_report.json', JSON.stringify({ results }, null, 2));
  await browser.close();

  // Pass criteria — every row must satisfy ALL of:
  //   banner_count ≥ 1                — N6 (banner mounted)
  //   marker_count ≥ 4                — N7 (≥4 personal-data cells carry marker)
  //   forbiddenHits.length === 0      — N7 (no synthetic-name leak)
  const fail = results.some(
    (r) => r.bannerCount < 1 || r.markerCount < 4 || r.forbiddenHits.length > 0,
  );
  if (fail) {
    console.error(
      '[smoke] FAIL — N6/N7 regression: banner missing, marker absent, or synthetic name leaked',
    );
    process.exit(1);
  }
  console.log('[smoke] PASS — N6 banner + N7 marker assertions green on all in-window rows');
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
