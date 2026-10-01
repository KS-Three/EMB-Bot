import { test, expect } from "vitest";
import { readFileSync } from "node:fs";
import { rgbToLab, ciede2000, rankThreads, samplePatch, matchWord } from "./colorMatch.js";
import { loadPalette, nearestInList } from "./threads.js";

// Pinned against the Python lane: every number in the fixture came out of
// skimage's deltaE_ciede2000 through digitizer_core.threads, so the browser
// and the digitizer name the same cone for the same colour.
const FIXTURE = JSON.parse(
  readFileSync(new URL("./ciede2000.fixture.json", import.meta.url), "utf8")
);

test("the fixture is the size it was generated at (a truncated file would pass vacuously)", () => {
  expect(FIXTURE.pairs).toHaveLength(48);
  expect(FIXTURE.ranks).toHaveLength(48);
});

test("rgbToLab matches skimage's rgb2lab", () => {
  for (const p of FIXTURE.pairs) {
    const lab = rgbToLab(p.a);
    for (let k = 0; k < 3; k++) expect(lab[k]).toBeCloseTo(p.labA[k], 8);
  }
});

test("ciede2000 matches skimage on every pinned pair", () => {
  for (const p of FIXTURE.pairs) {
    expect(ciede2000(rgbToLab(p.a), rgbToLab(p.b))).toBeCloseTo(p.de, 8);
  }
});

test("ciede2000 is zero on identical colours and symmetric", () => {
  const a = rgbToLab([20, 40, 90]);
  const b = rgbToLab([200, 30, 130]);
  expect(ciede2000(a, a)).toBe(0);
  expect(ciede2000(a, b)).toBeCloseTo(ciede2000(b, a), 10);
});

test("rankThreads returns the same top five, in the same order, as the Python chart", async () => {
  for (const r of FIXTURE.ranks) {
    const chart = await loadPalette(r.brand);
    expect(chart.id).toBe(r.brand);
    const got = rankThreads(chart.threads, r.rgb, 5);
    expect(got.map((t) => t.code)).toEqual(r.top.map((t) => t.code));
    got.forEach((t, i) => expect(t.deltaE).toBeCloseTo(r.top[i].de, 6));
  }
  // First test to import the ~1.1 MB brand chunk; on a loaded machine that
  // import alone has passed the 5 s default.
}, 30000);

test("rankThreads carries name, code, rgb and the list index, nearest first", async () => {
  const chart = await loadPalette("isacord");
  const got = rankThreads(chart.threads, [20, 40, 90], 3);
  expect(got).toHaveLength(3);
  expect(got[0].deltaE).toBeLessThanOrEqual(got[1].deltaE);
  expect(got[1].deltaE).toBeLessThanOrEqual(got[2].deltaE);
  expect(chart.threads[got[0].index].code).toBe(got[0].code);
  expect(got[0].rgb).toEqual(chart.threads[got[0].index].rgb);
});

test("rankThreads on an empty list or a missing colour is an empty list, not a throw", () => {
  expect(rankThreads([], [1, 2, 3], 5)).toEqual([]);
  expect(rankThreads([{ name: "x", rgb: [0, 0, 0] }], null, 5)).toEqual([]);
});

// The reason this module exists beside nearestInList: threads.py's own
// header records plain distance sending a dark navy to a grey. If the two
// metrics ever agree on every probe here, the comparison has gone vacuous.
test("the perceptual ranking disagrees with Euclidean RGB somewhere on a real chart", async () => {
  const chart = await loadPalette("isacord");
  const differs = FIXTURE.ranks
    .filter((r) => r.brand === "isacord")
    .some((r) => nearestInList(chart.threads, r.rgb).code !== rankThreads(chart.threads, r.rgb, 1)[0].code);
  expect(differs).toBe(true);
});

// --- samplePatch ----------------------------------------------------------

function image(w, h, fn) {
  const data = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) data.set(fn(x, y), (y * w + x) * 4);
  }
  return { data, width: w, height: h };
}

test("samplePatch on a flat colour returns that colour", () => {
  const img = image(20, 20, () => [200, 16, 46, 255]);
  expect(samplePatch(img, 10, 10, 4)).toEqual({ rgb: [200, 16, 46], count: 81 });
});

test("samplePatch averages the patch, so one stray pixel does not decide the answer", () => {
  const img = image(21, 21, (x, y) => (x === 10 && y === 10 ? [255, 255, 255, 255] : [20, 40, 90, 255]));
  const { rgb } = samplePatch(img, 10, 10, 4);
  // The worst case there is: pure white on a dark navy. It is a MEAN, so the
  // pixel still pulls (20 -> 38 on red), but the answer stays a navy.
  for (let k = 0; k < 3; k++) expect(Math.abs(rgb[k] - [20, 40, 90][k])).toBeLessThanOrEqual(20);
  expect(ciede2000(rgbToLab(rgb), rgbToLab([20, 40, 90]))).toBeLessThan(5);
  expect(ciede2000(rgbToLab(rgb), rgbToLab([255, 255, 255]))).toBeGreaterThan(60);
});

test("samplePatch averages light, not sRGB numbers: half black, half white is not 128", () => {
  const img = image(10, 1, (x) => (x < 5 ? [0, 0, 0, 255] : [255, 255, 255, 255]));
  const { rgb } = samplePatch({ ...img }, 4, 0, 20);
  expect(rgb).toEqual([188, 188, 188]);
});

test("samplePatch clips at the image edge and ignores see-through pixels", () => {
  const img = image(10, 10, (x) => (x < 2 ? [9, 9, 9, 0] : [100, 150, 200, 255]));
  const corner = samplePatch(img, 9, 9, 3);
  expect(corner).toEqual({ rgb: [100, 150, 200], count: 16 });
  expect(samplePatch(img, 2, 5, 2).rgb).toEqual([100, 150, 200]);
});

test("samplePatch returns null when there is nothing to read", () => {
  const clear = image(6, 6, () => [50, 50, 50, 0]);
  expect(samplePatch(clear, 3, 3, 2)).toBeNull();
  expect(samplePatch(image(6, 6, () => [1, 1, 1, 255]), 40, 40, 2)).toBeNull();
  expect(samplePatch(null, 0, 0, 2)).toBeNull();
});

// --- matchWord --------------------------------------------------------------

test("matchWord grades a difference in plain words on the bands preflight already cites", () => {
  expect(matchWord(0.4)).toBe("very close");
  expect(matchWord(1.9)).toBe("close");
  expect(matchWord(3.0)).toBe("noticeable");
  expect(matchWord(4.9)).toBe("clearly different");
  expect(matchWord(12)).toBe("a different colour");
  expect(matchWord(NaN)).toBe("");
});
