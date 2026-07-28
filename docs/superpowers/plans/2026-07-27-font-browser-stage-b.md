# Font Browser + Credits (Slice 10 Stage B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A searchable, filterable font browser with pre-rendered previews (killing the fetch-all-fonts ~30 MB thumbnail path), a manifest-driven credits screen, and a versioned QC harness for font tiering.

**Architecture:** Previews are PNGs rendered OFFLINE per font (`tools/build-previews.mjs` → `src/fonts/previews/<key>.png`, committed, copied to `app/public/fonts/previews/` by copy-engine) so the browser grid never fetches font binaries. `FontBrowser.svelte` is a focus-trapped dialog following the `ProjectsDrawer.svelte` pattern; `FontSelect.svelte` shrinks to a trigger button. Live your-text rendering happens ONLY for fonts already decoded in `EMB.SATIN_FONTS` — selection is the only action that fetches a binary. Credits render from the manifest (which gains `attribution` + `source` fields); the served `/fonts/bin/*.embf` files themselves are the public derived-data artifacts for ShareAlike.

**Tech Stack:** Vanilla JS engine modules (dual-mode IIFE), Node tools (zero deps, `tools/png.mjs` encoder), Svelte 5 legacy-mode components, vitest (app) + `node --test` (engine).

## Global Constraints

- No new dependencies anywhere.
- Engine tests `node --test` from repo root (baseline **203**); app tests `cd app && npm test` (baseline **188**); `cd app && npm run build` clean — all green before every commit.
- Svelte components use legacy `$:` reactivity, `createEventDispatcher`, in-flow or ProjectsDrawer-style dialogs — **never** a popover inside `.panel-body` (clips), **never** `outline: none`.
- Engine-file lists live in THREE synced places: `app/scripts/copy-engine.mjs`, `app/src/lib/emb.js` ENGINE_KEYS, `app/index.html` script tags. (Not expected to change this slice — no new engine modules.)
- `tools/build-embf.mjs` requires `scratch_ink/` (present this session) and refuses to build without it.
- Only `tier:"verified"` fonts ship. License policy for new fonts: OFL-1.1 / CC-BY-4.0 / CC-BY-SA-4.0 / CC0.
- Do NOT touch legacy `EMB-Bot.html` / `src/fonts/satin-fonts.js`.
- Do NOT `git push`.

---

### Task 1: Versioned QC harness (`tools/qc-font.mjs`)

The tier classifier currently lives only in gitignored `scratch_ink/` — un-versioned, untested, and its per-FILE satin count already let a 0-stitch font (`ondulamarif_XL`) through. This task versions the checks with the per-GLYPH fix.

**Files:**
- Create: `tools/qc-font.mjs`
- Test: `test/qc-font.test.js`

**Interfaces:**
- Produces: `qcFont(font)` → `{ pass: boolean, findings: string[] }` where `font` is a decoded font object (`{name, license, unitsPerEm, sizeMm, advDefault, glyphs: {ch: {adv, cols, runs}}}`). Exported CommonJS from the tool file via the same dual-use pattern other tools avoid — this tool is plain ESM with a named export `qcFont` plus a CLI entry. Test imports it with dynamic `import()`.
- CLI: `node tools/qc-font.mjs <font.json> [...]` prints `<key>: PASS` or `<key>: FAIL — <finding>; <finding>` per file, exit 1 if any FAIL.

- [ ] **Step 1: Write the failing test**

Create `test/qc-font.test.js`:

```js
const assert = require("node:assert");
const { test } = require("node:test");

function goodFont() {
  const col = { railA: [[0, 0], [0, 10]], railB: [[2, 0], [2, 10]], rungs: [] };
  const glyphs = {};
  for (const ch of "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789")
    glyphs[ch] = { adv: 10, cols: [col], runs: [] };
  return { name: "Good", license: "OFL", unitsPerEm: 100, sizeMm: 20, advDefault: 10, glyphs };
}

test("qcFont passes a well-formed font", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const r = qcFont(goodFont());
  assert.strictEqual(r.pass, true);
  assert.deepStrictEqual(r.findings, []);
});

test("flags letter glyphs with zero satin columns (the ondulamarif_XL case)", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  for (const ch of "ABCDEFGHIJ") f.glyphs[ch] = { adv: 10, cols: [], runs: [[[0,0],[1,1]]] };
  const r = qcFont(f);
  assert.strictEqual(r.pass, false);
  assert.ok(r.findings.some((s) => /satin/i.test(s)), r.findings.join("; "));
});

test("flags missing or degenerate advances", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  f.glyphs["A"].adv = 0;
  f.glyphs["B"].adv = null;
  const r = qcFont(f);
  assert.strictEqual(r.pass, false);
  assert.ok(r.findings.some((s) => /advance/i.test(s)));
});

test("flags NaN coordinates", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  f.glyphs["A"].cols[0] = { railA: [[NaN, 0], [0, 10]], railB: [[2, 0], [2, 10]], rungs: [] };
  const r = qcFont(f);
  assert.strictEqual(r.pass, false);
  assert.ok(r.findings.some((s) => /NaN|finite/i.test(s)));
});

test("flags missing basic Latin coverage as a warning-level finding but still passes", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  for (const ch of "abcdefghijklmnopqrstuvwxyz") delete f.glyphs[ch];
  const r = qcFont(f);
  assert.strictEqual(r.pass, true); // caps-only fonts are legitimate
  assert.ok(r.findings.some((s) => /coverage/i.test(s)));
});

test("flags missing sizeMm/unitsPerEm", async () => {
  const { qcFont } = await import("../tools/qc-font.mjs");
  const f = goodFont();
  delete f.sizeMm;
  const r = qcFont(f);
  assert.strictEqual(r.pass, false);
  assert.ok(r.findings.some((s) => /sizeMm/i.test(s)));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test test/qc-font.test.js`
Expected: FAIL — cannot find `../tools/qc-font.mjs`.

- [ ] **Step 3: Implement**

Create `tools/qc-font.mjs`:

```js
// Versioned font QC — the tier gate, in the repo, with tests.
// Encodes every failure mode this project has hit:
//   - medium_font: null advances collapsed glyphs
//   - ondulamarif_XL: letter glyphs runs-only (zero satin columns) -> 0
//     stitches; the old classifier counted satin per FILE, this counts per
//     LETTER GLYPH, which is what buildLetteringDesign actually stitches
//   - dropped fonts: broken metrics / degenerate geometry
// Usage: node tools/qc-font.mjs <font.json> [...more]
import { readFileSync } from "node:fs";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
const LOWER = "abcdefghijklmnopqrstuvwxyz";
const DIGITS = "0123456789";

function finiteRing(r) {
  return Array.isArray(r) && r.every((p) => Array.isArray(p) && p.length >= 2 &&
    Number.isFinite(p[0]) && Number.isFinite(p[1]));
}

export function qcFont(font) {
  const findings = [];
  let hardFail = false;
  const fail = (msg) => { findings.push(msg); hardFail = true; };
  const warn = (msg) => { findings.push(msg); };

  if (!font || typeof font !== "object" || !font.glyphs) return { pass: false, findings: ["not a font object"] };
  if (!(font.sizeMm > 0)) fail("missing/invalid sizeMm");
  if (!(font.unitsPerEm > 0)) fail("missing/invalid unitsPerEm");

  const present = (chars) => [...chars].filter((c) => font.glyphs[c]);
  const upper = present(LETTERS), lower = present(LOWER), digits = present(DIGITS);
  if (upper.length === 0) fail("no uppercase letter glyphs at all");
  if (lower.length === 0) warn("coverage: no lowercase glyphs (caps-only font)");
  if (digits.length === 0) warn("coverage: no digit glyphs");

  // Per-LETTER-GLYPH satin check: a letter with zero satin columns stitches
  // as nothing through buildLetteringDesign.
  const letterGlyphs = [...upper, ...lower];
  const satinless = letterGlyphs.filter((c) => !(font.glyphs[c].cols || []).length);
  if (letterGlyphs.length && satinless.length === letterGlyphs.length)
    fail("every letter glyph has zero satin columns (runs-only font -> 0 stitches)");
  else if (satinless.length > letterGlyphs.length * 0.25)
    warn(`satin: ${satinless.length}/${letterGlyphs.length} letter glyphs have no satin columns`);

  // Advances: zero/null/negative on any present letter glyph is a hard fail.
  const badAdv = letterGlyphs.filter((c) => !(font.glyphs[c].adv > 0));
  if (badAdv.length) fail(`advance: ${badAdv.length} letter glyphs with missing/zero advance (e.g. "${badAdv[0]}")`);

  // Geometry: every rail/rung/run point must be finite.
  outer:
  for (const [ch, g] of Object.entries(font.glyphs)) {
    for (const col of g.cols || []) {
      for (const ring of [col.railA, col.railB, ...(col.rungs || [])]) {
        if (ring && !finiteRing(ring)) { fail(`geometry: non-finite point in glyph "${ch}"`); break outer; }
      }
    }
    for (const run of g.runs || []) {
      const pts = run.pts || run;
      if (pts && !finiteRing(pts)) { fail(`geometry: non-finite point in glyph "${ch}" run`); break outer; }
    }
  }

  return { pass: !hardFail, findings };
}

// CLI
if (process.argv[1] && process.argv[1].replace(/\\/g, "/").endsWith("tools/qc-font.mjs")) {
  const files = process.argv.slice(2);
  if (!files.length) { console.error("usage: node tools/qc-font.mjs <font.json> [...]"); process.exit(1); }
  let anyFail = false;
  for (const f of files) {
    const font = JSON.parse(readFileSync(f, "utf8"));
    const key = f.replace(/\\/g, "/").split("/").pop().replace(/\.json$/, "");
    const { pass, findings } = qcFont(font);
    if (!pass) anyFail = true;
    console.log(`${key}: ${pass ? "PASS" : "FAIL"}${findings.length ? " — " + findings.join("; ") : ""}`);
  }
  process.exit(anyFail ? 1 : 0);
}
```

- [ ] **Step 4: Run tests**

Run: `node --test test/qc-font.test.js` → 6 pass.
Run: `node --test` → 209 pass (203 + 6).

- [ ] **Step 5: Prove it against the real library**

```bash
node tools/qc-font.mjs src/fonts/*.json 2>&1 | grep -v ": PASS"
node tools/qc-font.mjs scratch_ink/_out/ondulamarif_XL.json
```
Expected: shipped 21 all PASS (warnings allowed, e.g. caps-only coverage); `ondulamarif_XL` prints FAIL with the satin finding. If a shipped font hard-FAILs, STOP and report — that's a real discovery, not a test bug.

- [ ] **Step 6: Commit**

```bash
git add tools/qc-font.mjs test/qc-font.test.js
git commit -m "feat: versioned font QC harness with per-glyph satin check"
```

---

### Task 2: Manifest enrichment — attribution, source, full category coverage

**Files:**
- Modify: `tools/build-embf.mjs` (manifest entry emission, ~line 98)
- Modify: `tools/font-categories.json` (full 69-key coverage + new "Small" group)
- Modify: `app/src/ui/FontSelect.svelte:10` (GROUP_ORDER gains "Small")
- Modify: `test/embf-guard.test.js` (manifest entry assertions)
- Regenerate: `src/fonts/manifest.json` (via the tool; `.embf` files must NOT change)

**Interfaces:**
- Produces: every manifest font entry gains `attribution` (string, first non-empty line of the upstream license text, ≤200 chars) and `source` (string, the font's `source` field or `"Ink/Stitch embroidery-fonts"`). Groups become exactly `["Sans","Serif","Script","Display","Small","More"]`, and **at most 5 fonts** may remain in "More".

- [ ] **Step 1: Extend the guard test (failing first)**

In `test/embf-guard.test.js`, inside the "manifest lists every shipped font" test's `for (const f of man.fonts)` loop, extend the per-entry assertion:

```js
    assert.ok(f.name && f.licenseId && f.sizeMm > 0 && f.glyphCount > 0, "bad entry " + f.key);
    assert.ok(typeof f.attribution === "string" && f.attribution.length > 0 && f.attribution.length <= 200,
      "missing/oversized attribution: " + f.key);
    assert.ok(typeof f.source === "string" && f.source.length > 0, "missing source: " + f.key);
```

And add a new test after it:

```js
test("category coverage: known groups only, More is a small remainder", () => {
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const KNOWN = new Set(["Sans", "Serif", "Script", "Display", "Small", "More"]);
  for (const f of man.fonts) assert.ok(KNOWN.has(f.group), `unknown group ${f.group} on ${f.key}`);
  const more = man.fonts.filter((f) => f.group === "More");
  assert.ok(more.length <= 5, "More is a dumping ground: " + more.map((f) => f.key).join(", "));
});
```

Run: `node --test test/embf-guard.test.js` → FAILS (no attribution field yet; 17 fonts in More).

- [ ] **Step 2: Emit attribution + source in build-embf.mjs**

In `tools/build-embf.mjs`, where the manifest entry is pushed (~line 98), derive the two fields from the loaded font JSON (`font.license`, `font.source`):

```js
  // First non-empty line of the upstream license text is the human
  // attribution ("This font X has been adapted for Ink/Stitch by Y...").
  const attribution = String(font.license || "").split(/\r?\n/)
    .map((l) => l.trim()).filter(Boolean)[0]?.slice(0, 200)
    || (font.name + " — see license inside the font binary");
  manifest.push({
    key: s.key,
    name: font.name || s.key,
    tier: "verified",
    group: GROUPS[s.key] || "More",
    licenseId: id,
    sizeMm: font.sizeMm,
    glyphCount: Object.keys(font.glyphs || {}).length,
    bytes: bin.length,
    attribution,
    source: font.source || "Ink/Stitch embroidery-fonts",
  });
```

(Adapt property names to the existing push — keep every existing field, add the two new ones.)

- [ ] **Step 3: Author full category coverage**

Rewrite `tools/font-categories.json` so all 69 shipped keys are present. Rules:
- every `*_small` / `*_tiny` / `small_font` / `glacial_tiny` / `caffeine_tiny` / `pacificlo_tiny` key → `"Small"`;
- purge keys that don't ship (`montecarlo`, `precious`, `mimosa_large` if unshipped — check against the manifest);
- classify the rest by eyeballing preview names (serif faces → Serif, scripts/cursive → Script, bold display/pictogram packs like `cats`, `cogs_KOR`, `pixel10`, `neon`, `manga_impact` → Display, plain text faces → Sans);
- "More" only for genuinely unclassifiable leftovers, max 5.

Get the authoritative key list: `node -e "console.log(require('./src/fonts/manifest.json').fonts.map(f=>f.key).join('\n'))"`.

- [ ] **Step 4: Rebuild and verify the binaries did not change**

```bash
node tools/build-embf.mjs
git status --short src/fonts/
```
Expected: ONLY `src/fonts/manifest.json` modified. Any `.embf` diff means the codec was touched — STOP, that's wrong.

- [ ] **Step 5: GROUP_ORDER**

`app/src/ui/FontSelect.svelte:10`:

```js
  const GROUP_ORDER = ["Sans", "Serif", "Script", "Display", "Small", "More"];
```

- [ ] **Step 6: Run all suites**

`node --test` → 210 (209 + the new category-coverage test). `cd app && npm test` → 188. `cd app && node scripts/copy-engine.mjs` → clean.

- [ ] **Step 7: Commit**

```bash
git add tools/build-embf.mjs tools/font-categories.json app/src/ui/FontSelect.svelte test/embf-guard.test.js src/fonts/manifest.json
git commit -m "feat: manifest attribution/source fields + full category coverage with Small group"
```

---

### Task 3: Pre-rendered previews (`tools/build-previews.mjs`)

**Files:**
- Create: `tools/build-previews.mjs`
- Create: `src/fonts/previews/<key>.png` × 69 (generated, committed)
- Modify: `app/scripts/copy-engine.mjs` (copy previews dir)
- Test: `test/previews.test.js`

**Interfaces:**
- Produces: one PNG per manifest font at `src/fonts/previews/<key>.png`, ~360×56, white background, dark stitches, rendering the font's **name** in the font itself (glyph-aware fallback below). Served at `/fonts/previews/<key>.png`.

- [ ] **Step 1: Failing test**

Create `test/previews.test.js`:

```js
const assert = require("node:assert");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");

const FONT_DIR = path.join(__dirname, "..", "src", "fonts");
const PREV_DIR = path.join(FONT_DIR, "previews");

test("every manifest font has a committed preview PNG", () => {
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  for (const f of man.fonts) {
    const p = path.join(PREV_DIR, f.key + ".png");
    assert.ok(fs.existsSync(p), "missing preview: " + f.key);
    const buf = fs.readFileSync(p);
    assert.ok(buf.length > 200, "suspiciously tiny preview (blank?): " + f.key);
    assert.strictEqual(buf.readUInt32BE(0), 0x89504e47, "not a PNG: " + f.key);
  }
});

test("no orphan previews", () => {
  const man = JSON.parse(fs.readFileSync(path.join(FONT_DIR, "manifest.json"), "utf8"));
  const keys = new Set(man.fonts.map((f) => f.key));
  for (const f of fs.readdirSync(PREV_DIR)) {
    if (!f.endsWith(".png")) continue;
    assert.ok(keys.has(f.replace(/\.png$/, "")), "orphan preview: " + f);
  }
});
```

Run: `node --test test/previews.test.js` → FAIL (no previews dir).

- [ ] **Step 2: Implement the generator**

Create `tools/build-previews.mjs`:

```js
// Renders one preview PNG per manifest font: the font's display name set in
// the font itself (or a glyph-aware fallback sample), dark thread on white.
// These are the ONLY images the Stage B font browser grid loads — no font
// binary is fetched for browsing, which is the fix for the Stage A
// open-dropdown-fetches-30MB problem.
// Usage: node tools/build-previews.mjs
import { readFileSync, writeFileSync, mkdirSync, readdirSync, unlinkSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","fontbin","dst","fonts","digitize"])
  require("../src/" + f + ".js");
const EMB = globalThis.EMB;

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const FONT_DIR = join(root, "src", "fonts");
const PREV_DIR = join(FONT_DIR, "previews");
mkdirSync(PREV_DIR, { recursive: true });

// Sample: the font's own name where its glyphs allow, else the longest
// renderable prefix of the alphabet it actually has.
function sampleFor(font) {
  const has = (ch) => ch === " " || !!(font.glyphs && font.glyphs[ch]);
  const name = String(font.name || "Sample");
  if ([...name].every(has)) return name;
  const caseFixed = name.replace(/[a-z]/g, (c) => c.toUpperCase());
  if ([...caseFixed].every(has)) return caseFixed;
  const own = Object.keys(font.glyphs || {}).filter((k) => /^[A-Za-z0-9]$/.test(k)).slice(0, 6).join("");
  return own || "?";
}

const man = JSON.parse(readFileSync(join(FONT_DIR, "manifest.json"), "utf8"));
const wanted = new Set(man.fonts.map((f) => f.key));

// Clean orphans so a demoted font's preview can't linger (same lesson as the
// orphan-.embf guard).
for (const f of readdirSync(PREV_DIR)) {
  if (f.endsWith(".png") && !wanted.has(f.replace(/\.png$/, ""))) {
    unlinkSync(join(PREV_DIR, f));
    console.log("removed orphan", f);
  }
}

let made = 0;
for (const entry of man.fonts) {
  const font = EMB.decodeFontBin(readFileSync(join(FONT_DIR, "bin", entry.key + ".embf")));
  const text = sampleFor(font);
  const design = EMB.buildLetteringDesign(font, text, {
    garment: EMB.getGarment("left_chest"), pxPerMm: 8, densityMm: 0.5,
    underlay: false, targetWidthMm: 80,
  });
  if (!design.stitchCount) { console.error("EMPTY preview for " + entry.key + " — investigate"); process.exitCode = 1; continue; }
  const tmp = join(PREV_DIR, "_tmp.dst");
  writeFileSync(tmp, Buffer.from(EMB.encodeDST(design)));
  execFileSync("node", [join(root, "tools", "render-dst.mjs"), tmp, join(PREV_DIR, entry.key + ".png"), "4"]);
  made++;
}
if (existsSync(join(PREV_DIR, "_tmp.dst"))) unlinkSync(join(PREV_DIR, "_tmp.dst"));
console.log("previews:", made, "of", man.fonts.length);
```

- [ ] **Step 3: Generate + eyeball**

```bash
node tools/build-previews.mjs
ls src/fonts/previews | wc -l   # expect 69
```
Read 3-4 PNGs (a sans, a script, a pictogram like cats) to confirm they render legible samples. Pictogram packs will show symbols, not the name — correct behavior.

- [ ] **Step 4: copy-engine copies previews**

In `app/scripts/copy-engine.mjs`, alongside the existing manifest+bin copy block, add a loop copying `src/fonts/previews/*.png` → `app/public/fonts/previews/` (mkdir recursive first, same convention). Also delete stale files in the dest previews dir not present in source (the final review flagged copy-engine's no-clean behavior; do it right for the new dir):

```js
const prevSrc = join(srcDir, "fonts", "previews");
const prevOut = join(outDir, "..", "fonts", "previews");
mkdirSync(prevOut, { recursive: true });
const srcPngs = new Set(readdirSync(prevSrc).filter((f) => f.endsWith(".png")));
for (const f of readdirSync(prevOut)) if (f.endsWith(".png") && !srcPngs.has(f)) unlinkSync(join(prevOut, f));
for (const f of srcPngs) copyFileSync(join(prevSrc, f), join(prevOut, f));
console.log("copied", srcPngs.size, "font previews");
```

(Adjust `outDir` path math to the file's existing variables — read it first; add `unlinkSync`/`readdirSync` to its imports.)

- [ ] **Step 5: Suites + copy check**

`node --test` → 212 (210 + 2). `cd app && node scripts/copy-engine.mjs` → logs 69 previews. `cd app && npm test` → 188.

- [ ] **Step 6: Commit**

```bash
git add tools/build-previews.mjs test/previews.test.js src/fonts/previews app/scripts/copy-engine.mjs
git commit -m "feat: pre-rendered font preview PNGs + copy-engine sync with stale cleanup"
```

---

### Task 4: FontBrowser dialog + FontSelect becomes a trigger

**Files:**
- Create: `app/src/ui/FontBrowser.svelte`
- Rewrite: `app/src/ui/FontSelect.svelte`
- Test: `app/src/lib/fontFilter.js` + `app/src/lib/fontFilter.spec.js` (pure filter logic, unit-testable)

**Interfaces:**
- Consumes: manifest entries (`{key,name,group,attribution,...}` via `loadManifest()`), `/fonts/previews/<key>.png`, `ensureFont(key)`.
- Produces: `FontBrowser.svelte` props `{ selected, currentText }`, events `pick` (detail: font key) + `close`. `filterFonts(fonts, query, group)` from `app/src/lib/fontFilter.js`.
- **The fetch-all path dies here:** `ensureAll()` and the thumbnail queue are deleted. The ONLY `ensureFont` calls left in browsing UI are (a) the selected font's live preview, (b) a font the user picks.

- [ ] **Step 1: Failing filter tests**

Create `app/src/lib/fontFilter.spec.js`:

```js
import { describe, it, expect } from "vitest";
import { filterFonts } from "./fontFilter.js";

const FONTS = [
  { key: "geneva_simple", name: "Geneva Simple", group: "Sans" },
  { key: "aventurina", name: "Aventurina", group: "Script" },
  { key: "cats", name: "Cats", group: "Display" },
  { key: "small_font", name: "Small Font", group: "Small" },
];

describe("filterFonts", () => {
  it("no query, group All returns everything", () => {
    expect(filterFonts(FONTS, "", "All")).toHaveLength(4);
  });
  it("group filter narrows", () => {
    expect(filterFonts(FONTS, "", "Script").map((f) => f.key)).toEqual(["aventurina"]);
  });
  it("query matches name case-insensitively", () => {
    expect(filterFonts(FONTS, "gen", "All").map((f) => f.key)).toEqual(["geneva_simple"]);
  });
  it("query matches key too", () => {
    expect(filterFonts(FONTS, "small_f", "All")).toHaveLength(1);
  });
  it("query and group compose", () => {
    expect(filterFonts(FONTS, "a", "Display").map((f) => f.key)).toEqual(["cats"]);
  });
  it("no match returns empty, never throws", () => {
    expect(filterFonts(FONTS, "zzz", "All")).toEqual([]);
    expect(filterFonts([], "x", "Sans")).toEqual([]);
  });
});
```

Run: `cd app && npx vitest run src/lib/fontFilter.spec.js` → FAIL.

- [ ] **Step 2: Implement filter**

Create `app/src/lib/fontFilter.js`:

```js
// Pure font-list filtering for the browser dialog. Kept out of the component
// so it's unit-testable without DOM.
export function filterFonts(fonts, query, group) {
  const q = (query || "").trim().toLowerCase();
  return (fonts || []).filter((f) => {
    if (group && group !== "All" && f.group !== group) return false;
    if (!q) return true;
    return f.name.toLowerCase().includes(q) || f.key.toLowerCase().includes(q);
  });
}
```

Run: 6 pass.

- [ ] **Step 3: Build FontBrowser.svelte**

Follow `ProjectsDrawer.svelte`'s dialog mechanics EXACTLY (read it first): fixed backdrop + panel, `role="dialog" aria-modal="true"`, `tabindex="-1"` focus-on-mount, Tab trap via `focusableEls()`, Escape → `close`, focus restore is the opener's job. Content:

```svelte
<script>
  import { createEventDispatcher, onMount } from "svelte";
  import { EMB } from "../lib/emb.js";
  import { renderRealistic } from "../lib/preview.js";
  import { loadManifest, ensureFont } from "../lib/fontLoader.js";
  import { filterFonts } from "../lib/fontFilter.js";

  export let selected = null;
  export let currentText = "";
  const d = createEventDispatcher();

  const GROUPS = ["All", "Sans", "Serif", "Script", "Display", "Small", "More"];
  let fonts = [];
  let query = "";
  let group = "All";
  let manifestFailed = false;
  loadManifest().then((m) => { fonts = m.fonts; }).catch(() => { manifestFailed = true; });

  $: shown = filterFonts(fonts, query, group);

  // Live "your text" tile rendering — ONLY for fonts already decoded. The
  // grid must never trigger binary fetches (that was Stage A's 30MB
  // dropdown problem); static preview PNGs carry undecoded fonts.
  let liveThumbs = {};
  $: renderLive(shown, currentText);
  function renderLive(list, text) {
    const t = (text || "").trim().slice(0, 12);
    if (!t) { liveThumbs = {}; return; }
    const next = {};
    for (const f of list) {
      const font = (EMB.SATIN_FONTS || {})[f.key];
      if (!font) continue;
      try {
        const c = document.createElement("canvas");
        c.width = 360; c.height = 56;
        const design = EMB.buildLetteringDesign(font, t, {
          garment: EMB.getGarment("left_chest"), pxPerMm: 8, densityMm: 0.5, underlay: false,
        });
        renderRealistic(c, design, { colorOverride: [45, 45, 50], fabric: "#ffffff", pad: 8 });
        next[f.key] = c.toDataURL();
      } catch (e) { /* fall back to the static PNG */ }
    }
    liveThumbs = next;
  }

  async function pick(key) {
    try { await ensureFont(key); } catch (e) { /* generate paths surface errors */ }
    d("pick", key);
    d("close");
  }
  // ...dialog boilerplate from ProjectsDrawer: onMount focus, trapTab, Escape
</script>
```

Template: search input (label "Find a font"), group chips (buttons, `class:active`), grid of tiles — each tile a `<button>` with `<img src={liveThumbs[f.key] || "/fonts/previews/" + f.key + ".png"} alt="" loading="lazy" />` plus `<span>{f.name}</span>` and a size-band subtitle, `class:sel={f.key === selected}`. Empty state: "No fonts match "{query}"." Manifest failure state: "Couldn't load the font list — check your connection and reopen." Styles from `theme.css` tokens; grid `repeat(auto-fill, minmax(180px, 1fr))`; NO `outline: none`.

**Size-band guidance (spec §6, do not skip):** each font's recommended band is `[sizeMm × 0.75, sizeMm × 2.0]` from its manifest `sizeMm` — the size its author digitized it for. Two surfacings:

1. Tile subtitle: `bestAt(f)` → e.g. "best at 15–40 mm" (round to whole mm). Add to `app/src/lib/fontFilter.js` (it's the pure-logic module this component already imports):

```js
// Recommended size band from the authored size. Multipliers are a starting
// point per the spec — validate against real stitch-outs before trusting.
export function sizeBand(sizeMm) {
  if (!(sizeMm > 0)) return null;
  return { min: Math.round(sizeMm * 0.75), max: Math.round(sizeMm * 2.0) };
}
```

With spec tests appended to `fontFilter.spec.js`:

```js
import { sizeBand } from "./fontFilter.js";
describe("sizeBand", () => {
  it("derives 0.75x-2x from authored size", () => {
    expect(sizeBand(20)).toEqual({ min: 15, max: 40 });
  });
  it("null on missing size", () => {
    expect(sizeBand(undefined)).toBeNull();
    expect(sizeBand(0)).toBeNull();
  });
});
```

(App test totals shift +2: Task 4 lands at 196, Task 5 at 198, Definition of done app count is **198**.)

2. Non-blocking note: `FontBrowser` takes `export let currentHeightMm = null;` (the selected element's current rendered height, passed down from TextStep via FontSelect — App already emits `dims`; pass what's available, `null` is fine). When `currentHeightMm` falls outside the picked font's band, the tile shows a small warning line "sized outside this font's best range" — informational only, never blocks the pick.

- [ ] **Step 4: Shrink FontSelect**

Rewrite `app/src/ui/FontSelect.svelte`: keep the trigger button (selected font's static preview `<img src={"/fonts/previews/" + selected + ".png"}>` + name), clicking sets `browserOpen = true` and renders `<FontBrowser {selected} {currentText} on:pick on:close={...} />`. Add `export let currentText = "";` and have `TextStep.svelte` pass the element's text (read TextStep to find the FontSelect usage; pass `currentText={el.text}` — adapt to actual prop names there). DELETE: `ensureAll`, `thumbsPending`, `ensureThumb`, the dropdown `<ul>`, the `svelte:window` click-away. Selected-font live preview in the trigger may still `ensureFont(selected)` — that's one font, fine. Restore focus to the trigger on close (ProjectsDrawer pattern: capture `document.activeElement` at open).

- [ ] **Step 5: Suites + build**

`cd app && npm test` → 196 (188 + 8). `cd app && npm run build` → clean. `node --test` → 212.

- [ ] **Step 6: Grep the fetch-storm is gone**

`grep -n "ensureAll\|ensureThumb" app/src` → no hits.

- [ ] **Step 7: Commit**

```bash
git add app/src/ui/FontBrowser.svelte app/src/ui/FontSelect.svelte app/src/ui/TextStep.svelte app/src/lib/fontFilter.js app/src/lib/fontFilter.spec.js
git commit -m "feat: font browser dialog with search/filters/static previews; retire fetch-all dropdown"
```

---

### Task 5: Credits screen

**Files:**
- Create: `app/src/ui/FontCredits.svelte`
- Modify: `app/src/App.svelte` (open/close wiring + topbar entry)
- Modify: `app/src/ui/DownloadStep.svelte` (secondary entry link)
- Test: `app/src/lib/credits.spec.js`

**Interfaces:**
- Consumes: `loadManifest()` entries incl. `attribution`, `licenseId`, `source`.
- Produces: `creditLines(manifestFonts)` from `app/src/lib/credits.js` → `[{name, licenseId, attribution, binHref}]` sorted by name; `FontCredits.svelte` dialog (ProjectsDrawer mechanics) listing them, each with a link to its served binary (`/fonts/bin/<key>.embf`) — the public derived-data artifact CC-BY-SA asks for — plus a note line: "Fonts adapted from the Ink/Stitch open embroidery font collection. Each font's full license text ships inside its binary."

- [ ] **Step 1: Failing test**

Create `app/src/lib/credits.spec.js`:

```js
import { describe, it, expect } from "vitest";
import { creditLines } from "./credits.js";

const FONTS = [
  { key: "b_font", name: "Bravo", licenseId: "CC-BY-SA-4.0", attribution: "Adapted by X", source: "Ink/Stitch" },
  { key: "a_font", name: "Alpha", licenseId: "OFL-1.1", attribution: "Adapted by Y", source: "Ink/Stitch" },
];

describe("creditLines", () => {
  it("sorts by display name and carries license fields through", () => {
    const lines = creditLines(FONTS);
    expect(lines.map((l) => l.name)).toEqual(["Alpha", "Bravo"]);
    expect(lines[0]).toMatchObject({ licenseId: "OFL-1.1", attribution: "Adapted by Y", binHref: "/fonts/bin/a_font.embf" });
  });
  it("tolerates missing attribution without throwing", () => {
    const lines = creditLines([{ key: "x", name: "X", licenseId: "CC0" }]);
    expect(lines[0].attribution).toBe("");
  });
});
```

- [ ] **Step 2: Implement**

Create `app/src/lib/credits.js`:

```js
// Credits data derived from the font manifest — never hand-maintained.
export function creditLines(manifestFonts) {
  return (manifestFonts || [])
    .map((f) => ({
      name: f.name || f.key,
      licenseId: f.licenseId || "",
      attribution: f.attribution || "",
      binHref: "/fonts/bin/" + f.key + ".embf",
    }))
    .sort((a, b) => a.name.localeCompare(b.name));
}
```

Run: 2 pass.

- [ ] **Step 3: Dialog + entry points**

`FontCredits.svelte`: ProjectsDrawer dialog mechanics; heading "Font licenses & credits"; the collection note line; then one row per `creditLines(fonts)` entry — name (strong), licenseId (badge-style span), attribution (small text), and an `<a href={binHref} download>` labeled "font data". Wire in `App.svelte`: a small "Font credits" text button in the topbar area near "My designs" toggling the dialog (focus restore to the button). In `DownloadStep.svelte`: a one-line footer link "Fonts: open-source — see credits" dispatching the same open event upward.

- [ ] **Step 4: Suites + build**

`cd app && npm test` → 198. `cd app && npm run build` → clean.

- [ ] **Step 5: Commit**

```bash
git add app/src/ui/FontCredits.svelte app/src/lib/credits.js app/src/lib/credits.spec.js app/src/App.svelte app/src/ui/DownloadStep.svelte
git commit -m "feat: font credits dialog generated from manifest"
```

---

### Task 6: Browser acceptance + docs

**Files:**
- Modify: `README.md`, `COOKBOOK.md`

**Steps:**

- [ ] **Step 1: Live acceptance (controller runs this in the Browser pane)**

Restart the dev server (predev must copy previews). Verify, with the network panel:
1. Boot: manifest + at most ONE font binary fetched (the current element's).
2. Open the font browser: preview PNGs load (`/fonts/previews/*.png`), **zero** `.embf` fetches.
3. Search "cat" narrows; group chips filter; Small group populated.
4. Pick a font → exactly one `.embf` fetch → design regenerates.
5. Typed text appears as live tiles only for already-loaded fonts; static PNGs elsewhere.
6. Credits dialog lists 69 fonts with license ids; a font-data link downloads.
7. Zero console errors throughout.

- [ ] **Step 2: Docs**

README: replace the dropdown description with the browser (search, filters, credits). COOKBOOK: Stage B section — previews are committed artifacts (`node tools/build-previews.mjs` after any font/library change, orphan-cleaning), qc-font.mjs is the versioned tier gate (scratch_ink classify retired), the grid-never-fetches-binaries rule, credits generated from manifest. Update test baselines (engine 212, app 196).

- [ ] **Step 3: Final suites, commit**

```bash
node --test && cd app && npm test && npm run build
git add README.md COOKBOOK.md
git commit -m "docs: Stage B font browser, previews pipeline, QC harness"
```

---

## Definition of done

- [ ] Engine 212/212, app 198/198, build clean.
- [ ] Opening the font browser fetches ZERO font binaries (network-verified).
- [ ] Search + group filters work; ≤5 fonts in "More"; Small group exists.
- [ ] Credits dialog lists every shipped font with license id + attribution, generated from the manifest.
- [ ] `tools/qc-font.mjs` FAILs `ondulamarif_XL` and PASSes all 21 original shipped fonts.
- [ ] Previews: 69 committed PNGs, orphan-guarded both in the repo (test) and in copy-engine.
- [ ] No `.embf` file changed anywhere in this slice.
