// The customer's original artwork travels in the .embproj — end to end.
//
// Since 2026-09-20 a digitize sends the FILE the customer uploaded, not the
// panel's 1,200-px preview (the preview cost the nine corpus logos 503 -> 609
// trims, DOCTRINE 2026-09-19/20). The file's bytes live in IndexedDB, which
// is this browser's: a design opened on another machine, or after cleared
// site data, had only the preview and re-digitized from it with a note. So
// the .embproj now carries the originals beside the project
// (lib/projectFile.js `sources`) and the import puts them back in the store
// (lib/projectSources.js).
//
// The unit tests pin the envelope and the bridge against fakes. This drives
// the real thing: upload -> export -> read the downloaded file -> wipe the
// browser (localStorage AND IndexedDB, which is what "another machine" is)
// -> import -> the original is back under its content key, the registry
// record never carried the bytes, and — with the digitizer service up — the
// re-digitize request carries the file itself.
import { test, expect } from "@playwright/test";
import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SERVICE_URL = "http://127.0.0.1:8721";
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ART_PNG = path.join(__dirname, "fixtures", "enthusiast_logo.png");
const ART = readFileSync(ART_PNG);
// The store's key is the SHA-256 of the bytes (lib/sourceStore.js), so the
// file's `sources` map has exactly one, predictable key.
const ART_KEY = createHash("sha256").update(ART).digest("hex");

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

// The length of the record the store holds under `key`, 0 when absent, -1 when
// the database cannot be read. Opens the store's own database by name.
function storedLength(page, key) {
  return page.evaluate(
    (key) =>
      new Promise((resolve) => {
        const open = indexedDB.open("embstudio-sources", 1);
        open.onupgradeneeded = () => {
          if (!open.result.objectStoreNames.contains("sources")) open.result.createObjectStore("sources");
        };
        open.onerror = () => resolve(-1);
        open.onsuccess = () => {
          const db = open.result;
          let tx;
          try {
            tx = db.transaction("sources", "readonly");
          } catch (e) {
            db.close();
            resolve(-1);
            return;
          }
          const get = tx.objectStore("sources").get(key);
          get.onsuccess = () => {
            const r = get.result;
            db.close();
            resolve(r && r.bytes ? r.bytes.length || r.bytes.byteLength || 0 : 0);
          };
          get.onerror = () => {
            db.close();
            resolve(-1);
          };
        };
      }),
    key
  );
}

async function uploadArtwork(page) {
  await page.goto("/");
  await page.getByRole("button", { name: "Tote", exact: true }).click();
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByRole("button", { name: "Artwork" }).click();
  await page.locator(".dgp-upload input[type=file]").setInputFiles(ART_PNG);
  // The panel stores the file before it patches the element; wait for the
  // record rather than for a digitize, which needs the service.
  await expect.poll(() => storedLength(page, ART_KEY), { timeout: 30_000 }).toBe(ART.length);
  await expect(page.locator("img.dgp-thumb")).toBeVisible();
}

async function openDrawer(page) {
  if (await page.locator(".drawer").count()) return;
  await page.getByRole("button", { name: /My designs/ }).first().click();
  await expect(page.locator(".drawer")).toBeVisible();
}

async function exportCurrent(page) {
  await openDrawer(page);
  const [dl] = await Promise.all([
    page.waitForEvent("download"),
    page.locator(".drawer-row.current").getByRole("button", { name: "Export" }).click(),
  ]);
  const text = readFileSync(await dl.path(), "utf8");
  return { filename: dl.suggestedFilename(), text, json: JSON.parse(text) };
}

// "Another machine": no registry, no source store.
async function wipeBrowser(page) {
  await page.evaluate(
    () =>
      new Promise((resolve) => {
        localStorage.clear();
        const del = indexedDB.deleteDatabase("embstudio-sources");
        del.onsuccess = del.onerror = del.onblocked = () => resolve();
      })
  );
  await page.goto("/");
  expect(await storedLength(page, ART_KEY)).toBe(0);
}

async function importFile(page, filename, text) {
  await openDrawer(page);
  await page
    .getByLabel("Import design file")
    .setInputFiles({ name: filename, mimeType: "application/json", buffer: Buffer.from(text, "utf8") });
  // A successful import closes the drawer and enters the design on Content.
  await expect(page.locator(".drawer")).toHaveCount(0);
}

// ---- the tests -----------------------------------------------------------------

test("the export carries the uploaded file byte for byte, beside the project and outside the registry", async ({ page }) => {
  await uploadArtwork(page);
  const { filename, json } = await exportCurrent(page);

  expect(filename).toBe("enthusiast-logo.embproj");
  expect(json.version).toBe(2);
  expect(Object.keys(json.sources)).toEqual([ART_KEY]);
  const src = json.sources[ART_KEY];
  expect(src.type).toBe("image/png");
  expect(src.name).toBe("enthusiast_logo.png");
  expect(src.size).toBe(ART.length);
  expect(Buffer.from(src.data, "base64").equals(ART)).toBe(true);

  // The element points at the key and carries no bytes; neither does the
  // registry record the file was built from.
  const el = json.project.elements.find((e) => e.type === "digitized");
  expect(el.sourceFile.key).toBe(ART_KEY);
  expect(JSON.stringify(json.project)).not.toContain(src.data.slice(0, 48));
  const registry = await page.evaluate(() =>
    Object.keys(localStorage)
      .filter((k) => k.startsWith("embstudio:p:"))
      .map((k) => localStorage.getItem(k))
  );
  expect(registry.length).toBeGreaterThan(0);
  for (const record of registry) expect(record).not.toContain(src.data.slice(0, 48));
});

test("imported on a wiped browser, the original is back in the store under its content key", async ({ page }) => {
  await uploadArtwork(page);
  const { filename, text, json } = await exportCurrent(page);

  await wipeBrowser(page);
  await importFile(page, filename, text);

  await expect.poll(() => storedLength(page, ART_KEY), { timeout: 30_000 }).toBe(ART.length);
  // The design is open on the artwork lane with its preview, and the panel
  // has no fallback note to show: nothing has digitized from the preview.
  await expect(page.locator("img.dgp-thumb")).toBeVisible();
  await expect(page.getByTestId("source-note")).toHaveCount(0);
  // The registry record still carries only the key. (Two records: the blank
  // design the app made on boot after the wipe, and the import.)
  const registry = await page.evaluate(() =>
    Object.keys(localStorage)
      .filter((k) => k.startsWith("embstudio:p:"))
      .map((k) => localStorage.getItem(k))
  );
  const imported = registry.filter((r) => r.includes(ART_KEY));
  expect(imported.length).toBe(1);
  // The record holds the 1,200-px preview and the stitch result, as it always
  // did — never the original's bytes.
  expect(imported[0]).not.toContain(json.sources[ART_KEY].data.slice(0, 48));
});

test("a re-digitize after the import sends the file itself, not the preview", async ({ page }) => {
  test.skip(!serviceUp, skipReason);
  test.setTimeout(300_000);

  await uploadArtwork(page);
  const { filename, text } = await exportCurrent(page);
  await wipeBrowser(page);
  await importFile(page, filename, text);
  await expect.poll(() => storedLength(page, ART_KEY), { timeout: 30_000 }).toBe(ART.length);

  // Chromium exposes no post data for a multipart body with a Blob part, so
  // the request is read where the panel makes it: `startDigitize` resolves
  // `globalThis.fetch` at call time, and this hook records the `image` part
  // of every /digitize POST before handing the call on.
  await page.evaluate(() => {
    const orig = window.fetch;
    window.__digitizeSends = [];
    window.fetch = async function (url, init) {
      if (typeof url === "string" && /\/digitize$/.test(url) && init && init.body instanceof FormData) {
        const img = init.body.get("image");
        const head = img ? Array.from(new Uint8Array(await img.slice(0, 16).arrayBuffer())) : null;
        window.__digitizeSends.push({ name: img && img.name, type: img && img.type, size: img && img.size, head });
      }
      return orig.call(this, url, init);
    };
  });

  const run = page.getByRole("button", { name: /^Digitize( again)?$/ });
  await expect(run).toBeEnabled({ timeout: 30_000 });
  await run.click();
  await expect.poll(() => page.evaluate(() => window.__digitizeSends.length), { timeout: 30_000 }).toBe(1);
  const sent = await page.evaluate(() => window.__digitizeSends[0]);
  // The file itself, under its own name — not `art.png`, the preview's.
  expect(sent.name).toBe("enthusiast_logo.png");
  expect(sent.type).toBe("image/png");
  expect(sent.size).toBe(ART.length);
  expect(sent.head).toEqual(Array.from(ART.subarray(0, 16)));

  await expect(page.locator(".dgp-stats")).toBeVisible({ timeout: 120_000 });
  await expect(page.getByTestId("source-note")).toHaveCount(0);
});
