// Render single check frames at given times: node check.mjs 3.5 14 40 ...
import { chromium } from 'playwright-core';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const dir = path.dirname(fileURLToPath(import.meta.url));
const times = process.argv.slice(2).map(Number);
const browser = await chromium.launch({
  executablePath: '/home/hatch/.cache/ms-playwright/chromium_headless_shell-1254/chrome-headless-shell-linux64/chrome-headless-shell',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--hide-scrollbars', '--force-color-profile=srgb'],
});
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await page.goto('file://' + path.join(dir, 'deck.html'));
await page.waitForFunction(() => typeof window.__render === 'function');
page.on('pageerror', e => console.log('PAGEERROR', e.message));
for (const t of times) {
  await page.evaluate((tt) => window.__render(tt), t);
  const name = 'chk-' + String(t).replace('.', '_') + '.png';
  await page.screenshot({ path: path.join(dir, 'checks', name) });
  console.log('wrote', name);
}
await browser.close();
