// Deterministic frame-stepped renderer (adapted from the NEAR demo-v4 recipe).
// Usage: node render.mjs <framesDir> <startFrame> <endFrameExclusive>
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.dirname(fileURLToPath(import.meta.url));
const framesDir = process.argv[2];
const start = parseInt(process.argv[3] || '0', 10);
const end = parseInt(process.argv[4] || '4367', 10);
mkdirSync(framesDir, { recursive: true });

const browser = await chromium.launch({
  executablePath: '/home/hatch/.cache/ms-playwright/chromium_headless_shell-1254/chrome-headless-shell-linux64/chrome-headless-shell',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--hide-scrollbars', '--force-color-profile=srgb'],
});
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
await page.goto('file://' + path.join(dir, 'deck.html'));
await page.waitForFunction(() => typeof window.__render === 'function');

const t0 = Date.now();
for (let i = start; i < end; i++) {
  const t = i / 30;
  await page.evaluate((tt) => window.__render(tt), t);
  await page.screenshot({ path: path.join(framesDir, 'f' + String(i).padStart(5, '0') + '.jpg'), type: 'jpeg', quality: 84 });
  if ((i - start) % 300 === 299) {
    const el = ((Date.now() - t0) / 1000).toFixed(1);
    console.log(`frame ${i + 1}/${end} elapsed ${el}s`);
  }
}
console.log(`DONE ${end - start} frames in ${((Date.now() - t0) / 1000).toFixed(1)}s`);
await browser.close();
