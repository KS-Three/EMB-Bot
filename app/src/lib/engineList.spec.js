// The engine's file list exists in THREE places and nothing checked them.
//
// `app/scripts/copy-engine.mjs` decides what gets copied into
// `app/public/engine/`, `index.html` decides what the browser actually loads
// and in what order, and `lib/emb.js`'s `ENGINE_KEYS` is what app code reads
// the list from. `emb.js`'s own comment has said "MUST stay in sync with
// scripts/copy-engine.mjs's ENGINE_FILES and the <script src=...> order in
// index.html" since it was written — and "must" was the whole enforcement.
//
// Measured 2026-09-20, adding `sewtime.js`: updating one list and not the
// others does NOT fail loudly. A file copied but never script-tagged simply
// is not on `EMB`, and every caller that guards for its absence — which is
// the house style, because a missing engine symbol means a stale
// `public/engine/` copy — then degrades quietly. `estimate.js` drops its
// thread row without `THREAD_LENGTH_FACTOR` for exactly that reason, and the
// review screen would have dropped the run-time row the same way, on a build
// where the only thing wrong was a forgotten line of HTML.
//
// This is the fourth guard of its kind, and the same argument as the other
// three (`test_code_wires.py` for warning codes, `test_fabric_wire.py` for
// the fabric table, `test_machine_wire.py` for the physical constants): the
// duplication is deliberate and stays, so the tripwire is what makes it safe.
//
// NOT covered here, deliberately: the private module list in
// `estimate.spec.js`'s `beforeAll`. That is a test fixture loading the subset
// a spec needs, not a shipping list, and forcing it to match would make every
// spec load the whole engine.
import { test, expect } from "vitest";
import { readFileSync } from "node:fs";

const here = (rel) => new URL(rel, import.meta.url);

// `emb.js` is READ, not imported: its module body throws "Engine not loaded"
// unless `globalThis.EMB` has already been populated by requiring the engine
// scripts, and booting the whole engine to read one array would make this
// guard depend on the very thing it is guarding.
function engineKeys() {
  const src = readFileSync(here("./emb.js"), "utf-8");
  const m = src.match(/export const ENGINE_KEYS = \[(.*?)\n\];/s);
  expect(m, "no `export const ENGINE_KEYS = [...]` in emb.js").toBeTruthy();
  // Comments are stripped FIRST. The block inside this array explains why
  // `"fonts.js"` is excluded — and names it in quotes, so a naive scan reads
  // the explanation as a list entry and silently adds back the one file the
  // comment exists to keep out.
  return [...m[1].replace(/\/\/[^\n]*/g, "").matchAll(/"([^"]+\.js)"/g)].map((x) => x[1]);
}

function copyEngineFiles() {
  const src = readFileSync(here("../../scripts/copy-engine.mjs"), "utf-8");
  const m = src.match(/export const ENGINE_FILES = \[(.*?)\];/s);
  expect(m, "no `export const ENGINE_FILES = [...]` in copy-engine.mjs").toBeTruthy();
  return [...m[1].matchAll(/"([^"]+\.js)"/g)].map((x) => x[1]);
}

function indexHtmlEngineTags() {
  const src = readFileSync(here("../../index.html"), "utf-8");
  return [...src.matchAll(/<script src="\/engine\/([^"]+\.js)"><\/script>/g)].map((x) => x[1]);
}

test("the parsers are not vacuous", () => {
  // A regex that finds nothing agrees with everything. Pin that all three
  // lists are substantial and that a known member is in each, the same way
  // `test_fabric_wire.py` pins its own parser first.
  expect(engineKeys().length).toBeGreaterThan(10);
  expect(copyEngineFiles().length).toBeGreaterThan(10);
  expect(indexHtmlEngineTags().length).toBeGreaterThan(10);
  for (const list of [engineKeys(), copyEngineFiles(), indexHtmlEngineTags()]) {
    expect(list).toContain("units.js");
    expect(list).toContain("pdfsheet.js");
  }
});

test("copy-engine, index.html and ENGINE_KEYS name the same files in the same order", () => {
  // ORDER matters, not just membership: these are plain scripts sharing one
  // `globalThis.EMB`, loaded in dependency order, so a file that loads before
  // something it reads is a different failure from one that never loads.
  const copied = copyEngineFiles();
  const tagged = indexHtmlEngineTags();

  // `fonts.js` is deliberately absent from ENGINE_KEYS (see its comment
  // there) — it is a Node-only module the Studio never loads. If it is ever
  // absent from the other two as well this simply passes; the assertion is
  // about the lists agreeing, not about that one decision.
  const skip = new Set(copied.filter((f) => !engineKeys().includes(f)));
  expect([...skip], "an engine file is copied and tagged but unknown to app code").toEqual(
    tagged.filter((f) => !engineKeys().includes(f))
  );

  expect(copied.filter((f) => !skip.has(f))).toEqual(engineKeys());
  expect(tagged.filter((f) => !skip.has(f))).toEqual(engineKeys());
});
