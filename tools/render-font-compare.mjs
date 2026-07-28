// Renders "Kent" at hat scale (55mm) from (a) the original JSON font and
// (b) the decoded .embf, exports both DSTs, and reports stitch counts.
// PNGs via tools/render-dst.mjs. Usage:
//   node tools/render-font-compare.mjs geneva_simple aventurina montecarlo
//
// Some pictogram/symbol fonts don't have glyphs for every letter of "Kent".
// For those, pass an alternate sample string with --sample=<key>:<text>
// (repeatable), e.g.:
//   node tools/render-font-compare.mjs cats --sample=cats:cdo
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { execFileSync } from "node:child_process";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
for (const f of ["units","garments","fabrics","fill","geometry","satin","satinplay","satinfont","fontbin","dst","fonts","digitize"])
  require("../src/" + f + ".js");
const EMB = globalThis.EMB;

const rawArgs = process.argv.slice(2);
const sampleOverrides = {};
const keys = [];
for (const a of rawArgs) {
  const m = /^--sample=([^:]+):(.+)$/.exec(a);
  if (m) sampleOverrides[m[1]] = m[2];
  else keys.push(a);
}
if (!keys.length) { console.error("usage: node tools/render-font-compare.mjs <key> [key...] [--sample=<key>:<text>]"); process.exit(1); }

for (const key of keys) {
  const jsonPath = existsSync(`src/fonts/${key}.json`) ? `src/fonts/${key}.json` : `scratch_ink/_out/${key}.json`;
  const orig = JSON.parse(readFileSync(jsonPath, "utf8"));
  const deco = EMB.decodeFontBin(readFileSync(`src/fonts/bin/${key}.embf`));
  const sample = sampleOverrides[key] || "Kent";
  const opts = { garment: EMB.getGarment("hat_front"), pxPerMm: 8, densityMm: 0.4, targetWidthMm: 55 };
  const a = EMB.buildLetteringDesign(orig, sample, opts);
  const b = EMB.buildLetteringDesign(deco, sample, opts);
  writeFileSync(`scratch_ink/cmp_${key}_json.dst`, Buffer.from(EMB.encodeDST(a)));
  writeFileSync(`scratch_ink/cmp_${key}_embf.dst`, Buffer.from(EMB.encodeDST(b)));
  for (const side of ["json", "embf"])
    execFileSync("node", ["tools/render-dst.mjs", `scratch_ink/cmp_${key}_${side}.dst`, `scratch_ink/cmp_${key}_${side}.png`, "12"]);
  if (a.stitchCount === 0) {
    console.log(`${key}: EMPTY RENDER with sample "${sample}" — font has no glyphs for these characters`);
    continue;
  }
  const drift = Math.abs(a.stitchCount - b.stitchCount) / a.stitchCount;
  const sampleNote = sample !== "Kent" ? ` sample="${sample}"` : "";
  console.log(`${key}: json=${a.stitchCount} embf=${b.stitchCount} drift=${(drift * 100).toFixed(2)}%${sampleNote}`);
  if (drift > 0.01) console.log(`  WARNING: >1% stitch drift on ${key} — inspect the PNGs`);
}
