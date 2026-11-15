// Which box does each size path clamp to? One row per garment x placement.
//
//   node tools/placement-box-paths.mjs > docs/placement-box-paths-2026-11-14.md
//
// The engine has two kinds of "box" for the same placement, and they agree
// everywhere except the default placement of the three garments the pro
// measured (hat_front, left_chest, beanie):
//
//   PLACEMENTS box  `placementBoxMm(placed)`: the pro's measured box or a
//                   seeded one. What auto-fit (`fitScale`), the Studio's typed
//                   width and drag clamps, and the outline-lettering width read.
//   inch pair       `garment.widthIn x heightIn` of the garment AS PLACED. For a
//                   non-default placement `resolvePlacement` rewrites it from
//                   the PLACEMENTS box (same number); for a default placement
//                   it is the old round-inch table (hat_front 5 x 2.25 in).
//                   What `buildImportedDesign` and the engine's typed-width
//                   clamps (`digitize.js`) read.
//
// Every number printed here is MEASURED by running the engine on a probe (a
// design thousands of mm wide, then thousands tall), not copied from a table,
// so a path that changes its box changes this output. The overflow section
// re-runs the 2026-11-14 starter x placement table (docs/hat-autofit-note-
// 2026-11-14/overflow-table.md) over the 12 committed starter DSTs under both
// boxes. No npm deps; `--rows-only` prints the path table only.
import "./_help.mjs";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const g = require(path.join(ROOT, "src", "garments.js"));
const dstimport = require(path.join(ROOT, "src", "dstimport.js"));
const DG = require(path.join(ROOT, "src", "digitize.js"));

const MM_PER_IN = 25.4;
const AUTO_RANGE = [0.75, 1.5]; // app/src/lib/generate.js STITCH_FILE_AUTO_RANGE
const r1 = (x) => Math.round(x * 10) / 10;
const f1 = (x) => r1(x).toFixed(1);
const cell = (b) => `${f1(b.w)} x ${f1(b.h)}`;

// ---- probes: the box a path really clamps to ---------------------------------

// A design this big is clamped on one axis only: the other axis stays tiny.
function decodedProbe(wMm, hMm) {
  const u = 10; // DST_UNITS_PER_MM
  return {
    stitches: [
      { x: -wMm * u / 2, y: -hMm * u / 2, type: "stitch" },
      { x: wMm * u / 2, y: hMm * u / 2, type: "stitch" },
    ],
    widthMM: wMm, heightMM: hMm, colorCount: 1, stitchCount: 2, jumpCount: 0, trimCount: 0,
  };
}

// buildImportedDesign (stitch file, digitized result, outline lettering):
// native size, no typed width, no autoScaleRange: the box clamp alone.
export function importClampBox(placed) {
  const wide = dstimport.buildImportedDesign(decodedProbe(5000, 1), { garment: placed });
  const tall = dstimport.buildImportedDesign(decodedProbe(1, 5000), { garment: placed });
  return { w: wide.widthMM, h: tall.heightMM };
}

// The engine's own typed-width clamp (digitize.js, buildQualityDesign and
// buildLetteringDesign share the expression): a typed width of 5000 mm.
export function engineTypedBox(placed) {
  const rect = (w, h) => [{ x: 0, y: 0 }, { x: w, y: 0 }, { x: w, y: h }, { x: 0, y: h }];
  const build = (w, h) => DG.buildQualityDesign(
    [{ rgb: [0, 0, 0], shapes: [{ outer: rect(w, h), holes: [], tierOverride: "fill" }] }],
    { garment: placed, pxPerMm: 10, targetWidthMm: 5000, underlay: false, fillColumns: true, darkOnTop: false });
  const wide = build(3000, 150), tall = build(150, 3000);
  // stitches round to 0.1 mm: snap back to the nearest 0.1
  return { w: r1(wide.widthMM), h: r1(tall.heightMM) };
}

// fitScale (digitized upload default width, lettering auto-fit): hoop-capped.
export function autoFitProbe(placed) {
  const wide = g.fitScale(5000, 1, placed);
  const tall = g.fitScale(1, 5000, placed);
  return { w: wide.targetWmm, h: tall.targetHmm, area: g.autoFitAreaMm2(placed) };
}

// A square logo through the digitized upload path: auto-fit to the box, then
// the service result re-enters buildImportedDesign at native size (generate.js
// generateElement, `digitized`).
export function squareUpload(placed) {
  const fit = g.fitScale(100, 100, placed);
  const side = fit.targetWmm; // square: W = H
  const built = dstimport.buildImportedDesign(decodedProbe(side, side), { garment: placed });
  return { fitted: side, drawn: built.widthMM };
}

export function placedOf(garmentId, pid) {
  return g.resolvePlacement(garmentId, pid === garmentId ? null : pid);
}

export function pathRows() {
  const rows = [];
  for (const garment of g.GARMENTS) {
    const ids = g.GARMENT_PLACEMENTS[garment.id] || [garment.id];
    for (const pid of ids) {
      const placed = placedOf(garment.id, pid);
      const placement = g.getPlacement(pid);
      const entry = placement ? placement.box : null;
      const measured = !!entry && Object.values(g.PRO_PLACEMENT_MM).includes(entry) && pid !== "right_chest";
      const imp = importClampBox(placed);
      const typed = engineTypedBox(placed);
      const auto = autoFitProbe(placed);
      const app = g.placementBoxMm(placed);
      const sq = squareUpload(placed);
      // The PLACEMENTS entry for a default placement of a garment with no row
      // of its own is still the garment's own id row (every garment id is a
      // placement id), so `entry` is always present.
      rows.push({
        garmentId: garment.id, placementId: pid, isDefault: pid === garment.id,
        entry: { w: entry.w, h: entry.h }, source: measured ? "pro" : pid === "right_chest" ? "seeded (pro mirrored)" : "seeded",
        importBox: imp, engineTyped: typed, autoFit: auto, appBox: app,
        square: sq,
        disagree: Math.abs(imp.w - entry.w) > 0.2 || Math.abs(imp.h - entry.h) > 0.2,
        dW: imp.w - entry.w, dH: imp.h - entry.h,
      });
    }
  }
  return rows;
}

// ---- overflow table under both boxes -----------------------------------------

export function loadStarters() {
  const dir = path.join(ROOT, "app", "public", "starter");
  const manifest = JSON.parse(fs.readFileSync(path.join(dir, "manifest.json"), "utf8"));
  return manifest.designs.map((d) => {
    const bytes = new Uint8Array(fs.readFileSync(path.join(dir, d.dst)));
    return { id: d.id, title: d.title, decoded: dstimport.decodeDSTStandard(bytes) };
  });
}

// variant "inch"       = before Kent's 2026-11-14 hat-front ruling: every
//                        garment clamps to its inch pair;
//         "current"    = the code as it is: the hat front on its PLACEMENTS box,
//                        left chest and beanie still on the inch pair;
//         "placements" = the same call handed the PLACEMENTS box everywhere
//                        (what unifying left chest and beanie too would do).
export function overflowRows(starters, variant) {
  const out = [];
  for (const garment of g.GARMENTS) {
    for (const pid of g.GARMENT_PLACEMENTS[garment.id] || [garment.id]) {
      const placed = placedOf(garment.id, pid);
      let box, asPlaced;
      if (variant === "inch") {
        box = { w: placed.widthIn * MM_PER_IN, h: placed.heightIn * MM_PER_IN };
        asPlaced = { ...placed, clampBox: undefined };
      } else if (variant === "current") {
        box = g.clampBoxMm(placed);
        asPlaced = placed;
      } else {
        box = g.placementBoxMm(placed);
        asPlaced = { ...placed, clampBox: undefined, widthIn: box.w / MM_PER_IN, heightIn: box.h / MM_PER_IN };
      }
      for (const s of starters) {
        const built = dstimport.buildImportedDesign(s.decoded, { garment: asPlaced, autoScaleRange: AUTO_RANGE });
        const ow = Math.max(0, built.widthMM - box.w), oh = Math.max(0, built.heightMM - box.h);
        out.push({
          placement: pid, garment: garment.id, starter: s.title, box,
          native: { w: s.decoded.widthMM, h: s.decoded.heightMM },
          scale: built._debug.scale, w: built.widthMM, h: built.heightMM,
          overflows: ow > 0.05 || oh > 0.05, ow, oh,
        });
      }
    }
  }
  return out;
}

export function overflowDiff(starters, from = "current", to = "placements") {
  const a = overflowRows(starters, from);
  const b = overflowRows(starters, to);
  const key = (r) => `${r.garment}|${r.placement}|${r.starter}`; // garment too: left_chest is a placement of three garments
  const bm = new Map(b.map((r) => [key(r), r]));
  const changed = [];
  for (const r of a) {
    const n = bm.get(key(r));
    if (r.overflows === n.overflows && Math.abs(r.ow - n.ow) < 0.05 && Math.abs(r.oh - n.oh) < 0.05) continue;
    changed.push({ before: r, after: n });
  }
  // fits under both boxes but is drawn at a different scale (left chest: the
  // 96 x 76.5 box is smaller than the 4 in square, so a tall starter shrinks)
  const rescaled = [];
  for (const r of a) {
    const n = bm.get(key(r));
    if (r.overflows || n.overflows) continue;
    if (Math.abs(r.scale - n.scale) > 0.005) rescaled.push({ before: r, after: n });
  }
  return { before: a, after: b, changed, rescaled };
}

// ---- document -----------------------------------------------------------------

function pathTable(rows) {
  const lines = [
    "| Garment | Placement | PLACEMENTS entry (source) | Import clamp `buildImportedDesign` | Engine typed clamp | Auto-fit (hoop-capped) | App typed/drag clamp | Paths disagree? |",
    "|---|---|---|---|---|---|---|---|",
  ];
  for (const r of rows) {
    const name = r.isDefault ? `${r.placementId} (default)` : r.placementId;
    const dis = r.disagree
      ? `**YES**: import ${r.dW >= 0 ? "+" : ""}${f1(r.dW)} w / ${r.dH >= 0 ? "+" : ""}${f1(r.dH)} h mm`
      : "no";
    const area = Number.isFinite(r.autoFit.area) ? `, area ${r.autoFit.area}` : "";
    lines.push(`| ${r.garmentId} | ${name} | ${cell(r.entry)} (${r.source}) | ${cell(r.importBox)} | ${cell(r.engineTyped)} | ${cell({ w: r.autoFit.w, h: r.autoFit.h })}${area} | ${cell(r.appBox)} | ${dis} |`);
  }
  return lines;
}

const cellOf = (r) => `${Math.round(r.scale * 100)}%, ${r.overflows ? `${f1(r.ow)} / ${f1(r.oh)}` : "fits"}`;
const worse = (c) => (c.after.ow + c.after.oh) > (c.before.ow + c.before.oh) + 0.05;
export const verdictOf = (c) => !c.before.overflows && c.after.overflows ? "NEW overflow"
  : c.before.overflows && !c.after.overflows ? "now fits"
    : worse(c) ? "worse" : "better";
const nOver = (list) => list.filter((r) => r.overflows).length;

// One before/after section of the starter overflow table.
function overflowSection(title, fromLabel, toLabel, diff, filter) {
  const keep = (c) => !filter || filter(c.before.placement);
  const changed = diff.changed.filter(keep);
  const rescaled = diff.rescaled.filter(keep);
  const lines = [];
  lines.push(`### ${title}`, "");
  lines.push(`Overflowing starter x placement combinations: **${nOver(diff.before)}** ${fromLabel}, **${nOver(diff.after)}** ${toLabel}. ${diff.changed.length} of ${diff.before.length} combinations change overflow.`, "");
  lines.push(`| Placement | Box (${fromLabel}) | Box (${toLabel}) | Starter | ${fromLabel} (scale, overflow w/h) | ${toLabel} (scale, overflow w/h) | Verdict |`);
  lines.push("|---|---|---|---|---|---|---|");
  for (const c of changed) {
    lines.push(`| ${c.before.placement} | ${cell(c.before.box)} | ${cell(c.after.box)} | ${c.before.starter} | ${cellOf(c.before)} | ${cellOf(c.after)} | ${verdictOf(c)} |`);
  }
  lines.push("");
  const tally = { "now fits": 0, better: 0, worse: 0, "NEW overflow": 0 };
  for (const c of changed) tally[verdictOf(c)]++;
  lines.push(`Tally: ${Object.entries(tally).map(([k, v]) => `${k} ${v}`).join(", ")}.`, "");
  lines.push(`Fits under both boxes but drawn at a different scale: ${rescaled.length} combinations.`, "");
  if (rescaled.length) {
    lines.push(`| Placement | Starter | Scale ${fromLabel} | Scale ${toLabel} |`, "|---|---|---|---|");
    for (const c of rescaled) {
      lines.push(`| ${c.before.placement} | ${c.before.starter} | ${Math.round(c.before.scale * 100)}% | ${Math.round(c.after.scale * 100)}% |`);
    }
    lines.push("");
  }
  return lines;
}

// `rulingDiff`: before Kent's hat-front ruling vs the code now (hat front rows
// only; the other placements do not move). `restDiff`: the code now vs the
// PLACEMENTS box everywhere (what is still split: left chest, beanie).
export function docLines(rows, rulingDiff, restDiff) {
  const dis = rows.filter((r) => r.disagree);
  const lines = [];
  lines.push(`**Paths still disagree on ${dis.length} of ${rows.length} placements**: ${dis.map((r) => r.placementId).join(", ")} (Kent's ruling 2026-11-14: hat front only; left chest and beanie stay split on purpose).`, "");
  lines.push("## Path table (measured by probe, mm, W x H)", "");
  lines.push(...pathTable(rows), "");
  lines.push("## Square logo through the digitized upload path", "");
  lines.push("Auto-fit sizes a square logo into the PLACEMENTS box; the service result then re-enters `buildImportedDesign` at native size and meets the clamp box.", "");
  lines.push("| Placement | Fitted side (auto-fit) | Drawn side after import clamp |", "|---|---|---|");
  for (const r of rows.filter((x) => x.isDefault && ["hat_front", "left_chest", "beanie"].includes(x.placementId))) {
    lines.push(`| ${r.placementId} | ${f1(r.square.fitted)} | ${f1(r.square.drawn)}${r.square.drawn < r.square.fitted - 0.05 ? " (shrunk)" : ""} |`);
  }
  lines.push("");
  lines.push("## Starter overflow at the 75% stop", "");
  lines.push(...overflowSection("Kent's hat-front ruling: before vs after", "before", "after", rulingDiff, (p) => p === "hat_front"));
  lines.push(...overflowSection("Still open: the code now vs the PLACEMENTS box everywhere", "now", "all PLACEMENTS", restDiff));
  return lines;
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const rows = pathRows();
  if (process.argv.includes("--rows-only")) {
    process.stdout.write(pathTable(rows).join("\n") + "\n");
  } else {
    const starters = loadStarters();
    const out = docLines(rows, overflowDiff(starters, "inch", "current"), overflowDiff(starters, "current", "placements"));
    process.stdout.write(out.join("\n") + "\n");
  }
}
