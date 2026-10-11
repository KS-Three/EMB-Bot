import { describe, it, expect } from "vitest";
import { pruneDeletedShapes, pendingDeletedIds, displayResult, decodedFromDesign } from "./digitizer.js";

// Three runs over eight stitches: shape A (0-2), shape B (3-5, with a blend
// suffix on its second run id), and the edge cap (6-7).
function design() {
  const st = (x, y, type = "stitch") => ({ x, y, type });
  return {
    name: "t",
    colors: [{ r: 1, g: 1, b: 1 }],
    stitches: [st(0, 0), st(10, 0), st(20, 0), st(100, 0), st(110, 0), st(120, 0), st(0, 50), st(120, 50)],
    runs: [
      { i0: 0, i1: 2, kind: "fill", shape: "A", role: "", block: 0 },
      { i0: 3, i1: 4, kind: "fill", shape: "B-blend0", role: "", block: 0 },
      { i0: 5, i1: 5, kind: "satin", shape: "B", role: "border", block: 0 },
      { i0: 6, i1: 7, kind: "run", shape: "__edge_cap__", role: "edge_cap", block: 0 },
    ],
  };
}

describe("pruneDeletedShapes", () => {
  it("drops a shape's stitches, including its blend runs, and re-indexes the rest", () => {
    const out = pruneDeletedShapes(design(), ["B"], ["A", "B"]);
    expect(out.stitches.map((s) => s.x)).toEqual([0, 10, 20, 0, 120]);
    expect(out.runs.map((r) => [r.shape, r.i0, r.i1])).toEqual([["A", 0, 2], ["__edge_cap__", 3, 4]]);
  });

  it("leaves the edge cap alone", () => {
    const out = pruneDeletedShapes(design(), ["A", "B"], ["A", "B"]);
    expect(out.runs).toHaveLength(1);
    expect(out.runs[0].role).toBe("edge_cap");
  });

  it("takes one cap stretch by its own id and keeps the others", () => {
    const d = design();
    d.runs[3] = { i0: 6, i1: 6, kind: "run", shape: "__edge_cap__", role: "edge_cap", block: 0, piece: "cap:1:2" };
    d.runs.push({ i0: 7, i1: 7, kind: "run", shape: "__edge_cap__", role: "edge_cap", block: 0, piece: "cap:3:4" });
    const out = pruneDeletedShapes(d, ["cap:1:2"], ["A", "B"]);
    expect(out.runs.filter((r) => r.role === "edge_cap").map((r) => r.piece)).toEqual(["cap:3:4"]);
    expect(out.stitches).toHaveLength(7);
  });

  it("returns the same object when nothing matches", () => {
    const d = design();
    expect(pruneDeletedShapes(d, ["Z"], ["A", "B"])).toBe(d);
    expect(pruneDeletedShapes(d, [], ["A", "B"])).toBe(d);
  });

  it("keeps the unpruned frame, so the survivors do not re-centre", () => {
    const d = design();
    const whole = decodedFromDesign(d);
    const out = pruneDeletedShapes(d, ["B"], ["A", "B"]);
    const part = decodedFromDesign(out);
    // A's first stitch sits at the same offset from the frame centre either way.
    expect(part.stitches[0].x).toBe(whole.stitches[0].x);
    expect(part.widthMM).toBe(whole.widthMM);
  });
});

describe("pendingDeletedIds / displayResult", () => {
  it("only the deletions the result does not already carry are pending", () => {
    const el = { deletedShapeIds: ["A", "B"], appliedEdits: JSON.stringify([["A"], {}, [], {}]) };
    expect(pendingDeletedIds(el)).toEqual(["B"]);
  });

  it("with no applied record every deletion is pending", () => {
    expect(pendingDeletedIds({ deletedShapeIds: ["A"], appliedEdits: null })).toEqual(["A"]);
  });

  it("displayResult prunes a pending deletion and is cached per result", () => {
    const result = design();
    const el = { result, deletedShapeIds: ["B"], appliedEdits: null, review: { shapes: [{ id: "A" }, { id: "B" }] } };
    const a = displayResult(el);
    expect(a.stitches).toHaveLength(5);
    expect(displayResult(el)).toBe(a);
    expect(displayResult({ ...el, deletedShapeIds: [] })).toBe(result);
  });
});
