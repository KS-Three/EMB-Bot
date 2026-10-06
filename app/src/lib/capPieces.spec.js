import { describe, it, expect } from "vitest";
import { isCapPieceId, capPieceSpans, capOutlinesMm, capPieceRgb, capPieceRow } from "./capPieces.js";
import { popoverModel, popoverPatch } from "./shapePopover.js";
import { hitOverlay, hitShapeInterior } from "./shapeOverlay.js";

const st = (x, y, type = "stitch") => ({ x, y, type });

// Two cap stretches (blocks 1 and 2) after one shape's fill (block 0).
function result() {
  return {
    colors: [{ r: 10, g: 10, b: 10 }, { r: 255, g: 170, b: 51 }, { r: 142, g: 71, b: 173 }],
    stitches: [
      st(0, 0), st(100, 0),
      st(0, 0), st(50, 0), st(100, 0), st(100, 0, "jump"),
      st(100, 0), st(100, 50), st(100, 100),
    ],
    runs: [
      { i0: 0, i1: 1, kind: "fill", shape: "A", role: "", block: 0 },
      { i0: 2, i1: 4, kind: "run", shape: "__edge_cap__", role: "edge_cap", block: 1, piece: "cap:5:0" },
      { i0: 5, i1: 5, kind: "travel", shape: "__edge_cap__", role: "edge_cap", block: 1 },
      { i0: 6, i1: 8, kind: "run", shape: "__edge_cap__", role: "edge_cap", block: 2, piece: "cap:10:5" },
    ],
  };
}
const element = (extra = {}) => ({
  type: "digitized", result: result(), deletedShapeIds: [], shapeOverrides: {},
  review: { shapes: [{ id: "A" }] }, appliedEdits: null, ...extra,
});

describe("capPieces", () => {
  it("recognises cap ids", () => {
    expect(isCapPieceId("cap:1:2")).toBe(true);
    expect(isCapPieceId("S4ed77037")).toBe(false);
    expect(isCapPieceId(null)).toBe(false);
  });

  it("lists the cap's stretches in sew order and skips its travel", () => {
    expect(capPieceSpans(result()).map((s) => [s.id, s.block])).toEqual([["cap:5:0", 1], ["cap:10:5", 2]]);
  });

  it("builds open polylines in field mm from the built stitches", () => {
    const out = capOutlinesMm(element(), { stitches: result().stitches });
    expect(out).toHaveLength(2);
    expect(out[0]).toMatchObject({ id: "cap:5:0", open: true });
    expect(out[0].points).toEqual([[0, 0], [5, 0], [10, 0]]);
    expect(out[1].points).toEqual([[10, 0], [10, 5], [10, 10]]);
  });

  it("reads a stretch's colour off its block, and an override over that", () => {
    expect(capPieceRgb(element(), "cap:10:5")).toEqual([142, 71, 173]);
    expect(capPieceRow(element({ shapeOverrides: { "cap:10:5": { rgb: [1, 2, 3] } } }), "cap:10:5").rgb).toEqual([1, 2, 3]);
    expect(capPieceRow(element(), "cap:9:9")).toBeNull();
  });
});

describe("the popover for a cap stretch", () => {
  it("offers a colour and a delete, and nothing about tiers or borders", () => {
    const m = popoverModel({ element: element(), shapeId: "cap:5:0" });
    expect(m.name).toBe("Edge stitch");
    expect(m.rows.map((r) => r.key)).toEqual(["color", "delete"]);
    expect(m.rows[0].rgb).toEqual([255, 170, 51]);
  });

  it("deletes through deletedShapeIds like any shape", () => {
    expect(popoverPatch({ element: element(), shapeId: "cap:5:0" }, "delete"))
      .toEqual({ deletedShapeIds: ["cap:5:0"] });
  });

  it("is gone once deleted", () => {
    expect(popoverModel({ element: element({ deletedShapeIds: ["cap:5:0"] }), shapeId: "cap:5:0" })).toBeNull();
  });
});

describe("hit-testing an open polyline", () => {
  const line = { id: "cap:1:1", open: true, points: [[0, 0], [100, 0]] };

  it("hits along the line but never from its closing edge", () => {
    expect(hitOverlay([line], 50, 3)).toMatchObject({ shapeId: "cap:1:1", kind: "edge" });
    // A ring would close (100,0)->(0,0) and hit here; an open line has no such edge.
    const bent = { id: "cap:2:2", open: true, points: [[0, 0], [100, 0], [100, 100]] };
    expect(hitOverlay([bent], 50, 50)).toBeNull();
  });

  it("offers no nodes to grab", () => {
    expect(hitOverlay([line], 0, 0).kind).toBe("edge");
  });

  it("is never 'inside' anything", () => {
    const loop = { id: "cap:3:3", open: true, points: [[0, 0], [100, 0], [100, 100], [0, 100]] };
    expect(hitShapeInterior([loop], 50, 50)).toBeNull();
  });
});
