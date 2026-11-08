// stitchSample: the popover's 12 x 8 mm patch of the chosen stitching.
//
// vitest's node environment has no canvas 2D context, and a call-recording
// double cannot say whether satin LOOKS different from tatami. So the pixel
// tests below paint through `RasterCtx`: a tiny software rasterizer for the
// handful of calls drawThreads makes (stroked line paths with round caps,
// solid colours and alpha, dashes, fillRect), 3 x 3 supersampled. It is not a
// browser -- the anti-aliasing is cruder -- but every stroke drawThreads asks
// for lands where Chromium would put it, which is what the structure tests
// measure. The real-browser repaint timing is in the PR body (Playwright).
import { describe, expect, test } from "vitest";
import {
  sampleStrands, paintSample, sampleSpecFromModel, sampleCaption, sampleDensities, drawStitchSample,
  SAMPLE_W_MM, SAMPLE_H_MM, SAMPLE_PX_PER_MM, AUTO_SAMPLE_ANGLE,
} from "./stitchSample.js";
import { popoverModel } from "./shapePopover.js";

// The engine's spacings (digitize.js FILL_ROW_MM / SATIN_SPACING_MM), handed
// in as a fake engine global: this spec does not load the engine.
const ENG = { FILL_ROW_MM: 0.15, SATIN_SPACING_MM: 0.4, LETTERING_GUARDS: { BEAN_STITCH_MM: 2.5, BEAN_PASSES: 3 } };
const DENS = sampleDensities(ENG);
const RED = [200, 40, 40];

function parseColor(s) {
  if (s[0] === "#") {
    const h = s.length === 4 ? s.slice(1).split("").map((c) => c + c).join("") : s.slice(1);
    return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16), 1];
  }
  const m = /rgba?\(([^)]+)\)/.exec(s);
  const p = m[1].split(",").map((v) => parseFloat(v));
  return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
}

class RasterCtx {
  constructor(w, h) {
    this.w = w; this.h = h;
    this.px = new Float32Array(w * h * 3);
    this.lineWidth = 1; this.strokeStyle = "#000"; this.fillStyle = "#000"; this.globalAlpha = 1;
    this.dash = []; this.path = []; this.lineCap = "round"; this.lineJoin = "round";
  }
  setTransform() {}
  save() {} restore() {}
  setLineDash(d) { this.dash = d || []; }
  beginPath() { this.path = []; }
  moveTo(x, y) { this.path.push([[x, y]]); }
  lineTo(x, y) { this.path[this.path.length - 1].push([x, y]); }
  fillRect(x, y, w, h) {
    const [r, g, b, a0] = parseColor(this.fillStyle);
    const a = a0 * this.globalAlpha;
    for (let j = Math.max(0, Math.floor(y)); j < Math.min(this.h, Math.ceil(y + h)); j++)
      for (let i = Math.max(0, Math.floor(x)); i < Math.min(this.w, Math.ceil(x + w)); i++) this.blend(j * this.w + i, r, g, b, a);
  }
  blend(k, r, g, b, a) {
    const p = this.px;
    p[3 * k] += (r - p[3 * k]) * a; p[3 * k + 1] += (g - p[3 * k + 1]) * a; p[3 * k + 2] += (b - p[3 * k + 2]) * a;
  }
  stroke() {
    const [r, g, b, a0] = parseColor(this.strokeStyle);
    const a = a0 * this.globalAlpha;
    const hw = this.lineWidth / 2;
    const cov = new Float32Array(this.w * this.h); // union coverage of the whole path
    const S = 3;
    const period = this.dash.length ? this.dash.reduce((s, v) => s + v, 0) : 0;
    for (const sub of this.path) {
      let along = 0; // the dash phase restarts with every subpath
      for (let q = 1; q < sub.length; q++) {
        const [x0, y0] = sub[q - 1], [x1, y1] = sub[q];
        const dx = x1 - x0, dy = y1 - y0, L2 = dx * dx + dy * dy, L = Math.sqrt(L2);
        const i0 = Math.max(0, Math.floor(Math.min(x0, x1) - hw)), i1 = Math.min(this.w - 1, Math.ceil(Math.max(x0, x1) + hw));
        const j0 = Math.max(0, Math.floor(Math.min(y0, y1) - hw)), j1 = Math.min(this.h - 1, Math.ceil(Math.max(y0, y1) + hw));
        for (let j = j0; j <= j1; j++) for (let i = i0; i <= i1; i++) {
          let hit = 0;
          for (let sy = 0; sy < S; sy++) for (let sx = 0; sx < S; sx++) {
            const X = i + (sx + 0.5) / S, Y = j + (sy + 0.5) / S;
            let t = L2 > 0 ? ((X - x0) * dx + (Y - y0) * dy) / L2 : 0;
            t = Math.max(0, Math.min(1, t));
            const ex = x0 + t * dx - X, ey = y0 + t * dy - Y;
            if (ex * ex + ey * ey > hw * hw) continue;
            if (period > 0) {
              let s = (along + t * L) % period, on = true;
              for (let d = 0; d < this.dash.length; d++) { if (s < this.dash[d]) { on = d % 2 === 0; break; } s -= this.dash[d]; }
              if (!on) continue;
            }
            hit++;
          }
          const c = hit / (S * S), k = j * this.w + i;
          if (c > cov[k]) cov[k] = c;
        }
        along += L;
      }
    }
    for (let k = 0; k < cov.length; k++) if (cov[k] > 0) this.blend(k, r, g, b, a * cov[k]);
  }
  lum() {
    const out = new Float32Array(this.w * this.h);
    for (let k = 0; k < out.length; k++) out[k] = 0.2126 * this.px[3 * k] + 0.7152 * this.px[3 * k + 1] + 0.0722 * this.px[3 * k + 2];
    return out;
  }
}

function render(type, angleDeg, rgb = RED) {
  const w = SAMPLE_W_MM * SAMPLE_PX_PER_MM, h = SAMPLE_H_MM * SAMPLE_PX_PER_MM;
  const ctx = new RasterCtx(w, h);
  const strands = sampleStrands({ type, angleDeg, rgb, rowMm: DENS.rowMm, satinMm: DENS.satinMm });
  paintSample(ctx, strands, rgb);
  return { lum: ctx.lum(), w, h, n: strands.length };
}

// The mean variance of luminance along pixel ROWS (horizontal lines), over
// the inner 80% of the patch (edges carry clipped caps).
function rowVariance({ lum, w, h }) {
  let tot = 0, n = 0;
  for (let j = Math.floor(h * 0.1); j < Math.ceil(h * 0.9); j++) {
    let s = 0, s2 = 0, c = 0;
    for (let i = Math.floor(w * 0.1); i < Math.ceil(w * 0.9); i++) { const v = lum[j * w + i]; s += v; s2 += v * v; c++; }
    tot += s2 / c - (s / c) ** 2; n++;
  }
  return tot / n;
}
// The variance of the pixel rows' MEAN luminance, over the same inner patch.
function betweenRowVariance({ lum, w, h }) {
  const means = [];
  for (let j = Math.floor(h * 0.1); j < Math.ceil(h * 0.9); j++) {
    let s = 0, c = 0;
    for (let i = Math.floor(w * 0.1); i < Math.ceil(w * 0.9); i++) { s += lum[j * w + i]; c++; }
    means.push(s / c);
  }
  const m = means.reduce((a, b) => a + b, 0) / means.length;
  return means.reduce((a, b) => a + (b - m) ** 2, 0) / means.length;
}
function colVariance(img) {
  const { lum, w, h } = img;
  const t = new Float32Array(w * h); // transpose, then the same measure
  for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) t[i * h + j] = lum[j * w + i];
  return rowVariance({ lum: t, w: h, h: w });
}

// The dominant gradient orientation, degrees mod 180, from the structure
// tensor of a central-difference gradient over the inner patch.
function dominantGradientDeg({ lum, w, h }) {
  let xx = 0, yy = 0, xy = 0;
  for (let j = 2; j < h - 2; j++) for (let i = 2; i < w - 2; i++) {
    const gx = (lum[j * w + i + 1] - lum[j * w + i - 1]) / 2;
    const gy = (lum[(j + 1) * w + i] - lum[(j - 1) * w + i]) / 2;
    xx += gx * gx; yy += gy * gy; xy += gx * gy;
  }
  const th = (0.5 * Math.atan2(2 * xy, xx - yy) * 180) / Math.PI;
  return ((th % 180) + 180) % 180;
}
const angDiff = (a, b) => { const d = Math.abs(a - b) % 180; return Math.min(d, 180 - d); };

describe("the sample's pixels", () => {
  test("satin and tatami differ: row variance, satin over tatami, >= 2", () => {
    // Stitches horizontal (angle 0), so a pixel row runs ALONG the stitches.
    // Row variance = the variance BETWEEN pixel rows' mean luminance: satin's
    // crosses lie 0.4 mm apart, one thread width, so each one reads as its
    // own ridge; tatami's rows lie 0.15 mm apart and merge into one sheet,
    // broken instead ALONG the row at its staggered holes.
    const satin = render("satin", 0), tatami = render("tatami", 0);
    const rs = betweenRowVariance(satin), rt = betweenRowVariance(tatami);
    const as = colVariance(satin) / rowVariance(satin), at = colVariance(tatami) / rowVariance(tatami);
    console.log(`[stitchSample] between-row variance: satin ${rs.toFixed(1)}, tatami ${rt.toFixed(1)}, ratio ${(rs / rt).toFixed(2)}; along-row: satin ${rowVariance(satin).toFixed(1)}, tatami ${rowVariance(tatami).toFixed(1)}; across/along: satin ${as.toFixed(2)}, tatami ${at.toFixed(2)}`);
    expect(rs / rt).toBeGreaterThanOrEqual(2);
    // The same difference as a shape: satin is strongly directional, tatami
    // much less so.
    expect(as / at).toBeGreaterThanOrEqual(2);
  });

  for (const type of ["satin", "tatami"]) {
    test(`${type}: turning the angle 90° turns the dominant gradient 90° (+/- 10)`, () => {
      for (const a of [0, 30, 45]) {
        const g0 = dominantGradientDeg(render(type, a));
        const g1 = dominantGradientDeg(render(type, a + 90));
        const turn = angDiff(g0, g1);
        console.log(`[stitchSample] ${type} ${a}° -> ${a + 90}°: gradient ${g0.toFixed(1)}° -> ${g1.toFixed(1)}°, turned ${turn.toFixed(1)}°`);
        expect(Math.abs(turn - 90)).toBeLessThanOrEqual(10);
      }
    });
  }

  test("the colour drawn is the thread's: a red sample is red, a blue one blue", () => {
    const sum = (rgb) => {
      const ctx = new RasterCtx(120, 80);
      paintSample(ctx, sampleStrands({ type: "tatami", angleDeg: 45, rgb, rowMm: DENS.rowMm, satinMm: DENS.satinMm }), rgb);
      let r = 0, b = 0;
      for (let k = 40 * 120 + 20; k < 40 * 120 + 100; k++) { r += ctx.px[3 * k]; b += ctx.px[3 * k + 2]; }
      return { r, b };
    };
    const red = sum([200, 40, 40]), blue = sum([40, 40, 200]);
    expect(red.r).toBeGreaterThan(2 * red.b);
    expect(blue.b).toBeGreaterThan(2 * blue.r);
  });
});

describe("strands", () => {
  test("every type fills the patch and stays inside it", () => {
    for (const type of ["satin", "tatami", "brick", "run", "bean"]) {
      const s = sampleStrands({ type, angleDeg: 30, rgb: RED, rowMm: 0.15, satinMm: 0.4, stitchMm: type === "run" || type === "bean" ? 2.5 : null });
      expect(s.length, type).toBeGreaterThan(5);
      for (const q of s) for (const [x, y] of [[q.x0, q.y0], [q.x1, q.y1]]) {
        expect(x).toBeGreaterThanOrEqual(-1e-6); expect(x).toBeLessThanOrEqual(SAMPLE_W_MM + 1e-6);
        expect(y).toBeGreaterThanOrEqual(-1e-6); expect(y).toBeLessThanOrEqual(SAMPLE_H_MM + 1e-6);
      }
    }
  });

  test("satin crosses sit at the satin spacing; tatami rows at the fill row, cut into stitches", () => {
    const sat = sampleStrands({ type: "satin", angleDeg: 0, rgb: RED, rowMm: 0.15, satinMm: 0.4 });
    expect(sat.length).toBe(21); // 8 mm / 0.4 mm, centred: rows -10..10
    expect(sat.every((q) => Math.abs(Math.abs(q.x1 - q.x0) - SAMPLE_W_MM) < 1e-9 && q.kind === "satin")).toBe(true);
    const tat = sampleStrands({ type: "tatami", angleDeg: 0, rgb: RED, rowMm: 0.15, satinMm: 0.4 });
    const rows = new Set(tat.map((q) => q.y0.toFixed(4)));
    expect(rows.size).toBe(53); // 8 mm / 0.15 mm, centred
    expect(Math.max(...tat.map((q) => Math.abs(q.x1 - q.x0)))).toBeLessThanOrEqual(3 + 1e-9);
    expect(tat.every((q) => q.kind === "fill")).toBe(true);
    // Staggered: the first hole of three consecutive rows falls at three
    // different places.
    const firstHoles = [...rows].slice(20, 23).map((y) => Math.min(...tat.filter((q) => q.y0.toFixed(4) === y && q.x0 > 1e-6).map((q) => q.x0)));
    expect(new Set(firstHoles.map((v) => v.toFixed(3))).size).toBe(3);
  });

  test("a bean sews each stitch three times; a run once", () => {
    const run = sampleStrands({ type: "run", angleDeg: 0, rgb: RED, stitchMm: 2.5 });
    const bean = sampleStrands({ type: "bean", angleDeg: 0, rgb: RED, stitchMm: 2.5 });
    expect(bean.length).toBe(3 * run.length);
    expect(bean.every((q) => q.kind === "bean")).toBe(true);
  });
});

describe("from the popover's model", () => {
  const square = [{ x: 0, y: 0 }, { x: 100, y: 0 }, { x: 100, y: 100 }, { x: 0, y: 100 }];
  const manual = (patch) => ({ id: 4, type: "manual", shapes: [{ id: "s1", points: square, curves: {}, stitchType: "fill", colorRgb: [20, 20, 20], angleDeg: null, ...patch }] });
  const digitized = (entry, tier = "fill") => ({ id: 6, type: "digitized", params: { border: null },
    review: { brandId: "isacord", shapes: [{ id: "Sabc", threadNumber: "1301", areaMm2: 123.4, tier, rgb: [10, 20, 30] }] },
    shapeOverrides: entry ? { Sabc: entry } : {}, deletedShapeIds: [] });

  test("manual fill, auto angle: tatami at the auto sample angle, captioned as auto", () => {
    const spec = sampleSpecFromModel(popoverModel({ element: manual(), shapeId: "s1" }));
    expect(spec).toEqual({ type: "tatami", angleDeg: AUTO_SAMPLE_ANGLE, autoAngle: true, rgb: [20, 20, 20], stitchMm: null });
    expect(sampleCaption(spec)).toBe(`Fill sample, auto angle (shown ${AUTO_SAMPLE_ANGLE}°)`);
  });

  test("a pick wins over the stored value, before the patch round-trip", () => {
    const m = popoverModel({ element: manual({ angleDeg: 30 }), shapeId: "s1" });
    expect(sampleSpecFromModel(m).angleDeg).toBe(30);
    const spec = sampleSpecFromModel(m, { stitchType: "satin", angle: "120", color: [1, 2, 3] });
    expect(spec).toMatchObject({ type: "satin", angleDeg: 120, autoAngle: false, rgb: [1, 2, 3] });
    expect(sampleCaption(spec)).toBe("Satin sample, 120°");
  });

  test("digitized: Auto reads its effective tier; a stored tier and angle are used", () => {
    expect(sampleSpecFromModel(popoverModel({ element: digitized(null, "satin"), shapeId: "Sabc" })).type).toBe("satin");
    const spec = sampleSpecFromModel(popoverModel({ element: digitized({ tier: "brick", fill_angle_deg: 60 }), shapeId: "Sabc" }));
    expect(spec).toMatchObject({ type: "brick", angleDeg: 60, autoAngle: false, rgb: [10, 20, 30] });
    expect(sampleCaption(spec)).toBe("Brick sample, 60°");
    expect(sampleSpecFromModel(popoverModel({ element: digitized({ fill_angle_deg: 135 }), shapeId: "Sabc" }))).toMatchObject({ type: "tatami", angleDeg: 135 });
  });

  // Post-merge review of #1342: brick has no angle row, but the service sews
  // brick as a fill and reads the stored fill_angle_deg; with none stored the
  // digitizer picks the angle, so the sample must SAY auto, never a definite
  // 45°. A digitized satin's crosses follow its column: never a definite 90°.
  test("digitized brick with no stored angle, and digitized satin, are captioned auto", () => {
    const brick = sampleSpecFromModel(popoverModel({ element: digitized({ tier: "brick" }), shapeId: "Sabc" }));
    expect(brick).toMatchObject({ type: "brick", angleDeg: AUTO_SAMPLE_ANGLE, autoAngle: true });
    expect(sampleCaption(brick)).toBe(`Brick sample, auto angle (shown ${AUTO_SAMPLE_ANGLE}°)`);
    const satin = sampleSpecFromModel(popoverModel({ element: digitized(null, "satin"), shapeId: "Sabc" }));
    expect(satin).toMatchObject({ type: "satin", autoAngle: true });
    expect(sampleCaption(satin)).toMatch(/^Satin sample, auto angle \(shown \d+°\)$/);
    // A satin keeps no fill angle: a stored one (switched from fill) is not its direction.
    expect(sampleSpecFromModel(popoverModel({ element: digitized({ tier: "satin", fill_angle_deg: 60 }), shapeId: "Sabc" }))).toMatchObject({ autoAngle: true });
  });

  test("picking Brick on a fill shape at 135° keeps 135° once the new model lands", () => {
    const fillModel = popoverModel({ element: digitized({ fill_angle_deg: 135 }), shapeId: "Sabc" });
    expect(sampleSpecFromModel(fillModel, { stitchType: "brick" })).toMatchObject({ type: "brick", angleDeg: 135, autoAngle: false });
    const brickModel = popoverModel({ element: digitized({ tier: "brick", fill_angle_deg: 135 }), shapeId: "Sabc" });
    expect(sampleSpecFromModel(brickModel)).toMatchObject({ type: "brick", angleDeg: 135, autoAngle: false });
  });

  test("a run shape samples run or bean by its passes", () => {
    const line = { id: "s1", kind: "run", points: [{ x: 0, y: 0 }, { x: 100, y: 0 }], curves: {}, colorRgb: [5, 5, 5], passes: 1, stitchLenMm: 2 };
    const m = popoverModel({ element: { id: 4, type: "manual", shapes: [line] }, shapeId: "s1" });
    if (!m.rows.some((r) => r.key === "passes")) return; // not a run in this build's manualShapes
    expect(sampleSpecFromModel(m)).toMatchObject({ type: "run", stitchMm: 2 });
    expect(sampleSpecFromModel(m, { passes: "3" }).type).toBe("bean");
  });

  test("nothing to sample: a cut-out, or no engine loaded", () => {
    expect(sampleSpecFromModel(popoverModel({ element: manual({ cutOut: true }), shapeId: "s1" }))).toBe(null);
    expect(sampleDensities(undefined)).toBe(null);
    expect(sampleDensities({})).toBe(null);
  });
});

describe("repaint cost", () => {
  test("building + painting the busiest sample: strand count and JS time (call-only ctx)", () => {
    // The pixels are the browser's; this times everything that is OURS --
    // strand building and drawThreads' grouping/projection -- against a ctx
    // that records nothing. Real-canvas timing is measured in Chromium.
    const noop = () => {};
    const ctx = new Proxy({}, { get: (t, k) => (k in t ? t[k] : noop), set: (t, k, v) => { t[k] = v; return true; } });
    const canvas = { width: 0, height: 0, getContext: () => ctx };
    const spec = { type: "tatami", angleDeg: 30, rgb: RED, stitchMm: null };
    const times = [];
    let n = 0;
    for (let i = 0; i < 50; i++) {
      const t0 = performance.now();
      n = drawStitchSample(canvas, { ...spec, angleDeg: 30 + i }, DENS, { dpr: 2 });
      times.push(performance.now() - t0);
    }
    times.sort((a, b) => a - b);
    console.log(`[stitchSample] tatami ${n} strands, JS-side median ${times[25].toFixed(3)} ms over 50`);
    expect(canvas.width).toBe(240);
    expect(times[25]).toBeLessThan(5);
  });
});
