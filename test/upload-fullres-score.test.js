// The scoring half of tools/upload-fullres-score.mjs (W5-08), on masks small
// enough to count by hand. The browser half and the service are exercised by
// running the tool; what is pinned here is that the numbers it prints mean what
// the table says they mean: an IoU of 1 is identical, an edge deviation is
// millimetres, and a shifted copy scores its shift.
const assert = require("node:assert");
const { test } = require("node:test");

const load = () => import("../tools/upload-fullres-score.mjs");

function rect(w, h, x0, y0, x1, y1) {
  const data = new Uint8Array(w * h);
  for (let y = y0; y < y1; y++) for (let x = x0; x < x1; x++) data[y * w + x] = 1;
  return { w, h, data };
}

test("IoU is 1 for identical masks, 0 for disjoint ones and a count for overlap", async () => {
  const { iou } = await load();
  const a = rect(20, 20, 2, 2, 12, 12);
  assert.strictEqual(iou(a, a), 1);
  assert.strictEqual(iou(a, rect(20, 20, 14, 14, 19, 19)), 0);
  // two 10x10 squares offset by 5 in x: 50 shared of 150 covered
  assert.ok(Math.abs(iou(a, rect(20, 20, 7, 2, 17, 12)) - 50 / 150) < 1e-12);
  // two empty masks agree
  assert.strictEqual(iou(rect(4, 4, 0, 0, 0, 0), rect(4, 4, 0, 0, 0, 0)), 1);
});

test("IoU over a band of rows counts only those rows", async () => {
  const { iou } = await load();
  const a = rect(10, 10, 0, 0, 10, 10);
  const b = rect(10, 10, 0, 0, 10, 5);      // the top half only
  assert.strictEqual(iou(a, b, [0, 5]), 1);
  assert.strictEqual(iou(a, b, [5, 10]), 0);
});

test("the distance transform is the exact Euclidean distance to the nearest set pixel", async () => {
  const { distanceTo } = await load();
  const m = rect(9, 9, 4, 4, 5, 5);          // one pixel in the middle
  const d = distanceTo(m);
  assert.strictEqual(d[4 * 9 + 4], 0);
  assert.strictEqual(d[4 * 9 + 7], 3);
  assert.ok(Math.abs(d[7 * 9 + 7] - Math.hypot(3, 3)) < 1e-9);
  assert.ok(Math.abs(d[0] - Math.hypot(4, 4)) < 1e-9);
});

test("edge deviation of a mask against a copy shifted by 3 px is 3 px along the sides it moved", async () => {
  const { edgeDeviation } = await load();
  const a = rect(40, 40, 10, 10, 30, 30);
  const same = edgeDeviation(a, a, 1);
  assert.strictEqual(same.both.mean, 0);
  assert.strictEqual(same.both.max, 0);
  // Shift right by 3: the left and right edges each lie 3 from the other's, the
  // top and bottom edges lie on the same rows (distance 0..3 along them).
  const b = rect(40, 40, 13, 10, 33, 30);
  const dev = edgeDeviation(a, b, 1);
  assert.ok(dev.both.max >= 3 && dev.both.max < 4, `max ${dev.both.max}`);
  assert.ok(dev.both.mean > 0 && dev.both.mean < 3);
  // and the unit is millimetres: 0.1 mm a pixel scales every figure by 0.1
  const mm = edgeDeviation(a, b, 0.1);
  assert.ok(Math.abs(mm.both.max - dev.both.max * 0.1) < 1e-12);
});

test("a thinner mask inside a fatter one deviates by the margin, in both directions", async () => {
  const { edgeDeviation } = await load();
  const fat = rect(40, 40, 8, 8, 32, 32);
  const thin = rect(40, 40, 11, 11, 29, 29);   // 3 px inside on every side
  const dev = edgeDeviation(fat, thin, 1);
  assert.ok(Math.abs(dev.ab.mean - 3) < 0.5 && Math.abs(dev.ba.mean - 3) < 0.5, JSON.stringify(dev));
});

test("bbox returns the half-open extent of the set pixels, null for an empty mask", async () => {
  const { bbox } = await load();
  assert.deepStrictEqual(bbox(rect(20, 20, 3, 4, 9, 7)), { x0: 3, y0: 4, x1: 9, y1: 7 });
  assert.strictEqual(bbox(rect(5, 5, 0, 0, 0, 0)), null);
});
