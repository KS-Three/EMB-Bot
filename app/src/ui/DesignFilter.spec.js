// @vitest-environment jsdom
import { expect, test, vi } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./DesignFilter.testHarness.svelte";

const HOOPS = [
  { id: "4x4", label: "4×4 in", widthMm: 100, heightMm: 100 },
  { id: "5x7", label: "5×7 in", widthMm: 130, heightMm: 180 },
];

const last = (fn) => fn.mock.calls[fn.mock.calls.length - 1][0];

test("starts with no criteria and no Clear button", () => {
  const onCriteria = vi.fn();
  render(Harness, { hoops: HOOPS, onCriteria });
  expect(last(onCriteria)).toEqual({ text: "", maxStitches: null, maxColors: null, hoop: null });
  expect(screen.queryByRole("button", { name: "Clear filters" })).toBeNull();
});

test("hands out the criteria filterProjects takes: numbers and the hoop object", async () => {
  const onCriteria = vi.fn();
  render(Harness, { hoops: HOOPS, onCriteria });
  await fireEvent.input(screen.getByLabelText("Find a design"), { target: { value: "dog" } });
  await fireEvent.change(screen.getByLabelText("Stitches"), { target: { value: "6000" } });
  await fireEvent.change(screen.getByLabelText("Colors"), { target: { value: "2" } });
  await fireEvent.change(screen.getByLabelText("Fits hoop"), { target: { value: "4x4" } });
  expect(last(onCriteria)).toEqual({ text: "dog", maxStitches: 6000, maxColors: 2, hoop: HOOPS[0] });
});

test("offers every hoop preset it is given, by label", () => {
  render(Harness, { hoops: HOOPS });
  const options = Array.from(screen.getByLabelText("Fits hoop").options).map((o) => o.textContent);
  expect(options).toEqual(["Any", "4×4 in", "5×7 in"]);
});

test("Clear filters resets all four and removes itself", async () => {
  const onCriteria = vi.fn();
  render(Harness, { hoops: HOOPS, onCriteria });
  await fireEvent.change(screen.getByLabelText("Colors"), { target: { value: "2" } });
  await fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
  expect(last(onCriteria)).toEqual({ text: "", maxStitches: null, maxColors: null, hoop: null });
  expect(screen.queryByRole("button", { name: "Clear filters" })).toBeNull();
});
