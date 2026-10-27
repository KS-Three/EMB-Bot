// SVG and EXIF-rotated JPEG uploads reach /digitize at decode resolution, not
// the 1,200-px preview (W5-08, built OFF).
//
// Three upload kinds cannot go to the service as the file the customer chose:
// an SVG and a GIF (cv2 does not decode them) and a phone JPEG the browser
// rotated on decode (cv2 ignores EXIF orientation). They digitized from the
// panel's 1,200-px canvas -- 4.8 px/mm across a 250 mm jacket back, under the
// 8 px/mm work grid. With the switch ON (localStorage "embbot-upload-full-res"
// = "1", rasterize.js) the panel draws them upright at up to the service's
// own 2,800-px decode size instead, stores THAT, and sends it.
//
// The request is read where the panel makes it -- Chromium exposes no post data
// for a multipart body with a Blob part -- by a fetch hook that records the
// `image` part of every /digitize POST. The hook then REFUSES the call: what is
// under test is what the panel sends, so the service does no digitize work for
// it (the stitch-level comparison is tools/upload-fullres-score.mjs).
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, uploadArtwork } from "./helpers.js";
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const FIX = (name) => path.join(__dirname, "fixtures", name);
const SVG = FIX("small_text_logo.svg");        // viewBox 600 x 300
const ROTATED = FIX("rotated_exif6.jpg");      // upright 2,520 x 1,400, stored 1,400 x 2,520
const TWIN = FIX("rotated_exif1_twin.jpg");    // the same art stored upright, no rotation tag
const KEY = "embbot-upload-full-res";

// ---- service bootstrap, same as the other digitize specs here ------------
async function healthy() {
  try {
    const r = await fetch(SERVICE_URL + "/health");
    if (!r.ok) return false;
    const h = await r.json();
    return !!h && h.status === "ok";
  } catch (e) {
    return false;
  }
}

function venvPythonCandidates() {
  const roots = [path.resolve(__dirname, "../..")];
  try {
    const stat = readFileSync(path.join(roots[0], ".git"), "utf8");
    const m = stat.match(/^gitdir:\s*(.+)$/m);
    if (m) {
      const mainRoot = path.resolve(m[1].trim(), "../../..");
      if (mainRoot !== roots[0]) roots.push(mainRoot);
    }
  } catch (e) {
    // .git is a directory: a normal checkout, nothing to add
  }
  const out = [];
  for (const root of roots) {
    out.push(path.join(root, "digitizer", ".venv", "bin", "python"));
    out.push(path.join(root, "digitizer", ".venv", "Scripts", "python.exe"));
  }
  return out.filter(existsSync);
}

let serviceProc = null;
let serviceUp = false;
let skipReason = "";

test.beforeAll(async () => {
  if (await healthy()) {
    serviceUp = true;
    return;
  }
  const [python] = venvPythonCandidates();
  if (!python) {
    skipReason = "digitizer service is not running and no venv python was found.";
    return;
  }
  serviceProc = spawn(python, ["-m", "digitizer_service"], {
    cwd: path.resolve(__dirname, "../../digitizer"),
    stdio: "ignore",
  });
  const deadline = Date.now() + 30_000;
  while (Date.now() < deadline) {
    if (await healthy()) {
      serviceUp = true;
      return;
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  skipReason = "digitizer service failed to answer /health within 30s of being started (" + python + ").";
});

test.afterAll(() => {
  if (serviceProc) serviceProc.kill("SIGTERM");
});

// ---- helpers -----------------------------------------------------------------

// What the source store holds: type, size and the PNG header's width/height.
function storedRecords(page) {
  return page.evaluate(
    () =>
      new Promise((resolve) => {
        const open = indexedDB.open("embstudio-sources", 1);
        open.onupgradeneeded = () => {
          if (!open.result.objectStoreNames.contains("sources")) open.result.createObjectStore("sources");
        };
        open.onerror = () => resolve([]);
        open.onsuccess = () => {
          const db = open.result;
          const all = db.transaction("sources", "readonly").objectStore("sources").getAll();
          all.onsuccess = () => {
            db.close();
            resolve(all.result.map((r) => {
              const b = new Uint8Array(r.bytes.buffer || r.bytes);
              const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
              const png = b[0] === 0x89 && b[1] === 0x50;
              return { type: r.type, name: r.name, size: b.length, png, width: png ? dv.getUint32(16) : 0, height: png ? dv.getUint32(20) : 0 };
            }));
          };
          all.onerror = () => { db.close(); resolve([]); };
        };
      })
  );
}

// Record the `image` part of every /digitize POST, then refuse the call.
async function recordAndRefuseSends(page) {
  await page.evaluate(() => {
    const orig = window.fetch;
    window.__sends = [];
    window.fetch = async function (url, init) {
      if (typeof url === "string" && /\/digitize$/.test(url) && init && init.body instanceof FormData) {
        const img = init.body.get("image");
        const buf = new Uint8Array(await img.arrayBuffer());
        const dv = new DataView(buf.buffer);
        let bin = "";
        for (let i = 0; i < buf.length; i += 0x8000) bin += String.fromCharCode(...buf.subarray(i, i + 0x8000));
        window.__sends.push({
          name: img.name, type: img.type, size: img.size,
          png: buf[0] === 0x89 && buf[1] === 0x50,
          width: dv.getUint32(16), height: dv.getUint32(20),
          b64: btoa(bin),
        });
        throw new TypeError("refused by upload-full-res.spec: the POST is what is under test");
      }
      return orig.call(this, url, init);
    };
  });
}

// Upload `file` on a fresh page, press Auto Digitize Image, and return the
// image the panel tried to send.
async function sendOf(context, file, { on }) {
  const page = await context.newPage();
  if (on) await page.addInitScript((k) => localStorage.setItem(k, "1"), KEY);
  await startStudio(page);
  await pickGarment(page, "Tote");
  await uploadArtwork(page, file, { run: false });
  await expect(page.locator("img.dgp-thumb")).toBeVisible({ timeout: 60_000 });
  await recordAndRefuseSends(page);
  const run = page.locator(".dgp-run");
  await expect(run).toBeEnabled({ timeout: 30_000 });
  await run.click();
  await expect.poll(() => page.evaluate(() => window.__sends.length), { timeout: 60_000 }).toBe(1);
  const sent = await page.evaluate(() => window.__sends[0]);
  const stored = await storedRecords(page);
  const previewPx = await page.locator("img.dgp-thumb").evaluate((im) => [im.naturalWidth, im.naturalHeight]);
  return { page, sent, stored, previewPx };
}

// ---- the tests ---------------------------------------------------------------

test.describe("switch OFF (today): the three canvas-path kinds send the 1,200-px preview", () => {
  test.beforeEach(() => test.skip(!serviceUp, skipReason));

  test("an SVG is sent as the 1,200-px canvas PNG and nothing is stored", async ({ context }) => {
    test.setTimeout(180_000);
    const { page, sent, stored } = await sendOf(context, SVG, { on: false });
    expect(sent).toMatchObject({ name: "art.png", type: "image/png", png: true, width: 1200, height: 600 });
    expect(stored).toEqual([]);
    await page.close();
  });

  test("a rotated JPEG is sent as the 1,200-px canvas PNG, upright", async ({ context }) => {
    test.setTimeout(180_000);
    const { page, sent, stored } = await sendOf(context, ROTATED, { on: false });
    expect(sent).toMatchObject({ name: "art.png", png: true, width: 1200, height: 667 });
    expect(stored).toEqual([]);
    await page.close();
  });
});

test.describe("switch ON: they send an upright render at up to the service's 2,800-px decode", () => {
  test.beforeEach(() => test.skip(!serviceUp, skipReason));

  test("an SVG is stored and sent as a 2,800 x 1,400 PNG; the preview stays 1,200 px", async ({ context }) => {
    test.setTimeout(180_000);
    const { page, sent, stored, previewPx } = await sendOf(context, SVG, { on: true });
    expect(sent).toMatchObject({ type: "image/png", png: true, width: 2800, height: 1400 });
    expect(stored).toHaveLength(1);
    expect(stored[0]).toMatchObject({ type: "image/png", name: "small_text_logo.png", png: true, width: 2800, height: 1400 });
    expect(stored[0].size).toBe(sent.size);
    // The localStorage preview is unchanged: still the 1,200-px canvas.
    expect(previewPx).toEqual([1200, 600]);
    await page.close();
  });

  test("a rotated JPEG goes up upright at its decoded size, and equals its upright twin through the same path", async ({ context }) => {
    test.setTimeout(240_000);
    const a = await sendOf(context, ROTATED, { on: true });
    const b = await sendOf(context, TWIN, { on: true });
    // 2,520 x 1,400 is what the BROWSER decodes (EXIF applied); the stored
    // JPEG is 1,400 x 2,520, which is what cv2.imdecode would have read.
    expect(a.sent).toMatchObject({ png: true, width: 2520, height: 1400 });
    expect(b.sent).toMatchObject({ png: true, width: 2520, height: 1400 });
    expect(a.stored).toHaveLength(1);
    expect(a.stored[0]).toMatchObject({ type: "image/png", png: true, width: 2520, height: 1400 });
    // Compared as pixels, both drawn by the same canvas path. The two JPEGs
    // were encoded separately (sideways and upright), so their DCT blocks
    // differ at flat-colour edges by a level or two; a wrong rotation or a
    // missing flip differs by whole colours.
    const diff = await a.page.evaluate(async ([x, y]) => {
      const px = async (b64) => {
        const bin = atob(b64);
        const bytes = Uint8Array.from(bin, (c) => c.charCodeAt(0));
        const bmp = await createImageBitmap(new Blob([bytes], { type: "image/png" }));
        const cv = new OffscreenCanvas(bmp.width, bmp.height);
        const cx = cv.getContext("2d");
        cx.drawImage(bmp, 0, 0);
        return cx.getImageData(0, 0, bmp.width, bmp.height).data;
      };
      const [p, q] = [await px(x), await px(y)];
      let max = 0, sum = 0, over8 = 0;
      for (let i = 0; i < p.length; i++) {
        if ((i & 3) === 3) continue;
        const d = Math.abs(p[i] - q[i]);
        if (d > max) max = d;
        if (d > 8) over8++;
        sum += d;
      }
      return { max, mean: sum / ((p.length / 4) * 3), over8, n: p.length / 4 };
    }, [a.sent.b64, b.sent.b64]);
    console.log(`rotated vs twin: max channel diff ${diff.max}, mean ${diff.mean.toFixed(4)}, ${diff.over8} of ${diff.n} px channels over 8`);
    expect(diff.mean).toBeLessThan(0.5);
    expect(diff.over8 / diff.n).toBeLessThan(0.01);
    await a.page.close();
    await b.page.close();
  });
});
