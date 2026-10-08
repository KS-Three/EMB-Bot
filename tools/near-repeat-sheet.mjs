// The corner of a 40 mm box whose last anchor is a slipped second click
// (MASTER_SCOPE defect 55), sewn on terry, as an SVG: thread as sewn, the
// ring as drawn in red. Run it once per build of src/digitize.js to compare.
//   node tools/near-repeat-sheet.mjs <out.svg> [label]
import "./_help.mjs";
import { writeFileSync } from "node:fs";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const DG = require("../src/digitize.js");
const FABRICS = require("../src/fabrics.js");

const box = [{ x: 0, y: 0 }, { x: 400, y: 0 }, { x: 400, y: 400 }, { x: 0, y: 400 }];
const slipped = box.concat([{ x: -0.2, y: 400.98 }]);   // the census's 1 px slip, at 10 px per mm
const build = (outer) => DG.buildQualityDesign(
  [{ rgb: [0, 0, 0], shapes: [{ outer, holes: [], tierOverride: "fill", angleOverride: 0 }] }],
  { garment: { id: "left_chest", widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: 40, darkOnTop: false, underlay: true, fabric: FABRICS.getFabric("terry_towel") });

// drawing px (y down, centred on 200,200) -> stitch units (0.1 mm, y up): 1 px is 1 unit
const W = 600, X0 = -230, Y0 = -170, S = W / 60;   // a 6 mm window on the corner at (-200, -200)
const sx = (x) => ((x - X0) * S).toFixed(1), sy = (y) => ((Y0 - y) * S).toFixed(1);
const panel = (outer, title, dx) => {
  const d = build(outer);
  let path = "", pen = false, far = -Infinity;
  for (const s of d.stitches) {
    if (s.type !== "stitch") { pen = false; continue; }
    path += (pen ? "L" : "M") + sx(s.x) + " " + sy(s.y);
    pen = true;
    far = Math.max(far, -200 - s.y);
  }
  const ring = outer.map((p) => sx(p.x - 200) + "," + sy(200 - p.y)).join(" ");
  return `<g transform="translate(${dx},40)"><rect width="${W}" height="${W}" fill="#fafafa" stroke="#ccc"/>
<svg width="${W}" height="${W}"><path d="${path}" fill="none" stroke="#1f3a93" stroke-width="1.2" stroke-opacity="0.75"/>
<polygon points="${ring}" fill="none" stroke="#d22" stroke-width="2"/></svg>
<text x="0" y="-12" font-family="sans-serif" font-size="18">${title}: fill ${(far / 10).toFixed(2)} mm below the drawn bottom edge</text></g>`;
};
const out = process.argv[2], label = process.argv[3] || "";
const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${2 * W + 40}" height="${W + 70}" style="background:#fff">
${panel(box, label + " clean corner", 0)}${panel(slipped, label + " anchor slipped 1 px", W + 40)}
<text x="0" y="${W + 64}" font-family="sans-serif" font-size="14">Bottom-left corner of a 40 mm box, terry (0.6 mm pull comp), 6 mm window. Red: ring as drawn. Blue: stitches.</text></svg>`;
writeFileSync(out, svg);
