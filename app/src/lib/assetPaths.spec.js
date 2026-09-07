// Hand-written asset paths must be document-relative, because the bundle is
// built with `base: "./"`.
//
// vite.config.js sets that base deliberately -- it exists so the bundle works
// wherever it is served from, and Vite honours it for everything it owns
// (index.html references "./assets/…"). The five hand-written `/fonts/…`
// paths were the exception, and the contradiction was invisible until the
// built bundle was served from somewhere other than the domain root.
//
// Measured 2026-09-07 on a real `npm run build`: served at the domain root,
// 1,356 stitches and zero failed requests; served from /studio/, seven 404s
// on /fonts/manifest.json and not one stitch, with the app showing the raw
// "Font fetch failed: manifest.json (404)". At the root the two forms resolve
// identically, so nothing about today's deployment changes.
//
// A SOURCE-LEVEL check on purpose, like App.projectReplacement.spec.js: the
// bug is precisely that one call site did not follow a rule the others did,
// and a test that only exercised fontLoader would leave the four asset-URL
// builders free to drift back. It is the cheap guard, not the complete one --
// the behavioural version needs a built bundle on a static server, which is
// what the measurement above did by hand.
import { test, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const FILES = [
  "../lib/fontLoader.js",
  "../lib/credits.js",
  "../ui/FontBrowser.svelte",
  "../ui/FontSelect.svelte",
];

test("no source file builds an absolute /fonts/ URL", () => {
  const offenders = [];
  for (const rel of FILES) {
    const path = fileURLToPath(new URL(rel, import.meta.url));
    const src = readFileSync(path, "utf8");
    src.split("\n").forEach((line, i) => {
      // Skip comment lines -- fontLoader.js explains the rule by quoting the
      // very string this forbids.
      if (/^\s*(\/\/|\*|\/\*)/.test(line)) return;
      if (/["'`]\/fonts\//.test(line)) offenders.push(`${rel}:${i + 1}: ${line.trim()}`);
    });
  }
  expect(offenders).toEqual([]);
});
