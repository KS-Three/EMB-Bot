#!/usr/bin/env node
// build-threads.mjs — converts the GIMP-palette (.gpl) thread charts in
// tools/palettes/ into the Studio's brand catalog, split across two
// generated modules:
//
//   app/src/lib/threadBrandsIndex.js  { id, label, count } per brand — tiny,
//                                     statically imported (brand dropdowns +
//                                     preference validation need only this).
//   app/src/lib/threadBrandsData.js   full thread lists — ~20k entries, so it
//                                     is ONLY ever loaded via dynamic import()
//                                     (threads.js loadPalette), keeping it out
//                                     of the main bundle as its own chunk
//                                     (same reasoning as the lazy jspdf and
//                                     .embf font binaries).
//
// Provenance: the .gpl files are manufacturer color charts redistributed by
// the Ink/Stitch project (github.com/inkstitch/inkstitch, palettes/,
// snapshot e7108fd). Thread color numbers and their RGB approximations are
// factual data (a catalog of facts, not creative expression); each brand
// name remains a trademark of its manufacturer and is used only to identify
// the corresponding thread line. "InkStitch RAL.gpl" is deliberately not
// shipped — RAL is a paint standard, not embroidery thread.
//
// Usage: node tools/build-threads.mjs
// Re-run whenever a palette file in tools/palettes/ is added or updated.
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const PALETTE_DIR = join(root, "tools", "palettes");
const OUT_INDEX = join(root, "app", "src", "lib", "threadBrandsIndex.js");
const OUT_DATA = join(root, "app", "src", "lib", "threadBrandsData.js");

// POLICY (Kent, 2026-07-29 blueprint grill): no thread charts from companies
// that sell or make embroidery software/machines — we don't carry a
// competitor's brand inside the product. Enforced here (not just by file
// deletion) so a wholesale re-copy from upstream can't silently reintroduce
// them; matches are skipped with a loud log line.
const POLICY_EXCLUDED = [
  "InkStitch Brother Country.gpl",      // Brother: machines + PE-Design
  "InkStitch Brother Embroidery.gpl",   // Brother: machines + PE-Design
  "InkStitch Janome.gpl",               // Janome: machines + software
  "InkStitch Viking Palette.gpl",       // Husqvarna Viking: machines + software
  "InkStitch Floriani Polyester.gpl",   // RNK: Floriani embroidery software
  "InkStitch Hemingworth.gpl",          // DIME: embroidery software
];

// The four charts that shipped before the full sweep keep their original
// ids/labels so the stored app-wide preference (embstudio:threadPalette)
// keeps resolving for existing users.
const LEGACY = {
  "InkStitch Isacord Polyester.gpl": { id: "isacord", label: "Isacord Polyester 40" },
  "InkStitch Madeira Polyneon.gpl": { id: "polyneon", label: "Madeira Polyneon 40" },
  "InkStitch Madeira Rayon.gpl": { id: "madeira-rayon", label: "Madeira Rayon 40" },
  "InkStitch Robison-Anton Polyester.gpl": { id: "robison-anton", label: "Robison-Anton Polyester 40" },
};

// A .gpl body line is "R G B <name words> <catalog number>", whitespace
// (spaces and/or tabs) separated, after a 3-4 line header. The catalog number
// is the last field; it always contains a digit in these charts, which is how
// we tell it apart from a name-only line (some palettes ship without codes --
// then the whole remainder is the name and code is "").
function parseGpl(text) {
  const entries = [];
  for (const raw of text.split(/\r\n|\r|\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith("#") || /^GIMP Palette$/i.test(line) || /^(Name|Columns):/i.test(line)) continue;
    const m = line.match(/^(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})\s+(.+)$/);
    if (!m) continue;
    const rgb = [Number(m[1]), Number(m[2]), Number(m[3])];
    if (rgb.some((v) => v > 255)) continue;
    const rest = m[4].trim();
    const lastSpace = rest.search(/\s\S+$/);
    const lastTok = lastSpace >= 0 ? rest.slice(lastSpace).trim() : "";
    let name, code;
    if (lastTok && /\d/.test(lastTok)) {
      name = rest.slice(0, lastSpace).trim();
      code = lastTok;
    } else {
      name = rest;
      code = "";
    }
    if (!name) { name = code; code = ""; }
    entries.push({ name, code, rgb });
  }
  return entries;
}

function labelFor(file) {
  return file.replace(/^InkStitch\s+/, "").replace(/\.gpl$/, "");
}

function idFor(label) {
  return label.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
}

const files = readdirSync(PALETTE_DIR).filter((f) => f.endsWith(".gpl")).sort();
const seenIds = new Set();
const brands = [];
for (const file of files) {
  if (POLICY_EXCLUDED.includes(file)) {
    console.log(`EXCLUDED (software-company policy): ${file}`);
    continue;
  }
  const meta = LEGACY[file] || (() => { const label = labelFor(file); return { id: idFor(label), label }; })();
  if (seenIds.has(meta.id)) throw new Error(`duplicate brand id "${meta.id}" from ${file}`);
  seenIds.add(meta.id);
  const threads = parseGpl(readFileSync(join(PALETTE_DIR, file), "utf8"));
  // Smallest legitimate chart shipped is 15 colors (Simthread Glow In The
  // Dark); anything under 10 means the file format changed on us -- fail the
  // build loudly rather than silently shipping a gutted chart.
  if (threads.length < 10) {
    throw new Error(`${file}: parsed only ${threads.length} entries -- format change?`);
  }
  brands.push({ id: meta.id, label: meta.label, threads });
}
brands.sort((a, b) => a.label.localeCompare(b.label));

const provenance = `// Source data: Ink/Stitch palette files (github.com/inkstitch/inkstitch,
// palettes/) — factual manufacturer color-chart data. Brand names are
// trademarks of their respective manufacturers, used only for identification.
`;

const index = brands.map(({ id, label, threads }) => ({ id, label, count: threads.length }));
writeFileSync(
  OUT_INDEX,
  `// threadBrandsIndex.js — GENERATED by tools/build-threads.mjs; do not edit by hand.
// One { id, label, count } entry per manufacturer thread chart. This is the
// ONLY statically-imported brand module (dropdowns and preference validation
// need nothing more); the actual thread lists live in threadBrandsData.js,
// loaded lazily via threads.js loadPalette().
${provenance}export const THREAD_BRAND_INDEX = ${JSON.stringify(index, null, 1)};
`
);

writeFileSync(
  OUT_DATA,
  `// threadBrandsData.js — GENERATED by tools/build-threads.mjs; do not edit by hand.
// Full manufacturer thread charts (name + catalog number + approximate RGB).
// ~${brands.reduce((n, b) => n + b.threads.length, 0)} entries: do NOT import this statically — threads.js loadPalette()
// dynamic-imports it so it stays out of the main bundle as its own chunk.
${provenance}export const THREAD_BRANDS = ${JSON.stringify(brands)};
`
);

let total = 0;
for (const b of brands) {
  total += b.threads.length;
  console.log(`${b.label}: ${b.threads.length} colors`);
}
console.log(`\n${brands.length} brands, ${total} colors total`);
console.log(`Wrote ${OUT_INDEX}`);
console.log(`Wrote ${OUT_DATA}`);
