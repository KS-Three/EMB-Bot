// The placement review table (tools/placement-table.mjs, rendered to
// docs/placement-boxes-2026-10-28.md) is generated from src/garments.js, and
// this pins the two things a reader relies on: one row per garment x
// placement pair the code offers, and the three measured boxes carrying the
// census numbers (hat front 113.5 x 64, left chest 96 x 76.5 with the 5,800
// mm2 area cap, beanie 94.5 x 56).
const assert = require("node:assert");
const { test } = require("node:test");
const { execFileSync } = require("node:child_process");
const path = require("node:path");
const g = require("../src/garments.js");

const ROOT = path.resolve(__dirname, "..");
const SCRIPT = path.join(ROOT, "tools", "placement-table.mjs");

function pairsInCode() {
  const pairs = [];
  for (const garment of g.GARMENTS) {
    for (const pid of g.GARMENT_PLACEMENTS[garment.id] || [garment.id]) pairs.push([garment.id, pid]);
  }
  return pairs;
}

function rowsFromScript() {
  const out = execFileSync(process.execPath, [SCRIPT, "--rows-only"], { encoding: "utf8" });
  return out.trim().split("\n").filter((l) => l.startsWith("|"));
}

test("one table row per garment x placement pair the code exposes", () => {
  const rows = rowsFromScript();
  const pairs = pairsInCode();
  assert.strictEqual(rows.length, pairs.length);
  // every pair is named, in code order
  rows.forEach((row, i) => {
    const [garmentId, pid] = pairs[i];
    assert.ok(row.includes(`\`${pid}\``), `row ${i} should carry ${pid}: ${row}`);
    assert.ok(row.includes(`| ${g.getGarment(garmentId).label} |`), `row ${i} should name ${garmentId}: ${row}`);
  });
  // and every row is marked one way or the other
  for (const row of rows) assert.match(row, /\| (MEASURED|SEEDED[^|]*) \|/);
});

test("the three measured rows carry the census numbers", () => {
  const rows = rowsFromScript();
  const row = (garmentLabel, pid) => {
    const hits = rows.filter((r) => r.includes(`| ${garmentLabel} |`) && r.includes(`\`${pid}\``));
    assert.strictEqual(hits.length, 1, `${garmentLabel} / ${pid}`);
    return hits[0];
  };
  const hat = row("Hat Front", "hat_front");
  assert.ok(hat.includes("| 113.5 x 64.0 mm (4.5 x 2.5 in) |"), hat);
  assert.ok(hat.includes("| none | MEASURED |"), hat);

  const lc = row("Left Chest", "left_chest");
  assert.ok(lc.includes("| 96.0 x 76.5 mm (3.8 x 3.0 in) |"), lc);
  assert.ok(lc.includes("| 5,800 mm2 | MEASURED |"), lc);

  const beanie = row("Beanie", "beanie");
  assert.ok(beanie.includes("| 94.5 x 56.0 mm (3.7 x 2.2 in) |"), beanie);
  assert.ok(beanie.includes("| none | MEASURED |"), beanie);

  // the right chest reuses the measured box but is a mirror, so it is seeded
  const rc = row("Left Chest", "right_chest");
  assert.match(rc, /\| SEEDED \(measured left chest, mirrored\) \|/);
  // and exactly as many MEASURED rows as the code has measured boxes appearing as placements
  const measuredRows = rows.filter((r) => r.includes("| MEASURED |")).length;
  const expected = pairsInCode().filter(([, pid]) => pid in g.PRO_PLACEMENT_MM).length;
  assert.strictEqual(measuredRows, expected);
});

test("the committed doc matches the generator", () => {
  const { readFileSync } = require("node:fs");
  const doc = readFileSync(path.join(ROOT, "docs", "placement-boxes-2026-10-28.md"), "utf8");
  const fresh = execFileSync(process.execPath, [SCRIPT], { encoding: "utf8" });
  assert.strictEqual(doc.replace(/\r\n/g, "\n"), fresh, "regenerate: node tools/placement-table.mjs > docs/placement-boxes-2026-10-28.md");
});
