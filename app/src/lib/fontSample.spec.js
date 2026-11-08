// Stitched font samples (lib/fontSample.js): what each tile sews, at what
// size, and -- the part that matters most -- that the queue feeding it only
// ever loads the fonts it was asked for. The font browser was rebuilt once
// already because opening it fetched every binary (~30 MB); these pin that a
// sample cannot bring that back.
import { describe, it, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const here = dirname(fileURLToPath(import.meta.url));
const FONT_DIR = join(here, "..", "..", "..", "src", "fonts");

let EMB, S;
const fonts = {};
beforeAll(async () => {
  for (const f of ["units", "sewtime", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "crossfill", "satinfont", "fontbin", "dst", "digitize"])
    require("../../../src/" + f + ".js");
  EMB = globalThis.EMB;
  S = await import("./fontSample.js");
  for (const k of ["small_font", "cats", "heavenly", "initials_medium", "jersey_15", "hebrew_font_large", "apesplit"])
    fonts[k] = EMB.decodeFontBin(readFileSync(join(FONT_DIR, "bin", k + ".embf")));
});

const flush = () => new Promise((r) => setTimeout(r, 0));
async function settle(q) { for (let i = 0; i < 50 && !q.idle; i++) await flush(); }

describe("sampleTextFor", () => {
  it("sets the full sample when the font has every glyph", () => {
    expect(S.sampleTextFor(fonts.cats)).toBe("Abc 123");
  });
  it("keeps what a caps-only face can sew rather than nothing", () => {
    const caps = { glyphs: { A: {}, B: {}, C: {}, 1: {}, 2: {}, 3: {} } };
    expect(S.sampleTextFor(caps)).toBe("ABC 123");
  });
  it("drops only the characters a font is missing", () => {
    // apesplit is caps only, with no digits: it sews what it has.
    expect(S.sampleTextFor(fonts.apesplit)).toBe("ABC");
  });
  it("falls back to the font's own glyphs for a non-Latin face", () => {
    const t = S.sampleTextFor(fonts.hebrew_font_large);
    expect(t.length).toBeGreaterThan(0);
    expect(/[A-Za-z0-9]/.test(t)).toBe(false);
  });
});

describe("buildSample", () => {
  it("sews every font at the same fixed height, whatever its natural size", () => {
    // Natural sizes in the manifest run from 14 mm (small_font) to 117
    // (initials_medium); the sample must not inherit any of them.
    for (const k of ["small_font", "cats", "heavenly", "initials_medium", "jersey_15"]) {
      const d = S.buildSample(EMB, fonts[k]);
      expect(d.stitchCount, k).toBeGreaterThan(100);
      // heightMM is the SEWN extent: pull compensation and a cross's rail
      // ends move it a little either side of the glyph box (7.5-8.3 at an
      // 8 mm target, measured), so the bound is +-12%.
      expect(d.heightMM, k).toBeGreaterThan(S.SAMPLE_HEIGHT_MM * 0.88);
      expect(d.heightMM, k).toBeLessThan(S.SAMPLE_HEIGHT_MM * 1.12);
    }
  });
  it("returns an empty design rather than throwing for a font that cannot sew it", () => {
    const d = S.buildSample(EMB, fonts.cats, { text: "א" });
    expect(d.stitchCount).toBe(0);
  });
});

// A recording 2D context: enough surface for drawThreads.
function recCtx() {
  const pts = [];
  const calls = { fillRect: [], stroke: 0 };
  const ctx = {
    lineCap: "", lineJoin: "", strokeStyle: "", fillStyle: "", lineWidth: 1, globalAlpha: 1,
    setLineDash() {}, beginPath() {}, save() {}, restore() {}, setTransform() {},
    moveTo(x, y) { pts.push([x, y]); }, lineTo(x, y) { pts.push([x, y]); },
    stroke() { calls.stroke++; }, fillRect(...a) { calls.fillRect.push(a); },
  };
  return { ctx, pts, calls };
}

describe("drawSample", () => {
  it("lays fabric first, then thread, all inside the tile's image box", () => {
    const { ctx, pts, calls } = recCtx();
    const ppm = S.drawSample(ctx, S.buildSample(EMB, fonts.cats));
    expect(calls.fillRect[0]).toEqual([0, 0, S.SAMPLE_BOX.w, S.SAMPLE_BOX.h]);
    expect(calls.stroke).toBeGreaterThan(0);
    expect(ppm).toBeGreaterThan(0);
    // Lit layers are offset across the strand by up to ~half a thread width,
    // so allow a thread width past the box edge.
    const slack = 2;
    for (const [x, y] of pts) {
      expect(x).toBeGreaterThan(-slack);
      expect(x).toBeLessThan(S.SAMPLE_BOX.w + slack);
      expect(y).toBeGreaterThan(-slack);
      expect(y).toBeLessThan(S.SAMPLE_BOX.h + slack);
    }
  });
  it("draws at the fixed display scale, and shrinks only a sample too wide for the box", () => {
    // heavenly is 36 mm wide at 10 mm tall: 3.5 px/mm is 126 px, inside 176 - 8.
    expect(S.drawSample(recCtx().ctx, S.buildSample(EMB, fonts.heavenly))).toBe(S.SAMPLE_PX_PER_MM);
    // small_font is 69 mm wide: 3.5 px/mm would be 242 px, so it shrinks.
    const ppm = S.drawSample(recCtx().ctx, S.buildSample(EMB, fonts.small_font));
    expect(ppm).toBeLessThan(S.SAMPLE_PX_PER_MM);
    expect(ppm).toBeGreaterThan(1.5);
  });
  it("draws nothing but fabric for an empty design", () => {
    const { ctx, calls } = recCtx();
    expect(S.drawSample(ctx, S.buildSample(EMB, fonts.cats, { text: "א" }))).toBe(0);
    expect(calls.stroke).toBe(0);
  });
});

describe("sampleEligible", () => {
  it("skips outline fonts and binaries over the byte cap", () => {
    expect(S.sampleEligible({ key: "a", bytes: 300_000 })).toBe(true);
    expect(S.sampleEligible({ key: "a" })).toBe(true); // older manifest: no bytes recorded
    expect(S.sampleEligible({ key: "b", bytes: S.SAMPLE_MAX_BYTES + 1 })).toBe(false);
    expect(S.sampleEligible({ key: "outline:x", kind: "outline" })).toBe(false);
  });
  it("leaves out the multi-megabyte binaries of the shipped library", () => {
    const man = JSON.parse(readFileSync(join(FONT_DIR, "manifest.json"), "utf8"));
    const big = man.fonts.filter((f) => !S.sampleEligible(f)).map((f) => f.key);
    for (const k of ["califragilistic", "alchemy", "barstitch_mandala", "ags_garamond_latin_grec"]) expect(big).toContain(k);
    // ...and keeps most of it: a cap that excluded half the library would
    // make the stitched sample the exception.
    expect(man.fonts.length - big.length).toBeGreaterThanOrEqual(Math.round(man.fonts.length * 0.8));
  });
});

describe("createSampleQueue", () => {
  function harness(extra) {
    const loads = [];
    let active = 0, peak = 0;
    const gates = new Map();
    const q = S.createSampleQueue({
      cache: new Map(),
      yieldFn: () => Promise.resolve(),
      load: (key) => {
        loads.push(key);
        active++; peak = Math.max(peak, active);
        return new Promise((res, rej) => gates.set(key, { res: (v) => { active--; res(v); }, rej: (e) => { active--; rej(e); } }));
      },
      render: (font, row) => "data:" + row.key,
      ...extra,
    });
    return { q, loads, gates, peak: () => peak };
  }
  const row = (key, bytes = 100_000) => ({ key, bytes });

  it("loads only what it was asked for, at most two at a time, in request order", async () => {
    const ready = [];
    const h = harness({ onReady: (k, u) => ready.push([k, u]) });
    for (const k of ["a", "b", "c", "d"]) h.q.want(row(k));
    expect(h.loads).toEqual(["a", "b"]);
    h.gates.get("a").res({});
    await flush();
    expect(h.loads).toEqual(["a", "b", "c"]);
    for (const k of ["b", "c"]) h.gates.get(k).res({});
    await flush();
    h.gates.get("d").res({});
    await settle(h.q);
    expect(h.loads).toEqual(["a", "b", "c", "d"]);
    expect(h.peak()).toBe(2);
    expect(ready.map((r) => r[0]).sort()).toEqual(["a", "b", "c", "d"]);
    expect(ready[0][1]).toBe("data:a");
  });

  it("never loads a row taken back before its turn", async () => {
    const h = harness();
    for (const k of ["a", "b", "c", "d"]) h.q.want(row(k));
    h.q.unwant("c");
    h.q.unwant("d");
    h.gates.get("a").res({});
    h.gates.get("b").res({});
    await settle(h.q);
    expect(h.loads).toEqual(["a", "b"]);
  });

  it("never loads an outline font or a binary over the cap", async () => {
    const h = harness();
    h.q.want({ key: "outline:roboto", kind: "outline" });
    h.q.want(row("huge", 7_700_000));
    h.q.want(row("ok"));
    expect(h.loads).toEqual(["ok"]);
  });

  it("does not load a font twice: repeat asks, and a later queue sharing the cache", async () => {
    const cache = new Map();
    const h = harness({ cache });
    h.q.want(row("a"));
    h.q.want(row("a"));
    h.gates.get("a").res({});
    await settle(h.q);
    h.q.want(row("a"));
    expect(h.loads).toEqual(["a"]);
    const h2 = harness({ cache });
    h2.q.want(row("a"));
    expect(h2.loads).toEqual([]);
  });

  it("stops: nothing new loads and nothing in flight is rendered", async () => {
    let rendered = 0;
    const h = harness({ render: () => { rendered++; return "x"; } });
    for (const k of ["a", "b", "c"]) h.q.want(row(k));
    h.q.stop();
    h.gates.get("a").res({});
    h.gates.get("b").res({});
    await flush(); await flush();
    h.q.want(row("d"));
    expect(h.loads).toEqual(["a", "b"]);
    expect(rendered).toBe(0);
  });

  it("does not retry a failed load inside one opening of the browser", async () => {
    const h = harness();
    h.q.want(row("a"));
    h.gates.get("a").rej(new Error("offline"));
    await settle(h.q);
    h.q.want(row("a"));
    expect(h.loads).toEqual(["a"]);
  });

  it("reports idle only once every requested sample has finished or failed", async () => {
    const seen = [];
    const h = harness({ onChange: (idle) => seen.push(idle) });
    for (const k of ["a", "b", "c"]) h.q.want(row(k));
    expect(seen.every((v) => v === false)).toBe(true);
    h.gates.get("a").res({});
    await flush(); await flush();
    // "c" started in a's place: still busy, never a transient idle.
    expect(seen.at(-1)).toBe(false);
    h.gates.get("b").rej(new Error("offline"));
    await flush(); await flush();
    expect(seen.at(-1)).toBe(false);
    h.gates.get("c").res({});
    await settle(h.q);
    expect(seen.at(-1)).toBe(true);
    expect(seen.indexOf(true)).toBe(seen.length - 1);
    // A cached row asks for nothing and stays idle.
    h.q.want(row("a"));
    expect(h.loads).toEqual(["a", "b", "c"]);
    expect(h.q.idle).toBe(true);
  });
});
