// @vitest-environment jsdom
import { expect, test, vi } from "vitest";
import { render, fireEvent, screen } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./Configurator.testHarness.svelte";

test("renders the title, subtitle and both slots in order", () => {
  render(Harness, { subtitle: "Tote · 8×8 in" });
  expect(screen.getByRole("heading", { name: "Your design" })).toBeInTheDocument();
  expect(screen.getByText("Tote · 8×8 in")).toBeInTheDocument();
  const design = screen.getByTestId("design-slot");
  const garment = screen.getByTestId("garment-slot");
  expect(design.compareDocumentPosition(garment) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
});

test("the start control dispatches addelement with text or artwork", async () => {
  const onAdd = vi.fn();
  render(Harness, { onAdd });
  await fireEvent.click(screen.getByRole("button", { name: "Add text" }));
  await fireEvent.click(screen.getByRole("button", { name: "Upload file" }));
  expect(onAdd.mock.calls.map((c) => c[0].detail)).toEqual(["text", "artwork"]);
});

test("forwards the bar's download event", async () => {
  const onDownload = vi.fn();
  render(Harness, { canDownload: true, onDownload });
  await fireEvent.click(screen.getByRole("button", { name: "Download" }));
  expect(onDownload).toHaveBeenCalledTimes(1);
});

test("never renders a step number or a Next button", () => {
  render(Harness);
  expect(screen.queryByRole("button", { name: /^Next$/ })).toBeNull();
  expect(screen.queryByText(/^\d Garment|^\d Content|^\d Review|^\d Download/)).toBeNull();
});
