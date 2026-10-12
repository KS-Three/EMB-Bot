// @vitest-environment jsdom
//
// The progressive-disclosure toggle (spec 2026-09-30 §2.2/§5): closed on
// first render, opens and closes on click, and remembers what the customer
// chose for the rest of the session -- across the panel being torn down and
// rebuilt when another element is selected. The state is NOT persisted.
import { beforeEach, expect, test } from "vitest";
import { render, fireEvent, screen, cleanup } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./Advanced.testHarness.svelte";
import { resetAdvanced } from "../lib/advanced.js";

beforeEach(() => { cleanup(); resetAdvanced(); });

test("first render: closed, content not visible, nothing deleted from the DOM", () => {
  render(Harness);
  const toggle = screen.getByRole("button", { name: /^Advanced/ });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(screen.getByTestId("adv-content")).not.toBeVisible();
});

test("opens and closes on click", async () => {
  render(Harness);
  const toggle = screen.getByTestId("advanced-toggle");
  await fireEvent.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByTestId("adv-content")).toBeVisible();
  await fireEvent.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(screen.getByTestId("adv-content")).not.toBeVisible();
});

test("remembers its state when the panel is rebuilt (session, in memory)", async () => {
  const first = render(Harness);
  await fireEvent.click(screen.getByTestId("advanced-toggle"));
  first.unmount();
  render(Harness);
  expect(screen.getByTestId("advanced-toggle")).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByTestId("adv-content")).toBeVisible();
});

test("is not written to browser storage", async () => {
  render(Harness);
  await fireEvent.click(screen.getByTestId("advanced-toggle"));
  expect(JSON.stringify({ ...localStorage })).not.toMatch(/advanced/i);
  expect(JSON.stringify({ ...sessionStorage })).not.toMatch(/advanced/i);
});

test("the toggle controls the body it names", () => {
  render(Harness);
  const toggle = screen.getByTestId("advanced-toggle");
  const body = screen.getByTestId("advanced-body");
  expect(toggle.getAttribute("aria-controls")).toBe(body.id);
});
