// exportPNG at a stated scale: the PNG is drawn at PNG_PX_PER_MM and carries a
// pHYs chunk (pixels per metre) so it prints at sewn size.
import { expect, test, vi } from "vitest";
import { deflateSync } from "fflate";

vi.mock("jspdf", () => ({ jsPDF: class FakeJsPDF {} }));
vi.mock("./preview.js", () => ({ renderRealistic: vi.fn() }));
vi.mock("./digitizer.js", () => ({ exportViaService: async () => ({}) }));
vi.mock("./emb.js", () => ({ EMB: {} }));

import { exportPNG, setPngPhys, PNG_PX_PER_MM, PNG_PAD_PX } from "./exporters.js";

const crcTable = Array.from({ length: 256 }, (_, n) => {
  let c = n;
  for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
  return c >>> 0;
});
const crc = (b) => {
  let c = 0xffffffff;
  for (const x of b) c = crcTable[(c ^ x) & 255] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
};
function chunk(type, data) {
  const out = new Uint8Array(12 + data.length);
  const dv = new DataView(out.buffer);
  dv.setUint32(0, data.length);
  for (let i = 0; i < 4; i++) out[4 + i] = type.charCodeAt(i);
  out.set(data, 8);
  dv.setUint32(8 + data.length, crc(out.subarray(4, 8 + data.length)));
  return out;
}
// A real (tiny-height) PNG of the given pixel size: 8-bit grey, all zero.
function fakePng(w, h) {
  const ihdr = new Uint8Array(13);
  const dv = new DataView(ihdr.buffer);
  dv.setUint32(0, w); dv.setUint32(4, h); ihdr[8] = 8; ihdr[9] = 0;
  const raw = new Uint8Array((w + 1) * h);
  const parts = [
    Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]),
    chunk("IHDR", ihdr), chunk("IDAT", deflateSync(raw)), chunk("IEND", new Uint8Array(0)),
  ];
  const out = new Uint8Array(parts.reduce((n, p) => n + p.length, 0));
  let o = 0; for (const p of parts) { out.set(p, o); o += p.length; }
  return out;
}
function readChunks(png) {
  const dv = new DataView(png.buffer, png.byteOffset, png.byteLength);
  const list = [];
  for (let off = 8; off + 12 <= png.length;) {
    const len = dv.getUint32(off);
    const type = String.fromCharCode(...png.subarray(off + 4, off + 8));
    const body = png.subarray(off + 8, off + 8 + len);
    const stored = dv.getUint32(off + 8 + len);
    list.push({ type, body, crcOk: stored === crc(png.subarray(off + 4, off + 8 + len)) });
    off += 12 + len;
  }
  return list;
}

async function run(design) {
  if (!globalThis.document) globalThis.document = { createElement: () => ({}) };
  const orig = globalThis.document.createElement;
  const canvas = {
    width: 0, height: 0, getContext: () => ({}),
    toBlob(cb) { cb(new Blob([fakePng(this.width, this.height)], { type: "image/png" })); },
  };
  globalThis.document.createElement = (t) => (t === "canvas" ? canvas : orig.call(globalThis.document, t));
  try {
    const out = await exportPNG(design);
    return { out, bytes: new Uint8Array(await out.blob.arrayBuffer()) };
  } finally {
    globalThis.document.createElement = orig;
  }
}

// 100 mm x 40 mm of stitches (DST units are 0.1 mm).
const stitchesFor = (wMM, hMM) => [
  { x: -wMM * 5, y: -hMM * 5, type: "stitch" }, { x: wMM * 5, y: hMM * 5, type: "stitch" },
];

test("pHYs ppm = px/mm x 1000 and the 100 mm design prints 100 mm wide (+/- 0.5)", async () => {
  const { out, bytes } = await run({ widthMM: 100, heightMM: 40, stitches: stitchesFor(100, 40) });
  const chunks = readChunks(bytes);
  expect(chunks.every((c) => c.crcOk)).toBe(true);
  expect(chunks.map((c) => c.type)).toEqual(["IHDR", "pHYs", "IDAT", "IEND"]);
  const ihdr = new DataView(chunks[0].body.buffer, chunks[0].body.byteOffset);
  const px = ihdr.getUint32(0), py = ihdr.getUint32(4);
  const p = new DataView(chunks[1].body.buffer, chunks[1].body.byteOffset);
  expect(p.getUint32(0)).toBe(PNG_PX_PER_MM * 1000);
  expect(p.getUint32(4)).toBe(PNG_PX_PER_MM * 1000);
  expect(chunks[1].body[8]).toBe(1); // metre
  expect(out.pxPerMm).toBe(PNG_PX_PER_MM);
  const ppm = p.getUint32(0);
  expect(Math.abs(((px - 2 * PNG_PAD_PX) / ppm) * 1000 - 100)).toBeLessThanOrEqual(0.5);
  expect(Math.abs(((py - 2 * PNG_PAD_PX) / ppm) * 1000 - 40)).toBeLessThanOrEqual(0.5);
});

test("an oversized design lowers the scale and pHYs follows it", async () => {
  const { out, bytes } = await run({ widthMM: 900, heightMM: 100, stitches: stitchesFor(900, 100) });
  const chunks = readChunks(bytes);
  const ihdr = new DataView(chunks[0].body.buffer, chunks[0].body.byteOffset);
  const ppm = new DataView(chunks[1].body.buffer, chunks[1].body.byteOffset).getUint32(0);
  expect(out.pxPerMm).toBeLessThan(PNG_PX_PER_MM);
  expect(ihdr.getUint32(0)).toBeLessThanOrEqual(6000);
  expect(Math.abs(((ihdr.getUint32(0) - 2 * PNG_PAD_PX) / ppm) * 1000 - 900)).toBeLessThanOrEqual(0.5);
});

test("setPngPhys replaces an existing pHYs and leaves non-PNG bytes alone", () => {
  const once = setPngPhys(fakePng(10, 4), 5000);
  const twice = setPngPhys(once, 7000);
  const ph = readChunks(twice).filter((c) => c.type === "pHYs");
  expect(ph).toHaveLength(1);
  expect(new DataView(ph[0].body.buffer, ph[0].body.byteOffset).getUint32(0)).toBe(7000);
  const junk = Uint8Array.from([1, 2, 3]);
  expect(setPngPhys(junk, 1)).toBe(junk);
});
