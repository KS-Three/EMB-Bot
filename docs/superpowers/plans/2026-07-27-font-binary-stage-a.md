# Font Binary Format + Lazy Loading (Slice 10 Stage A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 7.7 MB eager font registry with a 24.5x-smaller binary format loaded lazily per font, and grow the shipped library from 21 to 71 verified fonts.

**Architecture:** New engine module `src/fontbin.js` encodes a font JSON into a compact binary (`.embf`: quantize ×4 → per-ring delta → Int16 stream) and decodes it back. An offline tool builds `.embf` files plus a `manifest.json` carrying per-font tier/license metadata. The Studio loads the manifest eagerly and fetches font binaries on demand into the existing `EMB.SATIN_FONTS` object, so every synchronous call site keeps working once a font is ensured. `satin-fonts.js` leaves the Studio pipeline (the legacy `EMB-Bot.html` keeps it untouched until its separate audit).

**Tech Stack:** Vanilla JS dual-mode IIFE engine modules, `node:test` (engine), Svelte 5 + Vitest (app). Zero new dependencies — compression is HTTP-level brotli/gzip, native to browsers and servers.

## Global Constraints

- **Verified tier only ships.** The app must only ever see fonts with `tier: "verified"` (71 = 21 current + 50 new). Unverified fonts get no `.embf` and no manifest entry in the shipped set. Tier source of truth: `scratch_ink/_tiers.json`.
- **Decoder guard before removal.** `decode(encode(font))` must deep-equal `quantizeFont(font)` for ALL 21 currently-shipped fonts BEFORE `satin-fonts.js` leaves the Studio pipeline (spec §4.1a).
- **Quantization: Q = 4** (coords × 4, `Math.round`, Int16 deltas per ring, first delta absolute). Max error 0.125 units = 0.02–0.03 mm at typical `sizeMm` — beyond machine resolution.
- **No DOM in engine modules**; dual-mode IIFE wrapper exactly as `src/geometry.js:1-5`. **No new dependencies.**
- **Legacy `EMB-Bot.html` and `src/fonts/satin-fonts.js` are NOT touched.** The old tool keeps its 21 eager fonts until its audit (spec §3). Only the Studio (`app/`) switches to binary.
- **`ENGINE_FILES` is mirrored in three places** (`app/scripts/copy-engine.mjs`, `app/src/lib/emb.js` ENGINE_KEYS, `EMB-Bot.html` script tags). This slice changes the FIRST TWO only (drop `fonts/satin-fonts.js`, add `fontbin.js`); `EMB-Bot.html` keeps both its `satin-fonts.js` tag and does NOT get `fontbin.js` (it never decodes binaries). The `emb.spec.js` list-equality test must therefore change to compare against copy-engine only — see Task 3.
- Engine tests: `node --test` from repo root (baseline 177 on this branch). App tests: `cd app && npm test` (baseline 182). All green before every commit.
- Do NOT run `git push`.

## Branching note

Work happens on a new branch `feat/font-binary` created from `main` (2f5937f). It does NOT build on the parked `feat/svg-import-shapes` branch. Baseline engine suite on `main` is 169 (the 177 figure includes parked Slice 9's svgpath tests, which are not on `main`).

---

### Task 1: Binary encoder/decoder (`src/fontbin.js`)

**Files:**
- Create: `src/fontbin.js`
- Test: `test/fontbin.test.js`

**Interfaces:**
- Consumes: nothing (first task).
- Produces (all on `EMB`):
  - `quantizeFont(font, Q?)` → deep copy with every ring coordinate replaced by `Math.round(v*Q)/Q` (default Q=4).
  - `encodeFontBin(font, Q?)` → `Uint8Array` (.embf bytes).
  - `decodeFontBin(bytes)` → font object; `decode(encode(f))` deep-equals `quantizeFont(f)`.

**Format v1:** `"EMBF"` magic (4 bytes) · version u8 =1 · quant u8 · 2 reserved bytes · u32 LE metaLen · UTF-8 JSON meta · Int16 LE delta stream. The meta JSON is the font object with every "ring" (non-empty array whose every element is a 2-number array) replaced by `{"__r": pointCount}`; the stream holds the rings' delta-encoded points in depth-first traversal order. Per ring: first pair is the absolute quantized point, subsequent pairs are deltas. Encoder and decoder traverse identically (JSON key order is insertion order, preserved by `JSON.parse`/`stringify`), so no offsets table is needed.

- [ ] **Step 1: Write the failing test**

Create `test/fontbin.test.js`:

```js
const assert = require("node:assert");
const { test } = require("node:test");
const fb = require("../src/fontbin.js");

const FONT = {
  name: "T", license: "L", unitsPerEm: 100, sizeMm: 20,
  advDefault: 50, kerning: { AV: -3 },
  glyphs: {
    A: {
      adv: 40,
      cols: [{
        railA: [[0, 0], [10.26, 5.13], [20.5, 10.24]],
        railB: [[0, 4], [10.3, 9.1]],
        rungs: [[[0, 0], [0, 4]], [[20.5, 10.24], [10.3, 9.1]]],
      }],
      runs: [{ pts: [[1.111, 2.222], [3.333, 4.444]], jump: true }],
    },
    B: { adv: 30, cols: [], runs: [] },
  },
};

test("quantizeFont snaps ring coords to the Q grid and copies everything else", () => {
  const q = fb.quantizeFont(FONT, 4);
  assert.strictEqual(q.glyphs.A.cols[0].railA[1][0], 10.25); // round(10.26*4)=41 -> 10.25
  assert.strictEqual(q.glyphs.A.cols[0].railA[1][1], 5.25);  // round(5.13*4)=21 -> 5.25
  assert.strictEqual(q.name, "T");
  assert.strictEqual(q.glyphs.A.runs[0].jump, true);
  assert.notStrictEqual(q.glyphs.A.cols[0].railA, FONT.glyphs.A.cols[0].railA); // copy, not alias
  assert.strictEqual(FONT.glyphs.A.cols[0].railA[1][0], 10.26); // input untouched
});

test("encode/decode round-trips to exactly the quantized font", () => {
  const bytes = fb.encodeFontBin(FONT, 4);
  assert.ok(bytes instanceof Uint8Array);
  assert.deepStrictEqual(fb.decodeFontBin(bytes), fb.quantizeFont(FONT, 4));
});

test("header carries magic and version", () => {
  const b = fb.encodeFontBin(FONT, 4);
  assert.strictEqual(String.fromCharCode(b[0], b[1], b[2], b[3]), "EMBF");
  assert.strictEqual(b[4], 1);
  assert.strictEqual(b[5], 4);
});

test("binary is materially smaller than JSON for point-heavy data", () => {
  const big = { glyphs: { X: { adv: 1, cols: [{ railA:
    Array.from({ length: 4000 }, (_, i) => [i * 0.62, Math.sin(i / 9) * 40]) }] } } };
  const ratio = JSON.stringify(big).length / fb.encodeFontBin(big, 4).length;
  assert.ok(ratio > 3, "expected >3x, got " + ratio.toFixed(2));
});

test("empty arrays and negative/large coords survive", () => {
  const f = { glyphs: { Y: { adv: 0, cols: [], runs: [],
    weird: [[-800.25, 4000.75], [-799, 4001]] } } };
  assert.deepStrictEqual(fb.decodeFontBin(fb.encodeFontBin(f, 4)), fb.quantizeFont(f, 4));
});

test("decode rejects garbage", () => {
  assert.throws(() => fb.decodeFontBin(new Uint8Array([1, 2, 3, 4, 5, 6, 7, 8, 9])), /EMBF/);
});
```

- [ ] **Step 2: Run to verify it fails** — `node --test test/fontbin.test.js` → FAIL, cannot find module.

- [ ] **Step 3: Implement**

Create `src/fontbin.js`:

```js
// Compact binary font format (.embf) — see docs/superpowers/specs/
// 2026-07-27-font-library-expansion-design.md §4.1a. JSON stores coordinates
// as decimal text; this format quantizes to a Q-grid, delta-encodes each ring,
// and packs Int16 — measured 24.5x smaller than JSON before HTTP compression.
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.EMB = Object.assign(root.EMB || {}, api);
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  const MAGIC = "EMBF";
  const VERSION = 1;

  // A "ring" is a non-empty array whose every element is a [x, y] number pair.
  // This shape-based test (rather than key names like railA/rungs) keeps the
  // codec agnostic to the font schema — cols/rungs/runs.pts all match, and
  // future fields with point data are covered automatically.
  function isRing(v) {
    return Array.isArray(v) && v.length > 0 &&
      v.every((p) => Array.isArray(p) && p.length === 2 &&
        typeof p[0] === "number" && typeof p[1] === "number");
  }

  function quantizeFont(font, Q) {
    const q = Q || 4;
    return walk(font);
    function walk(v) {
      if (isRing(v)) return v.map((p) => [Math.round(p[0] * q) / q, Math.round(p[1] * q) / q]);
      if (Array.isArray(v)) return v.map(walk);
      if (v && typeof v === "object") {
        const o = {};
        for (const k of Object.keys(v)) o[k] = walk(v[k]);
        return o;
      }
      return v;
    }
  }

  function encodeFontBin(font, Q) {
    const q = Q || 4;
    const stream = []; // int16 values, dx dy pairs
    const skeleton = walk(font);
    function walk(v) {
      if (isRing(v)) {
        let px = 0, py = 0;
        for (let i = 0; i < v.length; i++) {
          const x = Math.round(v[i][0] * q), y = Math.round(v[i][1] * q);
          const dx = x - px, dy = y - py;
          if (dx < -32768 || dx > 32767 || dy < -32768 || dy > 32767)
            throw new Error("fontbin: delta overflow — ring jump exceeds Int16 at Q=" + q);
          stream.push(dx, dy);
          px = x; py = y;
        }
        return { __r: v.length };
      }
      if (Array.isArray(v)) return v.map(walk);
      if (v && typeof v === "object") {
        const o = {};
        for (const k of Object.keys(v)) o[k] = walk(v[k]);
        return o;
      }
      return v;
    }

    const metaBytes = utf8Encode(JSON.stringify(skeleton));
    const head = 4 + 1 + 1 + 2 + 4;
    const out = new Uint8Array(head + metaBytes.length + stream.length * 2);
    const dv = new DataView(out.buffer);
    out[0] = 69; out[1] = 77; out[2] = 66; out[3] = 70; // "EMBF"
    out[4] = VERSION;
    out[5] = q;
    dv.setUint32(8, metaBytes.length, true);
    out.set(metaBytes, head);
    let off = head + metaBytes.length;
    for (const v of stream) { dv.setInt16(off, v, true); off += 2; }
    return out;
  }

  function decodeFontBin(bytes) {
    const b = bytes instanceof Uint8Array ? bytes : new Uint8Array(bytes);
    if (b.length < 12 || String.fromCharCode(b[0], b[1], b[2], b[3]) !== MAGIC)
      throw new Error("fontbin: not an EMBF file");
    if (b[4] !== VERSION) throw new Error("fontbin: unsupported EMBF version " + b[4]);
    const q = b[5];
    const dv = new DataView(b.buffer, b.byteOffset, b.byteLength);
    const metaLen = dv.getUint32(8, true);
    const head = 12;
    const skeleton = JSON.parse(utf8Decode(b.subarray(head, head + metaLen)));
    let off = head + metaLen;
    function nextPair() {
      const dx = dv.getInt16(off, true), dy = dv.getInt16(off + 2, true);
      off += 4;
      return [dx, dy];
    }
    return walk(skeleton);
    function walk(v) {
      if (v && typeof v === "object" && !Array.isArray(v) &&
          typeof v.__r === "number" && Object.keys(v).length === 1) {
        const ring = [];
        let px = 0, py = 0;
        for (let i = 0; i < v.__r; i++) {
          const [dx, dy] = nextPair();
          px += dx; py += dy;
          ring.push([px / q, py / q]);
        }
        return ring;
      }
      if (Array.isArray(v)) return v.map(walk);
      if (v && typeof v === "object") {
        const o = {};
        for (const k of Object.keys(v)) o[k] = walk(v[k]);
        return o;
      }
      return v;
    }
  }

  // TextEncoder exists in browsers and Node >= 11; Buffer fallback is for
  // completeness only.
  function utf8Encode(s) {
    if (typeof TextEncoder !== "undefined") return new TextEncoder().encode(s);
    return new Uint8Array(Buffer.from(s, "utf8"));
  }
  function utf8Decode(b) {
    if (typeof TextDecoder !== "undefined") return new TextDecoder().decode(b);
    return Buffer.from(b).toString("utf8");
  }

  return { quantizeFont, encodeFontBin, decodeFontBin };
});
```

- [ ] **Step 4: Run to verify it passes** — `node --test test/fontbin.test.js` → PASS, 6 tests.
- [ ] **Step 5: Full engine suite** — `node --test` → PASS, 175 (169 baseline + 6).
- [ ] **Step 6: Commit**

```bash
git add src/fontbin.js test/fontbin.test.js
git commit -m "feat: EMBF binary font codec (quantize + delta + Int16)"
```

---

### Task 2: Build tool, manifest, and the 21-font decoder guard

**Files:**
- Create: `tools/build-embf.mjs`
- Create: `tools/font-categories.json`
- Test: `test/embf-guard.test.js`
- Create (generated, committed): `src/fonts/bin/*.embf` for the 21 current fonts + `src/fonts/manifest.json`

**Interfaces:**
- Consumes: `EMB.encodeFontBin`/`decodeFontBin`/`quantizeFont` from Task 1; existing `src/fonts/<key>.json` (21); `scratch_ink/_tiers.json` (tier data).
- Produces:
  - `src/fonts/bin/<key>.embf` per verified font.
  - `src/fonts/manifest.json`: `{ version: 1, fonts: [{ key, name, tier, group, licenseId, sizeMm, glyphCount, bytes }] }` — sorted by key, **verified only**.
  - `node tools/build-embf.mjs` is idempotent and rebuildable from sources.

- [ ] **Step 1: Write the guard test**

Create `test/embf-guard.test.js`:

```js
// Spec §4.1a guard: for every currently-shipped font, the binary round-trip
// must equal the quantized reference EXACTLY, and lettering built from the
// decoded font must be structurally sound. This test must be green before
// satin-fonts.js leaves the Studio pipeline (Task 3).
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const fb = require("../src/fontbin.js");

const FONT_DIR = path.join(__dirname, "..", "src", "fonts");
const BIN_DIR = path.join(FONT_DIR, "bin");
const keys = fs.readdirSync(FONT_DIR)
  .filter((f) => f.endsWith(".json") && f !== "manifest.json")
  .map((f) => f.replace(/\.json$/, ""));

test("all 21 shipped fonts have a committed .embf", () => {
  assert.ok(keys.length >= 21, "expected >=21 font JSONs, found " + keys.length);
  for (const k of keys)
    assert.ok(fs.existsSync(path.join(BIN_DIR, k + ".embf")), "missing bin for " + k);
});

for (const k of keys) {
  test("decoder guard: " + k, () => {
    const ref = JSON.parse(fs.readFileSync(path.join(FONT_DIR, k + ".json"), "utf8"));
    const bin = fs.readFileSync(path.join(BIN_DIR, k + ".embf"));
    assert.deepStrictEqual(fb.decodeFontBin(bin), fb.quantizeFont(ref, 4));
  });
}

test("manifest lists every shipped font exactly once, verified tier only", () => {
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const manKeys = man.fonts.map((f) => f.key);
  assert.strictEqual(new Set(manKeys).size, manKeys.length, "duplicate keys");
  for (const k of keys) assert.ok(manKeys.includes(k), "manifest missing " + k);
  for (const f of man.fonts) {
    assert.strictEqual(f.tier, "verified");
    assert.ok(f.name && f.licenseId && f.sizeMm > 0 && f.glyphCount > 0, "bad entry " + f.key);
    assert.ok(fs.existsSync(path.join(BIN_DIR, f.key + ".embf")), "manifest entry without bin: " + f.key);
  }
});
```

- [ ] **Step 2: Run to verify it fails** — `node --test test/embf-guard.test.js` → FAIL (no bin dir).

- [ ] **Step 3: Write the build tool**

Create `tools/font-categories.json` — display group per key (existing 21 copied from `FontSelect.svelte`'s `FONT_GROUP_MAP`; new 50 assigned by name/preview, adjustable later — unknown keys fall back to "More" in the UI, so a wrong guess is cosmetic):

```json
{
  "geneva_simple": "Sans", "medium_font": "Sans", "barstitch_regular": "Sans",
  "barstitch_bold": "Sans", "excalibur_KOR": "Sans", "milli_marif_bold": "Sans",
  "apex_simple_AGS": "Serif", "violin_serif": "Serif", "emilio_20": "Serif",
  "emilio_20_bold": "Serif", "roman_ags": "Serif",
  "aventurina": "Script", "pacificlo": "Script", "amitaclo": "Script",
  "mam_script": "Script", "chicken_scratch": "Script", "monicha": "Script",
  "auberge_marif": "Script", "digory_doodles_bean": "Script",
  "manga_impact": "Display", "tt_masters": "Display",
  "abecedaire_simple": "Sans", "apex_lake": "Display", "apesplit": "Display",
  "allegria55": "Script", "ambigue": "Script", "bathaus_FI": "Display",
  "bluenesia_satin": "Script", "caesarus_SC_FI": "Serif", "caffeine_KOR": "Display",
  "califragilistic_satin": "Script", "cherryforinkstitch": "Script",
  "cherryforkaalleen": "Script", "chicken_little": "Sans", "cooper_marif": "Display",
  "dejavufont": "Sans", "dinomouse72": "Display", "cats": "Display",
  "cogs_KOR": "Display", "colorful": "Display", "eloquent_satin": "Script",
  "emilio_20_simple": "Serif", "excalibur_small": "Sans", "geneva_rounded": "Sans",
  "gingo200": "Sans", "glacial_tiny": "Sans", "honoka_satin": "Display",
  "infinipicto": "Display", "initials_medium": "Display", "invercelia": "Script",
  "jersey_15_satin": "Display", "kum_tsoan_AGS": "Serif", "learning_curve_satin": "Script",
  "magnolia_KOR": "Script", "mai_en_fleur": "Script", "malika": "Script",
  "mam_legende": "Script", "marifenda": "Script", "mimosa_large": "Script",
  "mimosa_medium": "Script", "montecarlo": "Script", "nick_ainley_satin": "Script",
  "pacificlo_tiny": "Script", "pixel10": "Display", "precious": "Script",
  "priscilla_satin": "Script", "small_font": "Sans", "stebor_AGS": "Display",
  "sunset": "Script", "tt_directors": "Display", "venezia_small": "Serif"
}
```

Note: this map deliberately over-lists — keys present in the map but absent from the verified set are ignored by the build tool, and verified keys absent from the map get `"More"`. Do not treat map/verified mismatches as errors; the authoritative font list is the verified tier, never this map.

Create `tools/build-embf.mjs`:

```js
// Builds the binary font library + manifest from source JSONs.
//   node tools/build-embf.mjs
// Inputs:  src/fonts/<key>.json           (the 21 shipped fonts)
//          scratch_ink/_out/<key>.json    (trial imports of new fonts)
//          scratch_ink/_tiers.json        (tier classification, Kent-approved)
//          tools/font-categories.json     (display groups)
// Outputs: src/fonts/bin/<key>.embf   (VERIFIED tier only)
//          src/fonts/manifest.json
// Idempotent; safe to re-run. scratch_ink/ is gitignored source material —
// the committed artifacts are the .embf files and the manifest.
import { readFileSync, writeFileSync, mkdirSync, existsSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const fb = require("../src/fontbin.js");

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const FONT_DIR = join(root, "src", "fonts");
const BIN_DIR = join(FONT_DIR, "bin");
const GROUPS = JSON.parse(readFileSync(join(root, "tools", "font-categories.json"), "utf8"));

// license id from the first line of the font's license text
function licenseId(text) {
  const t = String(text || "");
  if (/SIL Open Font License|OFL/i.test(t)) return "OFL-1.1";
  if (/CC-BY-SA/i.test(t)) return "CC-BY-SA-4.0";
  if (/CC-BY/i.test(t)) return "CC-BY-4.0";
  if (/public domain|CC0/i.test(t)) return "CC0";
  return "SEE-LICENSE-FILE";
}

// 1. Shipped fonts: every src/fonts/<key>.json is verified by definition
//    (they are the 21 Kent already ships).
const sources = [];
for (const f of readdirSync(FONT_DIR)) {
  if (f.endsWith(".json") && f !== "manifest.json")
    sources.push({ key: f.replace(/\.json$/, ""), path: join(FONT_DIR, f), tier: "verified" });
}

// 2. New fonts: verified tier per _tiers.json, data from the trial imports.
const tiersPath = join(root, "scratch_ink", "_tiers.json");
if (existsSync(tiersPath)) {
  const tiers = JSON.parse(readFileSync(tiersPath, "utf8"));
  const have = new Set(sources.map((s) => s.key));
  for (const t of tiers) {
    if (t.tier !== "verified" || have.has(t.pack)) continue;
    const p = join(root, "scratch_ink", "_out", t.pack + ".json");
    if (!existsSync(p)) { console.warn("SKIP (no trial import):", t.pack); continue; }
    sources.push({ key: t.pack, path: p, tier: "verified" });
  }
} else {
  console.warn("scratch_ink/_tiers.json absent — building shipped fonts only");
}

mkdirSync(BIN_DIR, { recursive: true });
const manifest = [];
for (const s of sources.sort((a, b) => a.key.localeCompare(b.key))) {
  const font = JSON.parse(readFileSync(s.path, "utf8"));
  const bytes = fb.encodeFontBin(font, 4);
  // self-check every font on every build — cheap, and catches codec drift
  const back = fb.decodeFontBin(bytes);
  const want = fb.quantizeFont(font, 4);
  if (JSON.stringify(back) !== JSON.stringify(want))
    throw new Error("round-trip mismatch: " + s.key);
  writeFileSync(join(BIN_DIR, s.key + ".embf"), bytes);
  manifest.push({
    key: s.key,
    name: font.name || s.key,
    tier: s.tier,
    group: GROUPS[s.key] || "More",
    licenseId: licenseId(font.license),
    sizeMm: font.sizeMm || 0,
    glyphCount: Object.keys(font.glyphs || {}).length,
    bytes: bytes.length,
  });
}
writeFileSync(join(FONT_DIR, "manifest.json"),
  JSON.stringify({ version: 1, fonts: manifest }, null, 1));
const total = manifest.reduce((a, f) => a + f.bytes, 0);
console.log("built", manifest.length, "fonts,", (total / 1048576).toFixed(2), "MB binary");
```

- [ ] **Step 4: Run the build** — `node tools/build-embf.mjs`
Expected: `built 71 fonts, ~2.x MB binary` (50 new + 21; exact size may vary). If it prints 21, `scratch_ink/_tiers.json` is missing — stop and report, do not proceed with a partial library.

- [ ] **Step 5: Run the guard** — `node --test test/embf-guard.test.js` → PASS (21 shipped fonts round-trip + manifest checks).
- [ ] **Step 6: Full engine suite** — `node --test` → PASS (175 + guard tests).
- [ ] **Step 7: Commit** (binaries are committed artifacts, like satin-fonts.js was)

```bash
git add tools/build-embf.mjs tools/font-categories.json test/embf-guard.test.js src/fonts/bin src/fonts/manifest.json
git commit -m "feat: build EMBF binaries + manifest for 71 verified fonts"
```

---

### Task 3: Studio font loader; drop satin-fonts.js from the Studio pipeline

**Files:**
- Create: `app/src/lib/fontLoader.js`
- Test: `app/src/lib/fontLoader.spec.js`
- Modify: `app/scripts/copy-engine.mjs` (ENGINE_FILES + font copy step)
- Modify: `app/src/lib/emb.js` (ENGINE_KEYS)
- Modify: `app/src/lib/emb.spec.js`
- Create: `app/src/lib/testFonts.js` (spec preload helper)
- Modify: the 7 spec files that eval `satin-fonts.js` (listed in Step 5)

**Interfaces:**
- Consumes: `EMB.decodeFontBin` (Task 1), `src/fonts/manifest.json` + `src/fonts/bin/*.embf` (Task 2).
- Produces:
  - `loadManifest()` → `Promise<{version, fonts:[...]}>` (cached after first call).
  - `ensureFont(key)` → `Promise<fontData>`; populates `EMB.SATIN_FONTS[key]` so all existing synchronous reads keep working. Concurrent calls for the same key share one fetch. Unknown key → rejects with `Unknown font: <key>`.
  - `ensureFonts(keys)` → `Promise<void>` (parallel ensureFont).
  - Node path (vitest): reads `src/fonts/bin/` from disk. Browser path: fetches `/fonts/manifest.json` and `/fonts/<key>.embf`.
  - `app/src/lib/testFonts.js`: `preloadAllFontsSync()` — synchronous, decodes every manifest font from disk into `EMB.SATIN_FONTS` (spec files run in Node where sync fs is fine).

- [ ] **Step 1: Write the failing test**

Create `app/src/lib/fontLoader.spec.js`:

```js
import { describe, it, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);

beforeAll(() => {
  for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","fontbin","dst","exp","pes","svgexport","fonts","digitize"])
    require("../../../src/" + f + ".js");
});

describe("fontLoader", () => {
  it("loadManifest returns verified fonts and caches", async () => {
    const { loadManifest } = await import("./fontLoader.js");
    const m1 = await loadManifest();
    expect(m1.fonts.length).toBeGreaterThanOrEqual(71);
    expect(m1.fonts.every((f) => f.tier === "verified")).toBe(true);
    expect(await loadManifest()).toBe(m1); // same object -> cached
  });

  it("ensureFont populates EMB.SATIN_FONTS and returns the font", async () => {
    const { ensureFont } = await import("./fontLoader.js");
    const g = globalThis;
    delete (g.EMB.SATIN_FONTS || {}).geneva_simple;
    const font = await ensureFont("geneva_simple");
    expect(font.glyphs).toBeTruthy();
    expect(g.EMB.SATIN_FONTS.geneva_simple).toBe(font);
  });

  it("concurrent ensureFont calls share one load", async () => {
    const { ensureFont } = await import("./fontLoader.js");
    const [a, b] = await Promise.all([ensureFont("cats"), ensureFont("cats")]);
    expect(a).toBe(b);
  });

  it("unknown key rejects with a clear error", async () => {
    const { ensureFont } = await import("./fontLoader.js");
    await expect(ensureFont("nope_font")).rejects.toThrow(/Unknown font: nope_font/);
  });

  it("a newly imported font actually builds lettering", async () => {
    const { ensureFont } = await import("./fontLoader.js");
    const g = globalThis;
    const font = await ensureFont("cats");
    const design = g.EMB.buildLetteringDesign(font, "AB", {
      garment: g.EMB.getGarment("left_chest"), pxPerMm: 8, densityMm: 0.4,
    });
    expect(design.stitchCount).toBeGreaterThan(100);
  });
});
```

- [ ] **Step 2: Run to verify it fails** — `cd app && npx vitest run src/lib/fontLoader.spec.js` → FAIL, cannot resolve `./fontLoader.js`.

- [ ] **Step 3: Implement the loader**

Create `app/src/lib/fontLoader.js`:

```js
import { EMB } from "./emb.js";

// Lazy font delivery (spec §4.1). The manifest is small and loaded once;
// font binaries are fetched on demand, decoded via EMB.decodeFontBin, and
// cached on EMB.SATIN_FONTS so every existing synchronous call site
// (generate.js, FontSelect, TemplateRow, legacy specs) keeps working
// unchanged once a font has been ensured.
//
// Dual environment: in the browser, /fonts/* is served from app/public
// (copied by scripts/copy-engine.mjs). Under vitest (Node), files are read
// from src/fonts/ directly.
const IS_NODE = typeof window === "undefined";

let manifestPromise = null;
const fontPromises = new Map();

async function readBytes(rel) {
  if (IS_NODE) {
    const { readFileSync } = await import("node:fs");
    const { join, dirname } = await import("node:path");
    const { fileURLToPath } = await import("node:url");
    const here = dirname(fileURLToPath(import.meta.url));
    return readFileSync(join(here, "..", "..", "..", "src", "fonts", rel));
  }
  const res = await fetch("/fonts/" + rel);
  if (!res.ok) throw new Error("Font fetch failed: " + rel + " (" + res.status + ")");
  return new Uint8Array(await res.arrayBuffer());
}

export function loadManifest() {
  if (!manifestPromise) {
    manifestPromise = readBytes("manifest.json").then((b) => {
      const man = JSON.parse(new TextDecoder().decode(b));
      man.fonts = man.fonts.filter((f) => f.tier === "verified"); // belt & braces
      return man;
    });
  }
  return manifestPromise;
}

export function ensureFont(key) {
  const cached = (EMB.SATIN_FONTS || {})[key];
  if (cached) return Promise.resolve(cached);
  if (!fontPromises.has(key)) {
    fontPromises.set(key, (async () => {
      const man = await loadManifest();
      if (!man.fonts.some((f) => f.key === key)) {
        fontPromises.delete(key);
        throw new Error("Unknown font: " + key);
      }
      const bytes = await readBytes("bin/" + key + ".embf");
      const font = EMB.decodeFontBin(bytes);
      EMB.SATIN_FONTS = EMB.SATIN_FONTS || {};
      EMB.SATIN_FONTS[key] = font;
      return font;
    })());
  }
  return fontPromises.get(key);
}

export function ensureFonts(keys) {
  return Promise.all([...new Set(keys)].map(ensureFont)).then(() => {});
}
```

Create `app/src/lib/testFonts.js`:

```js
// Vitest-only synchronous preload. Replaces the old pattern of eval'ing
// src/fonts/satin-fonts.js (removed from the Studio pipeline in Slice 10):
// decodes every manifest font from disk into EMB.SATIN_FONTS so specs can
// keep reading it synchronously.
import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

export function preloadAllFontsSync() {
  const g = globalThis;
  if (!g.EMB || typeof g.EMB.decodeFontBin !== "function")
    throw new Error("preloadAllFontsSync: engine (incl. fontbin.js) must be required first");
  const here = dirname(fileURLToPath(import.meta.url));
  const binDir = join(here, "..", "..", "..", "src", "fonts", "bin");
  g.EMB.SATIN_FONTS = g.EMB.SATIN_FONTS || {};
  for (const f of readdirSync(binDir)) {
    if (!f.endsWith(".embf")) continue;
    const key = f.replace(/\.embf$/, "");
    if (!g.EMB.SATIN_FONTS[key])
      g.EMB.SATIN_FONTS[key] = g.EMB.decodeFontBin(readFileSync(join(binDir, f)));
  }
}
```

- [ ] **Step 4: Rewire the Studio pipeline**

In `app/scripts/copy-engine.mjs`: in `ENGINE_FILES`, replace the `"fonts/satin-fonts.js"` entry with `"fontbin.js"` placed immediately after `"satinfont.js"`. Then extend the copy step to also copy the font data (append after the existing loop):

```js
// Font binaries + manifest -> public/fonts (served at /fonts/*)
import { readdirSync } from "node:fs";
const fontsOut = join(here, "..", "public", "fonts");
mkdirSync(join(fontsOut, "bin"), { recursive: true });
copyFileSync(join(srcDir, "fonts", "manifest.json"), join(fontsOut, "manifest.json"));
for (const f of readdirSync(join(srcDir, "fonts", "bin")))
  if (f.endsWith(".embf"))
    copyFileSync(join(srcDir, "fonts", "bin", f), join(fontsOut, "bin", f));
console.log("copied font manifest + binaries to", fontsOut);
```

Also remove the now-unneeded `mkdirSync(join(outDir, "fonts"), ...)` line if nothing else uses it. Add `app/public/fonts/` to `app/.gitignore` (generated, like `public/engine/`— check how `public/engine` is ignored and mirror it; if `public/engine` is committed instead, commit `public/fonts` the same way. **Match the existing convention, whichever it is.**).

In `app/src/lib/emb.js`: apply the same two changes to `ENGINE_KEYS` (add `"fontbin.js"` after `"satinfont.js"`, remove `"fonts/satin-fonts.js"`).

In `app/src/lib/emb.spec.js`: the existing test asserts `Object.keys(EMB.SATIN_FONTS).length >= 14` after eval'ing satin-fonts.js. Replace that spec's satin-fonts eval (see Step 5) and change the assertion to run `preloadAllFontsSync()` then expect `>= 71`. Keep the ENGINE_KEYS/ENGINE_FILES equality test — it now covers `fontbin.js` automatically.

- [ ] **Step 5: Swap the 7 spec preloads**

Each of these evals satin-fonts.js by path (all use the identical `new Function(readFileSync(...))()` line): `combine.spec.js:7`, `emb.spec.js:8`, `exporters.spec.js:36`, `flatten.spec.js:7`, `generate.spec.js:7`, `imageRegions.spec.js:7`, `templates.spec.js:106`. In each: ensure `"fontbin"` is in the file's engine `require` list (add it if absent), then replace the eval line with:

```js
  const { preloadAllFontsSync } = await import("./testFonts.js");
  preloadAllFontsSync();
```

(If the surrounding function isn't async, `import` statically at the top of the file instead — these are ESM spec files, so a top-level `import { preloadAllFontsSync } from "./testFonts.js";` plus a call in the setup hook is the cleaner form. Use that.)

- [ ] **Step 6: Run all app tests** — `cd app && npm test` → PASS. Expected ≥ 187 (182 baseline + 5 loader specs; exact count may shift slightly with the emb.spec change).
- [ ] **Step 7: Engine suite still green** — `node --test` → PASS (satin-fonts.js untouched for the legacy tool).
- [ ] **Step 8: Commit**

```bash
git add app/src/lib/fontLoader.js app/src/lib/fontLoader.spec.js app/src/lib/testFonts.js app/scripts/copy-engine.mjs app/src/lib/emb.js app/src/lib/*.spec.js app/.gitignore
git commit -m "feat: lazy EMBF font loading in Studio; drop eager satin-fonts.js"
```

---

### Task 4: Async call sites — generate, FontSelect, TemplateRow

**Files:**
- Modify: `app/src/App.svelte` (generation flow)
- Modify: `app/src/ui/FontSelect.svelte`
- Modify: `app/src/ui/TemplateRow.svelte`

**Interfaces:**
- Consumes: `ensureFont`, `ensureFonts`, `loadManifest` from Task 3.
- Produces: no new exports. Behavior contract: generation never runs against a missing font; font list comes from the manifest; thumbnails render after their font arrives.

- [ ] **Step 1: Read the current generation flow**

Read `app/src/App.svelte` and find every call to `generateAll(` (the reactive/regeneration path — Slice 5 introduced it; Slice 8's KEY CONTRACT note says view-only changes skip `generateAll`). Identify the single function that invokes it (if it is called from more than one place, wrap ONE common entry point).

- [ ] **Step 2: Gate generation on fonts being present**

In `App.svelte`, import the loader and collect needed fonts before generating. The pattern (adapt names to what Step 1 found — the invariant is: `ensureFonts` resolves BEFORE `generateAll` runs, and a failed font load surfaces as the element error path, not an exception out of a reactive block):

```js
import { ensureFonts } from "./lib/fontLoader.js";

function fontKeysOf(project) {
  return (project.elements || [])
    .filter((el) => el.type === "text" && el.fontKey)
    .map((el) => el.fontKey);
}

// Replace the direct generateAll invocation:
//   const out = generateAll(project, runtime);
// with an awaited wrapper (the surrounding function becomes async; Svelte
// event handlers and $effect bodies may be async):
async function regenerate() {
  try {
    await ensureFonts(fontKeysOf(project));
  } catch (e) {
    generationError = String(e.message || e); // surface in the existing error UI
    return;
  }
  const out = generateAll(project, runtime);
  // ...existing post-generation code unchanged (combined, perElement, rects)
}
```

If `App.svelte` uses a reactive statement (`$:`) to trigger generation, keep the reactive trigger but have it call the async `regenerate()`; guard against overlapping runs with a simple in-flight flag if one is not already present (check first — Slice 8's rAF-throttling may already serialize this).

- [ ] **Step 3: FontSelect from the manifest**

In `app/src/ui/FontSelect.svelte` (line 44 area): the font list currently comes from `Object.entries(EMB.SATIN_FONTS)` — which is now empty at boot. Replace with the manifest, and drop the hardcoded `FONT_GROUP_MAP` in favor of manifest groups:

```js
import { loadManifest, ensureFont } from "../lib/fontLoader.js";

let fonts = [];
loadManifest().then((man) => {
  fonts = man.fonts.map((f) => ({ key: f.key, name: f.name, group: f.group }));
});
```

`groupedFonts` derives as before but reactively from `fonts` (it already recomputes when `fonts` changes — verify `$:` is on that derivation). `GROUP_ORDER` stays `["Sans", "Serif", "Script", "Display", "More"]`. Delete `FONT_GROUP_MAP` and `groupFor` — group data now lives in the manifest (single source of truth; `tools/font-categories.json` feeds it at build time).

In the thumbnail queue (line 71 area): before `EMB.buildLetteringDesign(EMB.SATIN_FONTS[key], "Sample", ...)`, await the font:

```js
      const font = await ensureFont(key);
      const design = EMB.buildLetteringDesign(font, "Sample", {
```

The queue is already idle-scheduled and cached (Slice 8); ensureFont resolving instantly for cached fonts keeps that behavior. 71 thumbnails × ~35 KB fetch as the user scrolls the open dropdown — acceptable for Stage A; Stage B's browser replaces this UI.

- [ ] **Step 4: TemplateRow**

`app/src/ui/TemplateRow.svelte:40` builds template previews from `EMB.SATIN_FONTS[el.fontKey]`. Same treatment: `const font = await ensureFont(el.fontKey);` then use `font` (the preview generation there is already async/idle — verify and slot in).

- [ ] **Step 5: Run all tests** — `cd app && npm test` → PASS. `node --test` → PASS.

- [ ] **Step 6: Browser acceptance (dev server)**

Serve the Studio (`preview_start` with the `emb-bot-studio` launch config; `predev` runs copy-engine which now also copies fonts). Verify, in order:
1. App boots with no console errors; network tab shows `manifest.json` fetched, NO `.embf` yet.
2. Type a name → generation works; exactly one `.embf` fetched (the default font).
3. Open the font dropdown → far more than 21 fonts, grouped; thumbnails fill in as fonts arrive.
4. Pick a new-import font (e.g. `montecarlo`) → text regenerates in it; DST downloads; stitch count sane.
5. Apply a quick-start template → renders (TemplateRow ensureFont path).
6. Reload → project restores (localStorage path untouched).

- [ ] **Step 7: Commit**

```bash
git add app/src/App.svelte app/src/ui/FontSelect.svelte app/src/ui/TemplateRow.svelte
git commit -m "feat: manifest-driven font list; generation awaits lazy fonts"
```

---

### Task 5: Quantization acceptance renders + new-font QC montage

**Files:**
- Create: `tools/render-font-compare.mjs`
- Create: `docs/superpowers/notes/2026-07-27-embf-acceptance.md`

**Interfaces:**
- Consumes: Tasks 1–2 outputs; existing `EMB.buildLetteringDesign`, `EMB.encodeDST`, and the DST render pattern from `tools/render-dst.mjs`.
- Produces: no code later tasks use. Human-reviewable evidence for the spec's risk #4 (quantization taste) and Kent's font QC loop.

- [ ] **Step 1: Write the compare harness**

Create `tools/render-font-compare.mjs`:

```js
// Renders "Kent" at hat scale (55mm) from (a) the original JSON font and
// (b) the decoded .embf, exports both DSTs, and reports stitch counts.
// PNGs via tools/render-dst.mjs. Usage:
//   node tools/render-font-compare.mjs geneva_simple aventurina montecarlo
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","fontbin","dst","fonts","digitize"])
  require("../src/" + f + ".js");
const EMB = globalThis.EMB;

const keys = process.argv.slice(2);
if (!keys.length) { console.error("usage: node tools/render-font-compare.mjs <key> [key...]"); process.exit(1); }

for (const key of keys) {
  const jsonPath = existsSync(`src/fonts/${key}.json`) ? `src/fonts/${key}.json` : `scratch_ink/_out/${key}.json`;
  const orig = JSON.parse(readFileSync(jsonPath, "utf8"));
  const deco = EMB.decodeFontBin(readFileSync(`src/fonts/bin/${key}.embf`));
  const opts = { garment: EMB.getGarment("hat_front"), pxPerMm: 8, densityMm: 0.4, targetWidthMm: 55 };
  const a = EMB.buildLetteringDesign(orig, "Kent", opts);
  const b = EMB.buildLetteringDesign(deco, "Kent", opts);
  writeFileSync(`scratch_ink/cmp_${key}_json.dst`, Buffer.from(EMB.encodeDST(a)));
  writeFileSync(`scratch_ink/cmp_${key}_embf.dst`, Buffer.from(EMB.encodeDST(b)));
  for (const side of ["json", "embf"])
    execFileSync("node", ["tools/render-dst.mjs", `scratch_ink/cmp_${key}_${side}.dst`, `scratch_ink/cmp_${key}_${side}.png`, "12"]);
  const drift = Math.abs(a.stitchCount - b.stitchCount) / a.stitchCount;
  console.log(`${key}: json=${a.stitchCount} embf=${b.stitchCount} drift=${(drift * 100).toFixed(2)}%`);
  if (drift > 0.01) console.log(`  WARNING: >1% stitch drift on ${key} — inspect the PNGs`);
}
```

- [ ] **Step 2: Run it on 3 fonts spanning the styles** — `node tools/render-font-compare.mjs geneva_simple aventurina montecarlo`
Expected: drift ≤ 1% per font (quantization at 0.02mm should barely move stitch placement). Open the PNG pairs and confirm they are visually indistinguishable at hat scale.

- [ ] **Step 3: Montage the 50 new fonts**

Render one sample per new font for Kent's QC eye (his standing rule: montage-render before shipping):

```bash
node -e "
const fs=require('node:fs');const man=JSON.parse(fs.readFileSync('src/fonts/manifest.json','utf8'));
const have=new Set(fs.readdirSync('src/fonts').filter(f=>f.endsWith('.json')&&f!=='manifest.json').map(f=>f.replace(/\.json$/,'')));
console.log(man.fonts.filter(f=>!have.has(f.key)).map(f=>f.key).join(' '));
" > scratch_ink/_newkeys.txt
for k in $(cat scratch_ink/_newkeys.txt); do node tools/render-font-compare.mjs "$k" || echo "RENDER FAIL $k"; done
```

Any `RENDER FAIL` or >1% drift: record it, and if the failure is real (not a harness quirk), REMOVE that font from verified — edit its tier in `scratch_ink/_tiers.json`, re-run `node tools/build-embf.mjs`, re-run the guard test. Shipping is verified-only; a font that cannot render a sample is not verified.

- [ ] **Step 4: Write the acceptance note**

`docs/superpowers/notes/2026-07-27-embf-acceptance.md`: per-font drift table for the 3 deep-compared fonts, the montage outcome (N rendered clean / M demoted with reasons), and final shipped count.

- [ ] **Step 5: Commit**

```bash
git add tools/render-font-compare.mjs docs/superpowers/notes/2026-07-27-embf-acceptance.md
git commit -m "test: EMBF quantization acceptance renders + new-font montage QC"
```

(If Step 3 demoted fonts: also `git add src/fonts/manifest.json src/fonts/bin` in this commit and say so in the message.)

---

### Task 6: Docs + final suites

**Files:**
- Modify: `README.md`
- Modify: `COOKBOOK.md`

- [ ] **Step 1: README** — update the font count (21 → the final shipped number from Task 5), describe the binary font library ("fonts load on demand; the app ships a manifest and per-font `.embf` binaries"), and note the standalone build is retired for new features (Studio is the product).
- [ ] **Step 2: COOKBOOK** — record: EMBF format (Q=4, delta, Int16, guard test `test/embf-guard.test.js`); `tools/build-embf.mjs` rebuild flow and that `scratch_ink/` is required to rebuild the full 71 (gitignored — the committed `.embf` files are the artifacts of record); the verified/unverified tier rule (verified-only ships, tier source `scratch_ink/_tiers.json`, mirrored into the manifest); legacy `EMB-Bot.html` still eager-loads `satin-fonts.js` (21 fonts) pending its audit; the three-place ENGINE_FILES sync is now a TWO-place sync for Studio files plus the untouched legacy page.
- [ ] **Step 3: Full suites one last time** — `node --test` and `cd app && npm test` → both green. Record final counts in the commit message.
- [ ] **Step 4: Commit**

```bash
git add README.md COOKBOOK.md
git commit -m "docs: binary font library, tiers, and rebuild flow"
```

---

## Definition of done

- [ ] `node --test` green; `cd app && npm test` green.
- [ ] Guard test proves decode(encode) == quantize for all 21 previously-shipped fonts.
- [ ] Studio boots fetching only the manifest; fonts fetch individually on demand.
- [ ] Font dropdown lists ~71 fonts from the manifest, grouped, with thumbnails.
- [ ] A newly imported font generates lettering and exports DST in the browser.
- [ ] 3-font hat-scale compare renders show no visible quantization difference; stitch drift ≤ 1%.
- [ ] All 50 new fonts montage-rendered; failures demoted to unverified, not shipped.
- [ ] Only `tier: "verified"` fonts have `.embf` files and manifest entries.
- [ ] Legacy `EMB-Bot.html` unchanged and still working (spot-check it opens).
