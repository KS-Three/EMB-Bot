import { describe, it, expect } from "vitest";
import { nodesForShape, nodeMarker, spanOfEdge, withNodes, ringEditOverrides, discardPatch, seedNodesCached, ringFingerprint, pastClickDeadZone } from "./shapeNodes.js";
import { seedNodes } from "./sparseNodes.js";
import { hitOverlay, nodesInBox, ringNodesInBox, simplifyRing } from "./shapeOverlay.js";

// A 40 mm square with 5 vertices per side (20 points), centred on the origin.
function squareRing(half = 20, per = 5) {
  const pts = [];
  const step = (2 * half) / per;
  for (let i = 0; i < per; i++) pts.push([-half + i * step, -half]);
  for (let i = 0; i < per; i++) pts.push([half, -half + i * step]);
  for (let i = 0; i < per; i++) pts.push([half - i * step, half]);
  for (let i = 0; i < per; i++) pts.push([-half, half - i * step]);
  return pts;
}
function circleRing(r = 20, n = 64) {
  return Array.from({ length: n }, (_, i) => [r * Math.cos((2 * Math.PI * i) / n), r * Math.sin((2 * Math.PI * i) / n)]);
}

describe("nodesForShape", () => {
  const shell = squareRing();
  it("seeds when nothing is stored, and the seeds are exactly seedNodes", () => {
    const got = nodesForShape(undefined, shell, []);
    expect(got.stored).toBe(false);
    expect(got.shell).toEqual(seedNodes(shell));
    expect(got.shell.map((n) => n.kind)).toEqual(["corner", "corner", "corner", "corner"]);
  });
  it("a valid stored list wins over the seeds", () => {
    const stored = { shell: [{ i: 0, kind: "smooth" }, { i: 6, kind: "corner" }, { i: 12, kind: "smooth" }], holes: [] };
    const got = nodesForShape({ nodes: stored }, shell, []);
    expect(got.stored).toBe(true);
    expect(got.shell).toEqual(stored.shell);
    // a copy: the caller can edit it without touching the override
    got.shell[0].kind = "corner";
    expect(stored.shell[0].kind).toBe("smooth");
  });
  it("an invalid stored list (index out of range, unsorted, under 3) is ignored and re-seeded", () => {
    for (const bad of [
      [{ i: 0, kind: "smooth" }, { i: 6, kind: "smooth" }, { i: 99, kind: "smooth" }],
      [{ i: 6, kind: "smooth" }, { i: 0, kind: "smooth" }, { i: 12, kind: "smooth" }],
      [{ i: 0, kind: "smooth" }, { i: 6, kind: "smooth" }],
    ]) {
      const got = nodesForShape({ nodes: { shell: bad, holes: [] } }, shell, []);
      expect(got.stored).toBe(false);
      expect(got.shell).toEqual(seedNodes(shell));
    }
  });
  it("a hole-count mismatch re-seeds every ring", () => {
    const hole = squareRing(5, 2);
    const stored = { shell: [{ i: 0, kind: "smooth" }, { i: 6, kind: "smooth" }, { i: 12, kind: "smooth" }], holes: [] };
    const got = nodesForShape({ nodes: stored }, shell, [hole]);
    expect(got.stored).toBe(false);
    expect(got.shell).toEqual(seedNodes(shell));
    expect(got.holes).toEqual([seedNodes(hole)]);
  });
  it("seeds are a pure function of the ring (cache returns equal, independent copies)", () => {
    const ring = circleRing();
    const a = seedNodesCached(ring), b = seedNodesCached(ring);
    expect(a).toEqual(b);
    a[0].kind = "corner";
    expect(seedNodesCached(ring)[0].kind).toBe(b[0].kind);
  });
});

describe("drawing helper and spans", () => {
  it("a corner draws as a square, a smooth node as the disc", () => {
    expect(nodeMarker("corner")).toBe("square");
    expect(nodeMarker("smooth")).toBe("disc");
  });
  it("spanOfEdge: the span that starts at the last node at or before the edge, wrapping", () => {
    const nodes = [{ i: 2, kind: "corner" }, { i: 6, kind: "corner" }, { i: 11, kind: "corner" }];
    expect(spanOfEdge(nodes, 2)).toBe(0);
    expect(spanOfEdge(nodes, 5)).toBe(0);
    expect(spanOfEdge(nodes, 6)).toBe(1);
    expect(spanOfEdge(nodes, 11)).toBe(2);
    expect(spanOfEdge(nodes, 0)).toBe(2);   // before the first node: the wrapping span
  });
});

describe("withNodes", () => {
  it("puts a node list on every ring, a hole's at its own index", () => {
    const outlines = [
      { id: "a", key: "a", points: squareRing() },
      { id: "a", ring: 0, key: "a#h0", points: squareRing(5, 2) },
    ];
    const out = withNodes(outlines, undefined);
    expect(out[0].nodes).toEqual(seedNodes(outlines[0].points));
    expect(out[1].nodes).toEqual(seedNodes(outlines[1].points));
    expect(out[0].points).toBe(outlines[0].points);
  });
});

describe("hit testing and the marquee work on nodes", () => {
  // A 100 px square drawn with 4 dense vertices per side; nodes only at the corners.
  const ring = [];
  for (let i = 0; i < 4; i++) ring.push([i * 25, 0]);
  for (let i = 0; i < 4; i++) ring.push([100, i * 25]);
  for (let i = 0; i < 4; i++) ring.push([100 - i * 25, 100]);
  for (let i = 0; i < 4; i++) ring.push([0, 100 - i * 25]);
  const nodes = [{ i: 0, kind: "corner" }, { i: 4, kind: "corner" }, { i: 8, kind: "corner" }, { i: 12, kind: "corner" }];
  const o = { id: "s", points: ring, nodes };

  it("a vertex that is not a node is not a node hit (it is the edge)", () => {
    const hit = hitOverlay([o], 37, 1);
    expect(hit.kind).toBe("edge");
    expect(hit.index).toBe(1);   // a polygon edge index
  });
  it("a node hit is the NEAREST node and its index is the node-list index", () => {
    expect(hitOverlay([o], 98, 3)).toMatchObject({ kind: "node", index: 1 });
    expect(hitOverlay([o], 2, 98)).toMatchObject({ kind: "node", index: 3 });
  });
  it("without nodes every vertex is a node, as before", () => {
    expect(hitOverlay([{ id: "s", points: ring }], 25, 1)).toMatchObject({ kind: "node", index: 1 });
  });
  it("the marquee returns node-list indices, shells and holes", () => {
    const hole = { id: "s", ring: 0, points: [[40, 40], [60, 40], [60, 60], [40, 60]], nodes: [{ i: 0, kind: "corner" }, { i: 2, kind: "corner" }, { i: 3, kind: "corner" }] };
    expect(nodesInBox([o], -5, -5, 105, 55).get("s")).toEqual(new Set([0, 1]));
    const all = ringNodesInBox([o, hole], -5, -5, 105, 105).get("s");
    expect(all.get("exterior")).toEqual(new Set([0, 1, 2, 3]));
    expect(all.get(0)).toEqual(new Set([0, 1, 2]));
  });
});

// ---- the commit path (ringEditOverrides) -----------------------------------
// Field mm == the service's mm here: bboxMm is the outline's own bbox, so the
// fit is the identity apart from the y flip.
function fixture(extra = {}) {
  const outlineFull = squareRing();
  const rows = [{ id: "a", outlineFull, holesFull: [], ...extra }];
  const toField = (ring) => ring.map(([x, y]) => [x, -y]);
  const basis = {
    rows,
    bboxMm: { x0: -20, y0: -20, x1: 20, y1: 20 },
    rotationDeg: 0,
  };
  const field = toField(outlineFull);
  basis.nodesById = new Map([["a", seedNodes(field)]]);
  return { rows, basis, field, outlineFull };
}

describe("ringEditOverrides and nodes", () => {
  it("the node editor writes nodes beside the polygon, seeds included", () => {
    const { basis, field } = fixture();
    const moved = field.map(([x, y], i) => (i === 0 ? [x - 3, y + 3] : [x, y]));
    const res = ringEditOverrides({ shapeOverrides: {} }, basis, new Map([["a", moved]]), null, new Map([["a", basis.nodesById.get("a")]]));
    expect(res.error).toBeUndefined();
    const entry = res.cur.a;
    expect(entry.boundary_override).toHaveLength(20);
    expect(entry.nodes.shell).toEqual(basis.nodesById.get("a"));
    expect(entry.nodes.holes).toEqual([]);
  });
  it("Simplify (no liveNodes) DELETES nodes from the entry it rewrites", () => {
    const { basis, field } = fixture();
    const el = { shapeOverrides: { a: { border: "satin", nodes: { shell: basis.nodesById.get("a"), holes: [] } } } };
    const thin = simplifyRing(field, 0.5);
    expect(thin.length).toBeLessThan(field.length);
    const res = ringEditOverrides(el, basis, new Map([["a", thin]]));
    expect(res.cur.a.nodes).toBeUndefined();
    expect(res.cur.a.border).toBe("satin");        // the rest of the entry stays
    expect(res.cur.a.boundary_override).toHaveLength(thin.length);
  });
  it("an edit that touches only a hole keeps the untouched shell's nodes", () => {
    const hole = [[-5, -5], [5, -5], [5, 5], [-5, 5]];
    const { basis, rows } = fixture();
    rows[0].holesFull = [hole.map(([x, y]) => [x, -y])];
    basis.nodesById.set("a#h0", seedNodes(hole));
    const moved = hole.map(([x, y], i) => (i === 1 ? [x + 1, y] : [x, y]));
    const res = ringEditOverrides({ shapeOverrides: {} }, basis, new Map([["a#h0", moved]]), null, new Map([["a#h0", basis.nodesById.get("a#h0")]]));
    expect(res.error).toBeUndefined();
    expect(res.cur.a.boundary_override).toBeUndefined();
    expect(res.cur.a.nodes.shell).toEqual(basis.nodesById.get("a"));
    expect(res.cur.a.nodes.holes).toHaveLength(1);
  });
  it("deleting a hole outright drops its node list", () => {
    const hole = [[-5, -5], [5, -5], [5, 5], [-5, 5]];
    const { basis, rows } = fixture();
    rows[0].holesFull = [hole.map(([x, y]) => [x, -y])];
    basis.nodesById.set("a#h0", seedNodes(hole));
    const res = ringEditOverrides({ shapeOverrides: {} }, basis, new Map(), new Map([["a", new Set([0])]]), new Map());
    expect(res.cur.a.holes_override).toEqual([]);
    expect(res.cur.a.nodes.holes).toEqual([]);
  });
});

describe("Discard restores nodes", () => {
  it("the RESHAPE_KEYS snapshot carries shapeOverrides, nodes inside, back", () => {
    const KEYS = ["shapeOverrides", "shapes", "sizeMm", "offsetXMm", "offsetYMm"];
    const nodes = { shell: [{ i: 0, kind: "corner" }, { i: 5, kind: "corner" }, { i: 10, kind: "corner" }], holes: [] };
    const start = { shapeOverrides: { a: { nodes } }, shapes: undefined, sizeMm: 40, offsetXMm: 0, offsetYMm: 0 };
    const edited = { ...start, shapeOverrides: { a: { nodes: { ...nodes, shell: nodes.shell.slice(0, 3).map((n) => ({ ...n, kind: "smooth" })) } } } };
    const patch = discardPatch(edited, start, KEYS);
    expect(Object.keys(patch)).toEqual(["shapeOverrides"]);
    expect(patch.shapeOverrides.a.nodes).toEqual(nodes);
    // nothing edited -> no patch
    expect(discardPatch(start, start, KEYS)).toEqual({});
  });
});

describe("ring fingerprint (stale nodes after a re-digitize)", () => {
  const nodesOf = (ring) => seedNodes(ring);
  it("is invariant under scale, rotation and offset, and ignores a closing duplicate", () => {
    const ring = squareRing();
    const moved = ring.map(([x, y]) => [3 * (0.6 * x - 0.8 * y) + 7, 3 * (0.8 * x + 0.6 * y) - 2]);
    expect(ringFingerprint(moved)).toBe(ringFingerprint(ring));
    expect(ringFingerprint([...ring, ring[0]])).toBe(ringFingerprint(ring));
  });
  it("a shell that kept its id but changed shape drops the stored nodes and re-seeds", () => {
    const ring = squareRing();
    const stored = { shell: nodesOf(ring), holes: [], fp: { shell: ringFingerprint(ring), holes: [] } };
    expect(nodesForShape({ nodes: stored }, ring, []).stored).toBe(true);
    const longer = squareRing(20, 8);                         // indices still in range, ring is not the one they were made on
    const got = nodesForShape({ nodes: stored }, longer, []);
    expect(got.stored).toBe(false);
    expect(got.shell).toEqual(seedNodes(longer));
  });
  it("a hole whose length changed under the same hole count re-seeds every ring", () => {
    const shell = squareRing(), hole = squareRing(5, 4);
    const stored = { shell: nodesOf(shell), holes: [nodesOf(hole)], fp: { shell: ringFingerprint(shell), holes: [ringFingerprint(hole)] } };
    expect(nodesForShape({ nodes: stored }, shell, [hole]).stored).toBe(true);
    const grown = squareRing(5, 8);
    const got = nodesForShape({ nodes: stored }, shell, [grown]);
    expect(got.stored).toBe(false);
    expect(got.holes).toEqual([seedNodes(grown)]);
  });
  it("a commit writes the fingerprint of the rings it wrote", () => {
    const outlineFull = squareRing();
    const rows = [{ id: "a", outlineFull, holesFull: [] }];
    const basis = { rows, bboxMm: { x0: -20, y0: -20, x1: 20, y1: 20 }, rotationDeg: 0, nodesById: new Map([["a", seedNodes(outlineFull.map(([x, y]) => [x, -y]))]]) };
    const field = outlineFull.map(([x, y]) => [x, -y]).map(([x, y], i) => (i === 0 ? [x - 1, y] : [x, y]));
    const res = ringEditOverrides({ shapeOverrides: {} }, basis, new Map([["a", field]]), null, new Map([["a", basis.nodesById.get("a")]]));
    expect(res.cur.a.nodes.fp.shell).toBe(ringFingerprint(res.cur.a.boundary_override));
    expect(res.cur.a.nodes.fp.holes).toEqual([]);
  });
});

describe("click dead zone", () => {
  it("under the threshold is a click, at or past it is a drag", () => {
    expect(pastClickDeadZone({ x: 10, y: 10 }, { x: 11, y: 10 }, 4)).toBe(false);
    expect(pastClickDeadZone({ x: 10, y: 10 }, { x: 12, y: 12 }, 4)).toBe(false);
    expect(pastClickDeadZone({ x: 10, y: 10 }, { x: 14, y: 10 }, 4)).toBe(true);
  });
});
