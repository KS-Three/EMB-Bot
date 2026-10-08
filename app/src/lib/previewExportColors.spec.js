// What the canvas paints for each sew block is what the machine file asks
// the operator to load for that block — pinned end to end on a GRADIENT.
//
// Kent, 2026-10-08, on an auto-digitized gradient icon (Hat Front, 57 mm):
// "Why is the bottom left corner display multiple colors, but is actually
// only 1 color on the stitch out?" A gradient sews through the blend tier as
// one block PER SHADE — four or five near-neighbour cones in a row, each with
// its own stop (stage6_blend.py) — so it is exactly the design where a
// preview drawing artwork colours, a writer merging "adjacent" stops, or a
// PES chart snap collapsing close oranges onto one Brother cone would make
// the Studio and the sew-out disagree. None of those happened on the repro
// (a synthetic rounded square, yellow -> orange -> magenta -> purple, white
// camera outline, digitized live at 57 mm on Hat Front: 8 blocks in the
// Realistic view, 8 blocks in the downloaded DST and PES, colours 1:1). This
// spec keeps it that way.
//
// The design below is service-shaped (adapter.py's Design: 0.1 mm ints,
// +y up, `colors` one per block named "<number> <name>") and carries the
// repro's own cones: five blend bands in sew order dark -> light, White, the
// re-loaded Iris Blue, and the edge cap.
import { test, expect, beforeAll } from "vitest";
import { createRequire } from "node:module";

beforeAll(() => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin",
                   "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp", "pes", "fonts", "digitize"])
    require("../../../src/" + f + ".js");
});

const CONES = [
  { r: 142, g: 71, b: 173, name: "2905 Iris Blue" },
  { r: 188, g: 63, b: 136, name: "2508 Hot Pink" },
  { r: 249, g: 89, b: 81, name: "1306 Devil Red" },
  { r: 255, g: 127, b: 30, name: "1106 Orange" },
  { r: 255, g: 170, b: 51, name: "1102 Pumpkin" },
  { r: 255, g: 255, b: 255, name: "0015 White" },
  { r: 142, g: 71, b: 173, name: "2905 Iris Blue" },
  { r: 235, g: 93, b: 112, name: "1753 Strawberries n' Cream" },
];

// One diagonal band per block, sewn as short fill rows, with the trim +
// colour pair adapter.py writes between blocks and its trailing `end`.
function gradientDesign() {
  const stitches = [];
  const runs = [];
  CONES.forEach((_, b) => {
    if (b > 0) {
      const last = stitches[stitches.length - 1];
      stitches.push({ x: last.x, y: last.y, type: "trim" }, { x: last.x, y: last.y, type: "color" });
    }
    const x0 = -280 + b * 60;
    stitches.push({ x: x0, y: -280, type: "jump" });
    const i0 = stitches.length;
    for (let row = 0; row < 12; row++) {
      const y = -280 + row * 40;
      const a = x0 + (row % 2 ? 50 : 0), z = x0 + (row % 2 ? 0 : 50);
      stitches.push({ x: a, y, type: "stitch" }, { x: z, y, type: "stitch" });
    }
    runs.push({ i0, i1: stitches.length - 1, kind: b === 7 ? "run" : "fill", shape: `S1-blend${b}`, role: "fill", block: b });
  });
  stitches.push({ x: 0, y: 0, type: "end" });
  return {
    stitches, runs, colors: CONES.map((c) => ({ ...c })),
    stitchCount: stitches.filter((s) => s.type === "stitch").length,
    colorCount: CONES.length, widthMM: 52, heightMM: 46, name: "gradient",
  };
}

function digitizedElement(blockColors = {}) {
  return {
    id: "e1", type: "digitized", name: "gradient.png", sourcePng: null,
    params: { target_width_mm: 57 }, warnings: [], result: gradientDesign(), blockColors,
    sizeMm: null, offsetXMm: 0, offsetYMm: 0, rotationDeg: 0,
  };
}

const rgbOf = (c) => [c.r, c.g, c.b];

// Every STITCH strand the Realistic/Stitches views paint, grouped by the sew
// block it belongs to (strands carry no block index, so walk the stream).
function strandRgbsPerBlock(design, strands) {
  const per = [new Set()];
  let si = 0;
  let prevSewn = false;
  for (const s of design.stitches) {
    if (s.type === "color") { per.push(new Set()); prevSewn = false; continue; }
    if (s.type !== "stitch") { prevSewn = false; continue; }
    if (prevSewn) per[per.length - 1].add(strands[si++].rgb.join(","));
    prevSewn = true;
  }
  return per;
}

// The PEC colour table (count-1, then one Brother chart index per block) and
// how many colour changes the PEC stitch stream holds.
function readPec(bytes) {
  const dv = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const pec = dv.getUint32(8, true);
  const n = bytes[pec + 48] + 1;
  const table = Array.from(bytes.slice(pec + 49, pec + 49 + n));
  let i = -1;
  for (let k = pec; k < bytes.length - 2; k++) {
    if (bytes[k] === 0x31 && bytes[k + 1] === 0xff && bytes[k + 2] === 0xf0) { i = k + 11; break; }
  }
  let changes = 0;
  while (i < bytes.length && bytes[i] !== 0xff) {
    if (bytes[i] === 0xfe) { changes++; i += 3; continue; }
    i += bytes[i] & 0x80 ? 2 : 1; // x
    i += bytes[i] & 0x80 ? 2 : 1; // y
  }
  return { table, changes };
}

async function generated(blockColors) {
  const { generateElement } = await import("./generate.js");
  const { EMB } = await import("./emb.js");
  const el = digitizedElement(blockColors);
  return { el, EMB, design: generateElement(el, EMB.getGarment("hat_front"), {}) };
}

test("a gradient's blend bands paint, export as DST stops, and list in the PES as the same thread, block for block", async () => {
  const { designToStrands } = await import("./strands.js");
  const { spoolCount } = await import("./digitizer.js");
  const { el, EMB, design } = await generated();

  // The Studio's block list IS the service's: no band merged, none dropped.
  expect(design.colors.map(rgbOf)).toEqual(CONES.map(rgbOf));

  // Preview: every stitch in block i is painted in block i's thread, and in
  // nothing else — not the artwork's sampled colour, not a neighbour's cone.
  const painted = strandRgbsPerBlock(design, designToStrands(design));
  expect(painted).toHaveLength(CONES.length);
  expect(painted.map((s) => [...s])).toEqual(CONES.map((c) => [rgbOf(c).join(",")]));

  // DST: a colour stop between every pair of blocks, the same stitches in each.
  const dst = EMB.decodeDST(EMB.encodeDST(design));
  const sewnPerBlock = (d) => {
    const n = [0];
    for (const s of d.stitches) {
      if (s.type === "color") n.push(0);
      else if (s.type === "stitch") n[n.length - 1]++;
    }
    return n;
  };
  expect(dst.colorCount).toBe(CONES.length);
  expect(sewnPerBlock(dst)).toEqual(sewnPerBlock(design));

  // PES: one stop per block boundary, and each block written as the Brother
  // cone nearest the colour the canvas painted it. The five bands land on five
  // DIFFERENT cones — a Brother machine shows five threads, not one.
  const pec = readPec(EMB.encodePES(design));
  expect(pec.changes).toBe(CONES.length - 1);
  expect(pec.table).toEqual(design.colors.map((c) => EMB.nearestPecIndex(c.r, c.g, c.b)));
  expect(new Set(pec.table.slice(0, 5)).size).toBe(5);

  // "N colors": spools, so the re-loaded Iris Blue counts once.
  expect(spoolCount(el.result)).toBe(7);
});

test("a thread picked for one band reaches the canvas and the PES for that band only", async () => {
  const { designToStrands } = await import("./strands.js");
  const navy = [20, 30, 90];
  const { EMB, design } = await generated({ 3: navy });

  const painted = strandRgbsPerBlock(design, designToStrands(design)).map((s) => [...s]);
  expect(painted[3]).toEqual([navy.join(",")]);
  expect(painted[2]).toEqual([rgbOf(CONES[2]).join(",")]);
  expect(painted[4]).toEqual([rgbOf(CONES[4]).join(",")]);

  const pec = readPec(EMB.encodePES(design));
  expect(pec.table[3]).toBe(EMB.nearestPecIndex(...navy));
  expect(pec.table[3]).not.toBe(EMB.nearestPecIndex(...rgbOf(CONES[3])));
});
