// @vitest-environment jsdom
//
// The drawer's filter, driven through the real component: the rows it lists,
// the count line, and what happens to a filter when its controls go away.
import { beforeAll, expect, test } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";

// The drawer imports "../lib/emb.js" at module load, and emb.js throws unless
// the engine global already exists — so the REAL units/garments modules load
// first (the hoop options and the fit rule are the engine's own), the
// buildLetteringDesign gate gets a stub, and the drawer is imported
// dynamically after. Same ordering GarmentStep.spec.js documents.
let ProjectsDrawer;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  ({ default: ProjectsDrawer } = await import("./ProjectsDrawer.svelte"));
});

const rowNames = (container) =>
  Array.from(container.querySelectorAll(".drawer-row-name")).map((n) => n.textContent);

const DOG = { id: "a", name: "Dog patch", updatedAt: 2, facts: { st: 5200, col: 2, w: 90, h: 80 } };
const CAT = { id: "b", name: "Cat patch", updatedAt: 1, facts: { st: 9000, col: 4, w: 120, h: 160 } };

test("the name filter narrows the rows and says how many of how many", async () => {
  const { container } = render(ProjectsDrawer, { projects: [DOG, CAT], currentId: "a" });
  expect(rowNames(container)).toEqual(["Dog patch", "Cat patch"]);
  await fireEvent.input(screen.getByLabelText("Find a design"), { target: { value: "dog" } });
  expect(rowNames(container)).toEqual(["Dog patch"]);
  expect(screen.getByRole("status")).toHaveTextContent("1 of 2 designs");
});

// The filter controls only show with two or more saved designs. Deleting down
// to one removes the controls, and a filter nobody can see or clear must not
// keep hiding the design that is left.
test("a filter does not outlive its controls: the last design is listed once the filter is gone", async () => {
  const { container, rerender } = render(ProjectsDrawer, { projects: [DOG, CAT], currentId: "a" });
  await fireEvent.input(screen.getByLabelText("Find a design"), { target: { value: "dog" } });
  expect(rowNames(container)).toEqual(["Dog patch"]);

  await rerender({ projects: [CAT], currentId: "b" });
  expect(screen.queryByLabelText("Find a design")).toBeNull();
  expect(rowNames(container)).toEqual(["Cat patch"]);
  expect(screen.queryByText("No saved design matches.")).toBeNull();
});

test("the same holds for a stitch filter, and no not-measured line is left behind", async () => {
  const unmeasured = { id: "c", name: "Old logo", updatedAt: 1 };
  const { container, rerender } = render(ProjectsDrawer, { projects: [DOG, unmeasured], currentId: "a" });
  await fireEvent.change(screen.getByLabelText("Stitches"), { target: { value: "6000" } });
  expect(rowNames(container)).toEqual(["Dog patch"]);
  expect(screen.getByText(/1 design isn't measured yet/)).toBeInTheDocument();

  await rerender({ projects: [unmeasured], currentId: "c" });
  expect(rowNames(container)).toEqual(["Old logo"]);
  expect(screen.queryByText(/isn't measured yet/)).toBeNull();
});
