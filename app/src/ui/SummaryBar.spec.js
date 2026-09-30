// @vitest-environment jsdom
import { expect, test, vi } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./SummaryBar.testHarness.svelte";

const FACTS = [
  { label: "Size", value: "76 × 18 mm" },
  { label: "Stitches", value: "3,412" },
  { label: "Run time", value: "~6 min at 650 spm" },
  { label: "Trims", value: "2" },
];

test("shows size, stitches and colours from the rows it is given", () => {
  render(Harness, { sewFacts: FACTS, colorCount: 1, canDownload: true });
  expect(screen.getByText("76 × 18 mm")).toBeInTheDocument();
  expect(screen.getByText("3,412")).toBeInTheDocument();
  expect(screen.getByText("1")).toBeInTheDocument();
  expect(screen.getByText(/colou?r$/)).toBeInTheDocument();
});

test("pluralises colours", () => {
  render(Harness, { sewFacts: FACTS, colorCount: 3, canDownload: true });
  expect(screen.getByText("colors")).toBeInTheDocument();
});

test("prints a dash for every figure when nothing sews", () => {
  render(Harness, { sewFacts: [], colorCount: 0, canDownload: false });
  const dashes = screen.getAllByText("—");
  expect(dashes.length).toBe(3);
});

test("the Download button is disabled with a reason until the design can sew", () => {
  render(Harness, { sewFacts: [], colorCount: 0, canDownload: false });
  const btn = screen.getByRole("button", { name: "Download" });
  expect(btn).toBeDisabled();
  expect(btn).toHaveAttribute("title", "Add text or a logo first");
});

test("clicking Download dispatches download", async () => {
  const onDownload = vi.fn();
  render(Harness, { sewFacts: FACTS, colorCount: 1, canDownload: true, onDownload });
  await fireEvent.click(screen.getByRole("button", { name: "Download" }));
  expect(onDownload).toHaveBeenCalledTimes(1);
});
