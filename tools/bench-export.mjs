// Times DST / PES / EXP export of a ~50k-stitch design and prints a SHA-256 of
// each output, so a speed change can be shown byte-identical:
//   node tools/bench-export.mjs [stitches=50000] [runs=7]
import "./_help.mjs";
import { createRequire } from "node:module";
import { createHash } from "node:crypto";
const require = createRequire(import.meta.url);
const n = +process.argv[2] || 50000, runs = +process.argv[3] || 7;

// Deterministic design: serpentine rows, some jumps, trims, colour changes,
// and the odd move longer than one record so the splitter is exercised too.
function makeDesign(count) {
  let s = 12345;
  const rnd = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
  const stitches = [], colors = [];
  for (let c = 0; c < 6; c++) colors.push({ r: c * 40, g: 255 - c * 40, b: c * 20, name: "c" + c });
  let x = 0, y = 0;
  for (let i = 0; i < count; i++) {
    const r = rnd();
    let type = "stitch";
    if (i && i % (count / 6 | 0) === 0) type = "color";
    else if (r < 0.004) type = "trim";
    else if (r < 0.012) type = "jump";
    const far = r > 0.995 ? 400 : 40;
    x += Math.round((rnd() - 0.5) * far); y += Math.round((rnd() - 0.5) * far);
    x = Math.max(-3000, Math.min(3000, x)); y = Math.max(-3000, Math.min(3000, y));
    stitches.push({ x, y, type });
  }
  stitches.push({ x: 0, y: 0, type: "end" });
  return { stitches, colors, label: "BENCH" };
}
const design = makeDesign(n);
const fmt = {
  DST: require("../src/dst.js").encodeDST,
  PES: require("../src/pes.js").encodePES,
  EXP: require("../src/exp.js").encodeEXP,
};
for (const [name, fn] of Object.entries(fmt)) {
  const out = fn(design); // warm-up
  const ts = [];
  for (let i = 0; i < runs; i++) { const t = performance.now(); fn(design); ts.push(performance.now() - t); }
  ts.sort((a, b) => a - b);
  const hash = createHash("sha256").update(out).digest("hex").slice(0, 16);
  console.log(`${name}  median ${ts[runs >> 1].toFixed(1)} ms  min ${ts[0].toFixed(1)} ms  bytes ${out.length}  sha256 ${hash}`);
}
