import { test, expect } from "vitest";
import { serialize, deserialize } from "./save.js";
import { defaultProject, updateElement } from "./project.js";

test("round-trips a v2 project", () => {
  const p = updateElement(defaultProject(), "e1", { text: "Team", fontKey: "manga_impact", colorRgb: [200, 0, 0] });
  const back = deserialize(serialize(p));
  expect(back.elements[0]).toMatchObject({ text: "Team", fontKey: "manga_impact", colorRgb: [200, 0, 0] });
});

test("bad input falls back to defaults", () => {
  expect(deserialize("not json")).toEqual(defaultProject());
});

test("deserialize migrates a v1 JSON string into a v2 project", () => {
  const v1 = {
    garmentId: "hat_front",
    text: "Crew",
    fontKey: "geneva_simple",
    sizeMm: null,
    offsetXMm: 0,
    offsetYMm: 0,
    colorRgb: [20, 20, 20],
    underlay: true,
    mode: "text",
    nColors: 4,
    removeBg: true,
    letterSpacingMm: 0,
  };
  const p = deserialize(JSON.stringify(v1));
  expect(p.version).toBe(2);
  expect(p.garmentId).toBe("hat_front");
  expect(p.elements).toHaveLength(1);
  expect(p.elements[0].type).toBe("text");
  expect(p.elements[0].text).toBe("Crew");
});

test("deserialize of unparseable input still falls back to defaultProject()", () => {
  expect(deserialize("{not valid json")).toEqual(defaultProject());
  expect(deserialize(JSON.stringify(42))).toEqual(defaultProject());
});
