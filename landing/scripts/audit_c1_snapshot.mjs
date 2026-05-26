// audit_c1_snapshot.mjs
// Read-only render snapshot of /app/logistics/1 for DfT audit baseline.
// Output: /tmp/audit_c1_dom.txt + /tmp/audit_c1_screenshot.png +
//         /tmp/audit_c1_report.json (sections, headings, chips, table rows,
//         drill-down links, console errors).
//
// Run:
//   node landing/scripts/audit_c1_snapshot.mjs
//
// Requires:
//   - landing dev on :3030
//   - backend on :18000
//   - docker exec dft-project_backend_1 reachable for JWT mint

import { chromium } from '/home/usergianni/.npm/_npx/a8a7eec953f1f314/node_modules/@playwright/test/index.mjs';
import { execFileSync } from 'node:child_process';
import { writeFileSync } from 'node:fs';

const BASE = 'http://localhost:3030';
const TARGET = '/app/logistics/1';
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

(async () => {
  const jwt = mintJwt();
  console.log(`[mint] jwt len=${jwt.length}`);

  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 900 },
  });
  await ctx.addCookies([
    {
      name: 'dft_session',
      value: jwt,
      domain: 'localhost',
      path: '/',
      httpOnly: false,
      secure: false,
    },
  ]);

  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];

  const page = await ctx.newPage();
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (e) => pageErrors.push(String(e)));
  page.on('response', (resp) => {
    const url = resp.url();
    const status = resp.status();
    if (url.includes('/api/') && status >= 400) {
      failedRequests.push({ url, status });
    }
  });

  const url = `${BASE}${TARGET}`;
  console.log(`[nav] ${url}`);
  const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  console.log(`[nav] status=${resp?.status()}`);

  // Wait for chain summary to render (or fail)
  await page.waitForTimeout(1500);

  // ---- DOM scrape ----
  const h1 = await page.locator('h1').first().innerText().catch(() => '');
  const h2s = await page.locator('h2').allInnerTexts();
  const h3s = await page.locator('h3').allInnerTexts();

  const allTableHeaders = await page.locator('table thead th').allInnerTexts();
  const allTableRowCounts = await page.evaluate(() =>
    Array.from(document.querySelectorAll('table')).map((t) => ({
      headers: Array.from(t.querySelectorAll('thead th')).map(
        (th) => th.innerText.trim(),
      ),
      rowCount: t.querySelectorAll('tbody tr').length,
    })),
  );

  // Chips / pills
  const chips = await page
    .locator('[class*="border-rule"][class*="px-2"]')
    .allInnerTexts();

  // Drill-down links
  const links = await page.evaluate(() =>
    Array.from(document.querySelectorAll('a[href^="/app/"]')).map((a) => ({
      text: a.innerText.trim(),
      href: a.getAttribute('href'),
    })),
  );

  // Buttons (chip openers for PDF / modals)
  const buttons = await page.evaluate(() =>
    Array.from(document.querySelectorAll('button')).map((b) => ({
      text: b.innerText.trim().slice(0, 80),
      aria: b.getAttribute('aria-label') ?? null,
    })),
  );

  // Full visible text (for grep against DfT requirements)
  const bodyText = await page.locator('body').innerText();

  // ---- Screenshot full page ----
  await page.screenshot({
    path: '/tmp/audit_c1_screenshot.png',
    fullPage: true,
  });

  await browser.close();

  // ---- Report ----
  const report = {
    target_url: url,
    nav_status: resp?.status() ?? null,
    h1,
    h2: h2s,
    h3: h3s,
    tables: allTableRowCounts,
    distinct_table_headers: Array.from(new Set(allTableHeaders)),
    chips,
    drilldown_links: links,
    buttons,
    console_errors: consoleErrors,
    page_errors: pageErrors,
    failed_api_requests: failedRequests,
    body_text_length: bodyText.length,
  };

  writeFileSync('/tmp/audit_c1_report.json', JSON.stringify(report, null, 2));
  writeFileSync('/tmp/audit_c1_dom.txt', bodyText);

  console.log('[done] report=/tmp/audit_c1_report.json');
  console.log('[done] dom=/tmp/audit_c1_dom.txt');
  console.log('[done] screenshot=/tmp/audit_c1_screenshot.png');
  console.log(
    `[summary] h2=${h2s.length} tables=${allTableRowCounts.length} chips=${chips.length} links=${links.length} buttons=${buttons.length}`,
  );
  console.log(
    `[errors] console=${consoleErrors.length} pageerror=${pageErrors.length} failedApi=${failedRequests.length}`,
  );
})().catch((e) => {
  console.error('[fatal]', e);
  process.exit(1);
});
