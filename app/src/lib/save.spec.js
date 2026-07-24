import { test, expect } from "vitest";
import { serialize, deserialize } from "./save.js";
import { defaultProject, update } from "./project.js";

test("round-trips a project", () => {
  const p = update(defaultProject(), { text: "Team", fontKey: "manga_impact", colorRgb: [200, 0, 0] });
  expect(deserialize(serialize(p))).toMatchObject({ text: "Team", fontKey: "manga_impact", colorRgb: [200, 0, 0] });
});

test("bad input falls back to defaults", () => {
  expect(deserialize("not json")).toMatchObject(defaultProject());
});
