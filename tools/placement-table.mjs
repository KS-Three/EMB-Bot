// Placement box review table: one Markdown row per garment x placement pair
// that src/garments.js offers, read from the code itself so the table can
// never drift from what the Studio sizes to.
//
//   node tools/placement-table.mjs > docs/placement-boxes-2026-10-28.md
//
// Columns: garment, placement, the placement's box W x H in mm and inches,
// the area cap on the auto-fit if the row has one, the source of the box
// (MEASURED from a commercial digitizer's stitch files via PRO_PLACEMENT_MM, by
// reference; SEEDED from the inch table or an industry chart), the hoop
// suggestHoop() lands on for that box, and the auto-fit W x H after the
// largest-hoop cap (autoFitBoxMm: 200 mm field less 1 mm margin a side, so
// 198). A SEEDED row is a starting number Kent corrects against real jobs;
// a MEASURED one is the commercial digitizer's and is not up for adjustment here.
//
// Prints the full doc (header + table) so the redirect above is the whole
// regeneration step. `--rows-only` prints just the table body, which the
// test counts. No npm deps.
import "./_help.mjs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const g = require(path.join(ROOT, "src", "garments.js"));

const MM_PER_IN = 25.4;
const fmt1 = (x) => x.toFixed(1);
const inches = (mm) => fmt1(mm / MM_PER_IN);
const sizeCell = (box) => `${fmt1(box.w)} x ${fmt1(box.h)} mm (${inches(box.w)} x ${inches(box.h)} in)`;

// The measured boxes are shared BY REFERENCE from PRO_PLACEMENT_MM, so an
// identity check tells a measured row from a seeded one without reading the
// source comments. The right chest reuses the left chest's object but is a
// mirror, not a measurement: PR #1159 marks it seeded, and so does this.
const MEASURED = new Set(Object.values(g.PRO_PLACEMENT_MM));
const MIRRORED = new Set(["right_chest"]);

export function placementRows() {
  const rows = [];
  for (const garment of g.GARMENTS) {
    const ids = g.GARMENT_PLACEMENTS[garment.id] || [garment.id];
    for (const pid of ids) {
      const placement = g.getPlacement(pid);
      const placed = g.resolvePlacement(garment.id, pid);
      const box = g.placementBoxMm(placed);
      const area = g.autoFitAreaMm2(placed);
      const fit = g.autoFitBoxMm(placed);
      const hoop = g.suggestHoop(placed);
      const measured = MEASURED.has(placement.box) && !MIRRORED.has(pid);
      rows.push({
        garmentId: garment.id,
        garment: garment.label,
        placementId: pid,
        placement: placement.label,
        isDefault: pid === garment.id,
        box,
        areaMm2: Number.isFinite(area) ? area : null,
        source: measured ? "MEASURED" : MIRRORED.has(pid) ? "SEEDED (measured left chest, mirrored)" : "SEEDED",
        hoop: hoop.label,
        fit,
        capped: fit.w < box.w || fit.h < box.h,
      });
    }
  }
  return rows;
}

export function tableLines(rows) {
  const lines = [
    "| Garment | Placement | Box W x H | Area cap | Source | Hoop | Auto-fit W x H |",
    "|---|---|---|---|---|---|---|",
  ];
  for (const r of rows) {
    const name = r.isDefault ? `${r.placement} (default)` : r.placement;
    const fitCell = sizeCell(r.fit) + (r.capped ? " (hoop-capped)" : "");
    lines.push(`| ${r.garment} | ${name} \`${r.placementId}\` | ${sizeCell(r.box)} | ${
      r.areaMm2 ? `${r.areaMm2.toLocaleString("en-US")} mm2` : "none"
    } | ${r.source} | ${r.hoop} | ${fitCell} |`);
  }
  return lines;
}

export function docLines(rows) {
  const measured = rows.filter((r) => r.source === "MEASURED").length;
  const boxes = Object.keys(g.PRO_PLACEMENT_MM).length;
  const hoop = g.HOOPS[g.HOOPS.length - 1];
  return [
    "# Placement boxes: measured vs seeded (2026-10-28)",
    "",
    "Every garment x placement pair the Studio offers, with the largest box a design",
    "is auto-fitted to there. Generated from `src/garments.js` (the `PLACEMENTS` and",
    "`GARMENT_PLACEMENTS` tables PR #1159 added, 2026-10-27); the numbers here ARE",
    "the code's numbers, not a copy of them.",
    "",
    `- **MEASURED** (${boxes} boxes, on ${measured} rows): read from a commercial digitizer's stitch`,
    "  files by `digitizer/tools/garment_size_census.py` (`PRO_PLACEMENT_MM`). Not up for review here.",
    `- **SEEDED** (${rows.length - measured} rows): the inch table or an industry decorator chart,`,
    "  not a measurement. **These are the rows Kent should check against real jobs**",
    "  and correct in `PLACEMENTS` when a machine or a customer disagrees.",
    "- **Area cap**: the left chest (and its mirror) also caps the auto-fit at the",
    "  artwork's bounding-box area, so a square logo fits 76.2 mm, not 96.",
    `- **Hoop**: the smallest preset whose field takes the box either way round.`,
    `- **Auto-fit W x H**: the box after the largest-hoop cap (${hoop.label}, ${hoop.widthMm} mm less`,
    `  ${g.HOOP_FIT_MARGIN_MM} mm a side). A box bigger than the hoop is "hoop-capped": the`,
    "  design is still clamped to the full box when typed or dragged, only the AUTO size caps.",
    "",
    "Regenerate after any change to `src/garments.js`:",
    "",
    "```bash",
    "node tools/placement-table.mjs > docs/placement-boxes-2026-10-28.md",
    "```",
    "",
    "`test/placement-table.test.js` checks the row count against the code and the",
    "three measured rows against their census numbers.",
    "",
    ...tableLines(rows),
    "",
  ];
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const rows = placementRows();
  const out = process.argv.includes("--rows-only") ? tableLines(rows).slice(2) : docLines(rows);
  process.stdout.write(out.join("\n") + "\n");
}
