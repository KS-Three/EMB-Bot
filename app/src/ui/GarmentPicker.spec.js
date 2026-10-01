// @vitest-environment jsdom
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent, screen, within } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";

let Harness;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  // lib/emb.js refuses to load without EMB.buildLetteringDesign; stub it.
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  ({ default: Harness } = await import("./GarmentPicker.testHarness.svelte"));
});

test("shows Polo, Hat, Tee and More, with the garment in force pressed", () => {
  render(Harness, { garmentId: "hat_front" });
  const group = screen.getByRole("group", { name: "Garment" });
  expect(within(group).getByRole("button", { name: "Polo" })).toHaveAttribute("aria-pressed", "false");
  expect(within(group).getByRole("button", { name: "Hat" })).toHaveAttribute("aria-pressed", "true");
  expect(within(group).getByRole("button", { name: "Tee" })).toBeInTheDocument();
  expect(within(group).getByRole("button", { name: "More garments" })).toBeInTheDocument();
});

test("clicking a pill dispatches update with its garment id", async () => {
  const onUpdate = vi.fn();
  render(Harness, { garmentId: "left_chest", onUpdate });
  await fireEvent.click(screen.getByRole("button", { name: "Tee" }));
  expect(onUpdate.mock.calls[0][0].detail).toEqual({ garmentId: "full_back" });
});

test("a garment outside the three appears as a fourth pressed pill", () => {
  render(Harness, { garmentId: "tote" });
  expect(screen.getByRole("button", { name: "Tote" })).toHaveAttribute("aria-pressed", "true");
});

test("More opens a menu of all ten garments, the current one checked", async () => {
  render(Harness, { garmentId: "tote" });
  expect(screen.queryByRole("menu")).toBeNull();
  await fireEvent.click(screen.getByRole("button", { name: "More garments" }));
  const menu = screen.getByRole("menu", { name: "All garments" });
  expect(within(menu).getAllByRole("menuitemradio").length).toBe(10);
  expect(within(menu).getByRole("menuitemradio", { name: "Tote" })).toHaveAttribute("aria-checked", "true");
  expect(within(menu).getByRole("menuitemradio", { name: "Left Chest" })).toHaveAttribute("aria-checked", "false");
});

test("picking from the menu dispatches update and closes it", async () => {
  const onUpdate = vi.fn();
  render(Harness, { garmentId: "left_chest", onUpdate });
  await fireEvent.click(screen.getByRole("button", { name: "More garments" }));
  await fireEvent.click(screen.getByRole("menuitemradio", { name: "Beanie" }));
  expect(onUpdate.mock.calls[0][0].detail).toEqual({ garmentId: "beanie" });
  expect(screen.queryByRole("menu")).toBeNull();
});

test("Escape closes the menu and returns focus to More", async () => {
  render(Harness, { garmentId: "left_chest" });
  const more = screen.getByRole("button", { name: "More garments" });
  await fireEvent.click(more);
  await fireEvent.keyDown(screen.getByRole("menu"), { key: "Escape" });
  expect(screen.queryByRole("menu")).toBeNull();
  expect(document.activeElement).toBe(more);
});

test("focus leaving the picker closes the menu", async () => {
  render(Harness, { garmentId: "left_chest" });
  await fireEvent.click(screen.getByRole("button", { name: "More garments" }));
  const item = screen.getByRole("menuitemradio", { name: "Beanie" });
  await fireEvent.focusOut(item, { relatedTarget: document.body });
  expect(screen.queryByRole("menu")).toBeNull();
});

test("focus moving between menu items keeps the menu open", async () => {
  render(Harness, { garmentId: "left_chest" });
  await fireEvent.click(screen.getByRole("button", { name: "More garments" }));
  const from = screen.getByRole("menuitemradio", { name: "Beanie" });
  const to = screen.getByRole("menuitemradio", { name: "Tote" });
  await fireEvent.focusOut(from, { relatedTarget: to });
  expect(screen.getByRole("menu", { name: "All garments" })).toBeInTheDocument();
});
