// A very large upload (6000x6000, ~20 MB PNG) is downscaled in the browser to
// the 2,800-px long side the digitizer service decodes to, and THAT is what the
// source store keeps and /digitize would send. Before, it exceeded the
// service's 12 MB upload limit, so the panel fell back to the 1,200-px
// low-smoothing preview. A normal-size image is untouched (design-originals
// spec pins that byte for byte). No service needed: the store is written on
// upload, before any digitize.
import { test, expect } from "@playwright/test";
import { startStudio, pickGarment, uploadArtwork } from "./helpers.js";
import { deflateSync } from "node:zlib";

const SIDE = 6000;
const MAX_UPLOAD = 12 * 1024 * 1024;

function crc32(buf) {
  let c, crc = 0xffffffff;
  for (let n = 0; n < buf.length; n++) {
    c = (crc ^ buf[n]) & 0xff;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    crc = (crc >>> 8) ^ c;
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function chunk(type, data) {
  const len = Buffer.alloc(4);
  len.writeUInt32BE(data.length);
  const td = Buffer.concat([Buffer.from(type), data]);
  const crc = Buffer.alloc(4);
  crc.writeUInt32BE(crc32(td));
  return Buffer.concat([len, td, crc]);
}

// A red disc on white, 6000x6000, plus ~20 MB of ancillary-chunk padding so the
// FILE is ~20 MB like a real print-resolution export while the pixels stay
// plain (a noisy raster would trip the unrelated 1.5 MB preview cap instead).
function bigPng() {
  const rowLen = 1 + SIDE * 3;
  const raw = Buffer.alloc(rowLen * SIDE);
  const c = SIDE / 2, r2 = (SIDE * 0.4) ** 2;
  for (let y = 0; y < SIDE; y++) {
    let o = y * rowLen + 1;
    for (let x = 0; x < SIDE; x++) {
      const inside = (x - c) ** 2 + (y - c) ** 2 < r2;
      raw[o++] = inside ? 200 : 252;
      raw[o++] = inside ? 30 : 252;
      raw[o++] = inside ? 30 : 252;
    }
  }
  const pad = Buffer.alloc(20 * 1024 * 1024);
  let seed = 12345;
  for (let i = 0; i < pad.length; i++) {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    pad[i] = seed >>> 24;
  }
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(SIDE, 0);
  ihdr.writeUInt32BE(SIDE, 4);
  ihdr[8] = 8; ihdr[9] = 2;
  return Buffer.concat([
    Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr), chunk("prVt", pad), chunk("IDAT", deflateSync(raw, { level: 1 })), chunk("IEND", Buffer.alloc(0)),
  ]);
}

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
            resolve(all.result.map((r) => ({
              type: r.type, size: r.bytes.length || r.bytes.byteLength,
              head: Array.from(new Uint8Array(r.bytes.buffer || r.bytes).slice(0, 24)),
            })));
          };
          all.onerror = () => { db.close(); resolve([]); };
        };
      })
  );
}

test("a 6000x6000 ~20 MB PNG is stored downscaled to 2,800 px and under the upload limit", async ({ page }) => {
  test.setTimeout(180_000);
  const buffer = bigPng();
  expect(buffer.length).toBeGreaterThan(MAX_UPLOAD);
  await startStudio(page);
  await pickGarment(page, "Tote");
  const t0 = Date.now();
  await uploadArtwork(page, { name: "huge.png", mimeType: "image/png", buffer }, { run: false });
  await expect.poll(async () => (await storedRecords(page)).length, { timeout: 120_000 }).toBe(1);
  console.log(`large upload: ${(buffer.length / 1048576).toFixed(1)} MB in, stored in ${Date.now() - t0} ms`);
  const [rec] = await storedRecords(page);
  expect(rec.type).toBe("image/png");
  expect(rec.size).toBeLessThanOrEqual(MAX_UPLOAD);
  // IHDR width/height at bytes 16..23: 6000 -> 2800 on both sides.
  const u32 = (i) => ((rec.head[i] << 24) | (rec.head[i + 1] << 16) | (rec.head[i + 2] << 8) | rec.head[i + 3]) >>> 0;
  expect([u32(16), u32(20)]).toEqual([2800, 2800]);
  await expect(page.locator("img.dgp-thumb")).toBeVisible();
});
