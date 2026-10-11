// The 8,255 designs PR 616 and PR 617 were measured on, as a set
// tools/file-cut-census.mjs can read:
//
//   node tools/file-cut-census.mjs --set tools/file-cut-sweep-set.mjs
//
// The generator is `sweepCorpus` of tools/sub-unit-stitch-census.mjs, copied
// whole, so that the two tools count the same designs. Only the wrapping at
// the foot is this file's.
export default function ({ DG, FAB }) {
  function sweepCorpus() {
    const R = (pts) => pts.map(([x, y]) => ({ x, y }));
    const box = (x0, y0, x1, y1) => R([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]);
    const round = (cx, cy, rx, ry, n) => Array.from({ length: n }, (_, i) => ({ x: cx + rx * Math.cos(2 * Math.PI * i / n), y: cy + ry * Math.sin(2 * Math.PI * i / n) }));
    const comb = (n, tw, gw, tl, sp) => {
      const pts = []; let x = 0;
      for (let i = 0; i < n; i++) { pts.push([x, 0], [x + tw, 0]); if (i < n - 1) pts.push([x + tw, tl], [x + tw + gw, tl]); x += tw + gw; }
      const w = n * tw + (n - 1) * gw;
      pts.push([w, tl + sp], [0, tl + sp]);
      return R(pts);
    };
    const bbox = (ring) => { let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity; for (const p of ring) { x0 = Math.min(x0, p.x); x1 = Math.max(x1, p.x); y0 = Math.min(y0, p.y); y1 = Math.max(y1, p.y); } return { x0, x1, y0, y1 }; };
    const turn = (shape, q) => {
      const f = [(p) => ({ x: p.x, y: p.y }), (p) => ({ x: -p.y, y: p.x }), (p) => ({ x: -p.x, y: -p.y }), (p) => ({ x: p.y, y: -p.x })][q];
      const outer = shape.outer.map(f), b = bbox(outer), mv = (p) => ({ x: p.x - b.x0, y: p.y - b.y0 });
      return { outer: outer.map(mv), holes: shape.holes.map((h) => h.map(f).map(mv)) };
    };
    const drawn = [];
    const add = (name, outer, holes, turns) => { for (const q of (turns || [0])) drawn.push([name + (turns && turns.length > 1 ? " q" + q : ""), turn({ outer, holes: holes || [] }, q)]); };
    const Q = [0, 1, 2, 3];
    for (const [n, tw, gw, tl, sp] of [[8, 28, 17.5, 245, 105], [3, 60, 45, 180, 120], [5, 30, 20, 200, 100], [6, 24, 15, 210, 90], [4, 40, 25, 150, 100], [8, 24, 15, 210, 90]]) add(`comb ${n}x${tw}/${gw}`, comb(n, tw, gw, tl, sp), [], Q);
    add("T", R([[0, 0], [350, 0], [350, 105], [227.5, 105], [227.5, 350], [122.5, 350], [122.5, 105], [0, 105]]), [], Q);
    add("L", R([[0, 0], [100, 0], [100, 235], [300, 235], [300, 335], [0, 335]]), [], Q);
    add("wide U", R([[0, 0], [140, 0], [140, 180], [300, 180], [300, 0], [440, 0], [440, 280], [0, 280]]), [], Q);
    add("tall U", R([[0, 0], [100, 0], [100, 300], [200, 300], [200, 0], [300, 0], [300, 400], [0, 400]]), [], Q);
    add("E", R([[0, 0], [260, 0], [260, 60], [80, 60], [80, 130], [220, 130], [220, 190], [80, 190], [80, 260], [260, 260], [260, 320], [0, 320]]), [], Q);
    add("H", R([[0, 0], [90, 0], [90, 120], [210, 120], [210, 0], [300, 0], [300, 300], [210, 300], [210, 180], [90, 180], [90, 300], [0, 300]]), [], [0, 1]);
    add("plus", R([[122.5, 0], [227.5, 0], [227.5, 122.5], [350, 122.5], [350, 227.5], [227.5, 227.5], [227.5, 350], [122.5, 350], [122.5, 227.5], [0, 227.5], [0, 122.5], [122.5, 122.5]]), [], [0]);
    add("stairs", R([[0, 0], [75, 0], [75, 75], [150, 75], [150, 150], [225, 150], [225, 225], [300, 225], [300, 300], [0, 300]]), [], Q);
    add("badge, two cut-outs", box(0, 0, 400, 400), [box(60, 140, 180, 260), box(285, 185, 315, 215)], Q);
    add("square, one hole", box(0, 0, 300, 300), [box(100, 100, 200, 200)], [0]);
    add("B", box(0, 0, 260, 360), [box(80, 60, 180, 140), box(80, 200, 200, 300)], Q);
    { const h = []; for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) h.push(box(60 + c * 100, 60 + r * 100, 100 + c * 100, 100 + r * 100)); add("badge 3x3", box(0, 0, 360, 360), h, [0]); }
    { const h = []; for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) h.push(box(40 + c * 95, 40 + r * 95, 80 + c * 95, 80 + r * 95)); add("badge 4x4", box(0, 0, 410, 410), h, [0]); }
    { const h = []; for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) h.push(round(100 + c * 150, 100 + r * 150, 35, 35, 24)); add("nine round holes", box(0, 0, 500, 500), h, [0]); }
    add("ring", round(150, 180, 150, 180, 64), [round(150, 180, 70, 100, 64)], [0, 1]);
    add("annulus", round(200, 200, 200, 200, 64), [round(200, 200, 110, 110, 48)], [0]);
    add("house, window on the grid", R([[150, 0], [300, 120], [300, 300], [0, 300], [0, 120]]), [box(100, 150, 200, 250)], Q);
    add("house, window off it", R([[150, 0], [300, 120], [300, 300], [0, 300], [0, 120]]), [box(95, 150, 195, 250)], Q);
    add("house, no window", R([[150, 0], [300, 120], [300, 300], [0, 300], [0, 120]]), [], Q);
    add("diamond with a hole", R([[150, 0], [300, 150], [150, 300], [0, 150]]), [box(110, 110, 190, 190)], [0, 1]);
    add("triangle with a hole", R([[150, 0], [300, 260], [0, 260]]), [box(120, 150, 180, 210)], Q);
    add("two peaks", R([[0, 300], [100, 0], [200, 200], [300, 50], [400, 300]]), [], Q);
    add("three peaks, a hole", R([[0, 300], [60, 0], [120, 180], [180, 30], [240, 180], [300, 0], [360, 300]]), [box(150, 220, 210, 270)], Q);
    add("arrow", R([[150, 0], [300, 150], [210, 150], [210, 350], [90, 350], [90, 150], [0, 150]]), [], Q);
    for (const n of [5, 6, 8]) {
      const star = []; for (let i = 0; i < 2 * n; i++) { const a = -Math.PI / 2 + Math.PI * i / n, r = i % 2 ? 80 : 180; star.push({ x: Math.round(180 + r * Math.cos(a)), y: Math.round(180 + r * Math.sin(a)) }); }
      add(`star ${n}`, star, [], [0, 1]);
      add(`star ${n}, a hole`, star, [box(160, 160, 200, 200)], [0, 1]);
      add(`polygon ${n}, a hole`, round(180, 180, 180, 180, n).map((p) => ({ x: Math.round(p.x), y: Math.round(p.y) })), [box(130, 130, 230, 230)], [0, 1]);
    }
    add("bullseye", box(0, 0, 400, 400), [box(80, 80, 320, 320), box(160, 160, 240, 240)], [0]);
    add("slot", box(0, 0, 300, 300), [box(145, 60, 155, 240)], [0, 1]);

    let seed = 4242;
    const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    const pick = (a) => a[Math.floor(rnd() * a.length)];
    const starR = (cx, cy, r, n, rough) => { const ph = rnd() * Math.PI * 2, pts = []; for (let i = 0; i < n; i++) { const a = ph + (2 * Math.PI * i) / n, rr = r * (1 - rough * rnd()); pts.push({ x: cx + rr * Math.cos(a), y: cy + rr * Math.sin(a) }); } return pts; };
    const stairsR = (w, h) => { const steps = 2 + Math.floor(rnd() * 4), top = [], bottom = []; let x = 0; for (let i = 0; i < steps; i++) { const nx = i === steps - 1 ? w : x + (w - x) * (0.2 + 0.5 * rnd()); const y0 = h * 0.4 * rnd(), y1 = h * (0.6 + 0.4 * rnd()); top.push({ x, y: y0 }, { x: nx, y: y0 }); bottom.push({ x, y: y1 }, { x: nx, y: y1 }); x = nx; } return top.concat(bottom.reverse()); };
    const edgesOf = (polys) => { const e = []; for (const p of polys) for (let i = 0; i < p.length; i++) e.push([p[i], p[(i + 1) % p.length]]); return e; };
    const insideE = (p, edges) => { let c = false; for (const [u, v] of edges) if ((u.y > p.y) !== (v.y > p.y) && u.x + ((p.y - u.y) / (v.y - u.y)) * (v.x - u.x) > p.x) c = !c; return c; };
    const depthE = (p, edges) => { let m = Infinity; for (const [u, v] of edges) { const dx = v.x - u.x, dy = v.y - u.y, l2 = dx * dx + dy * dy; const t = l2 ? Math.max(0, Math.min(1, ((p.x - u.x) * dx + (p.y - u.y) * dy) / l2)) : 0; m = Math.min(m, Math.hypot(p.x - (u.x + t * dx), p.y - (u.y + t * dy))); } return m; };
    const random = [];
    for (let t = 0; t < 260; t++) {
      const k = 1.5 + 2 * rnd();
      const sc = (r) => r.map((p) => ({ x: p.x * k, y: p.y * k }));
      const whole = rnd() < 0.35;
      const snap = (r) => whole ? r.map((p) => ({ x: Math.round(p.x), y: Math.round(p.y) })) : r;
      const outer0 = rnd() < 0.67 ? starR(100, 100, 60 + 40 * rnd(), 5 + Math.floor(rnd() * 30), pick([0, 0.2, 0.5])) : stairsR(160 + 60 * rnd(), 120 + 80 * rnd());
      const oe = edgesOf([outer0]), placed = [], holes0 = [];
      for (let h = Math.floor(rnd() * 6); h > 0; h--) {
        for (let tries = 0; tries < 20; tries++) {
          const c = { x: 20 + 180 * rnd(), y: 20 + 180 * rnd() }, r = 4 + 16 * rnd();
          if (!insideE(c, oe) || depthE(c, oe) < r + 4) continue;
          if (placed.some((q) => Math.hypot(q.c.x - c.x, q.c.y - c.y) < q.r + r + 3)) continue;
          holes0.push(starR(c.x, c.y, r, pick([4, 4, 6, 12, 20]), pick([0, 0, 0.3])));
          placed.push({ c, r });
          break;
        }
      }
      random.push([`random ${t}${whole ? " (whole px)" : ""}`, { outer: snap(sc(outer0)), holes: holes0.map((h) => snap(sc(h))) }, rnd() * 180]);
    }

    const designs = [];
    const fabrics = [null].concat(FAB.FABRICS);
    for (const [name, shape] of drawn) for (const fabric of fabrics) for (const angle of [null, 0, 90, 30]) designs.push({ name, shape, fabric, angle, underlay: true, set: "drawn" });
    for (const [name, shape] of drawn) for (const angle of [null, 0, 90]) designs.push({ name, shape, fabric: null, angle, underlay: false, set: "drawn" });
    for (const [name, shape, ang] of random) for (const fabric of fabrics) for (const angle of [null, Math.round(ang * 10) / 10]) designs.push({ name, shape, fabric, angle, underlay: true, set: "random" });
    const build = (d, extra, dg) => {
      const s = Object.assign({ tierOverride: "fill" }, d.shape);
      if (d.angle != null) s.angleOverride = d.angle;
      const b = bbox(d.shape.outer);
      const o = { garment: { id: "left_chest", widthIn: 4, heightIn: 4 }, pxPerMm: 10, targetWidthMm: (b.x1 - b.x0) / 10, darkOnTop: false, underlay: d.underlay };
      if (d.fabric) o.fabric = d.fabric;
      return (dg || DG).buildQualityDesign([{ rgb: [0, 0, 0], shapes: [s] }], Object.assign(o, extra));
    };
    const tag = (d) => ({ fabric: d.fabric ? d.fabric.id : "none", angle: d.angle == null ? "auto" : String(d.angle), set: d.set });
    return { designs, build, tag };
  }
  const c = sweepCorpus();
  return {
    designs: c.designs.map((d) => Object.assign({ lane: d.set, sizeMm: null }, d)),
    build: (d, extra, dg) => c.build(d, extra, dg),
    arms: { "as shipped": {}, "fillColumns on": { fillColumns: true } },
  };
}
