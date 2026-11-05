// Drive a LOCAL copy of heatstitch (MIT, github.com/pfedan/heatstitch) over the bench jobs.
//
//   node tools/bench_run_heatstitch.mjs --bench-dir DIR [--engine heatstitch] [--style flat|dynamic|smart]
//        [--only slug ...] [--port 8777]
//
// DIR/_tools/heatstitch/mirror is a static copy of the public build, served by
// `python -I -m http.server 8777 --bind 127.0.0.1 -d <mirror>`; every request that is not to
// 127.0.0.1 is aborted, so no artwork leaves the machine. For each job in DIR/jobs.json the
// ink-cropped art in DIR/_art is converted at the PRO's width (the "Width (mm)" control is the
// only size control: it is set per job and the size the tool reports is recorded) with the tool's
// DEFAULTS (6 colours, smooth 3, smallest area 3 mm2, background left out, Brother thread colours,
// Stable woven, 40 wt) and saved as DST to DIR/<engine>/<slug>.dst; manifest.json beside them
// carries the reported stitches / size / trims. `playwright-core` is resolved from
// DIR/_tools/pw/node_modules and the browser from the local Playwright cache.
import { createRequire } from 'node:module';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf(k); return i < 0 ? d : argv[i + 1]; };
const bench = opt('--bench-dir');
const engine = opt('--engine', 'heatstitch');
const style = opt('--style', 'flat');
const port = opt('--port', '8777');
const oi = argv.indexOf('--only');
const only = oi < 0 ? null : argv.slice(oi + 1).filter(a => !a.startsWith('--'));
if (!bench) { console.error('--bench-dir required'); process.exit(2); }

const req = createRequire(path.join(bench, '_tools', 'pw', 'package.json'));
const { chromium } = req('playwright-core');
const cache = path.join(os.homedir(), 'AppData', 'Local', 'ms-playwright');
const dirs = fs.readdirSync(cache).filter(d => /^chromium-\d+$/.test(d)).sort();
const exe = path.join(cache, dirs[dirs.length - 1], 'chrome-win64', 'chrome.exe');

const jobs = JSON.parse(fs.readFileSync(path.join(bench, 'jobs.json'), 'utf8'));
const out = path.join(bench, engine);
fs.mkdirSync(out, { recursive: true });
const mpath = path.join(out, 'manifest.json');
const manifest = fs.existsSync(mpath) ? JSON.parse(fs.readFileSync(mpath, 'utf8')) : {};

const browser = await chromium.launch({ executablePath: exe, headless: true });
for (const [slug, j] of Object.entries(jobs)) {
  if (only && !only.includes(slug)) continue;
  const ctx = await browser.newContext({ acceptDownloads: true, viewport: { width: 1400, height: 900 } });
  const page = await ctx.newPage();
  page.setDefaultTimeout(300000);
  await page.route('**/*', r => (new URL(r.request().url()).hostname === '127.0.0.1' ? r.continue() : r.abort()));
  const t0 = Date.now();
  try {
    await page.goto(`http://127.0.0.1:${port}/`);
    await page.getByRole('button', { name: /Convert a picture/ }).click();
    await page.locator('#image-input').setInputFiles(path.join(bench, '_art', `${slug}.png`));
    await page.waitForTimeout(1500);
    await page.locator('#image-width').fill(String(j.width_mm));
    await page.locator('#image-width').press('Tab');
    await page.waitForTimeout(500);
    const asked = (await page.locator('#image-height').innerText()).trim();
    await page.locator('#image-next').click();
    await page.waitForTimeout(3000);
    await page.locator('#image-next').click();
    if (style !== 'flat') await page.getByText(new RegExp(`^${style}$`, 'i')).first().click();
    await page.getByRole('button', { name: 'Take over' }).waitFor({ timeout: 300000 });
    await page.waitForTimeout(1500);
    const panel = await page.locator('body').innerText();
    const grab = k => (panel.match(new RegExp(`${k}\\s*\\n?\\s*([^\\n]+)`)) || [])[1];
    await page.getByRole('button', { name: 'Take over' }).click();
    await page.waitForTimeout(2500);
    await page.getByRole('button', { name: 'Save', exact: true }).first().click();
    await page.waitForTimeout(800);
    await page.locator('input[type=radio][value=dst]').check({ force: true });
    const [dl] = await Promise.all([
      page.waitForEvent('download', { timeout: 120000 }),
      page.getByRole('button', { name: 'Save', exact: true }).last().click(),
    ]);
    await dl.saveAs(path.join(out, `${slug}.dst`));
    manifest[slug] = { asked_width_mm: j.width_mm, size_readout_before: asked, style,
                       stitches_reported: (panel.match(/Stitches\s+(\d[\d,]*)/) || [])[1], size_reported: grab('Size'), trims_reported: grab('Trims'),
                       secs: Math.round((Date.now() - t0) / 100) / 10 };
    console.log(slug, 'ok', JSON.stringify(manifest[slug]));
  } catch (e) {
    manifest[slug] = { error: String(e).slice(0, 300), secs: Math.round((Date.now() - t0) / 100) / 10 };
    console.log(slug, 'FAIL', manifest[slug].error);
    try { await page.screenshot({ path: path.join(out, `${slug}_fail.png`) }); } catch { /* best effort */ }
  }
  fs.writeFileSync(mpath, JSON.stringify(manifest, null, 1));
  await ctx.close();
}
await browser.close();
