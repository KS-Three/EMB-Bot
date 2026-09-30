// @vitest-environment jsdom
import { test, expect, beforeEach, afterEach, vi } from "vitest";
import { tip, tipElement, hideTip, SHOW_DELAY_MS } from "./tip.js";
import { HELP } from "./settingHelp.js";

let host;
let action;

beforeEach(() => {
  vi.useFakeTimers();
  host = document.createElement("button");
  host.textContent = "Fill angle";
  document.body.appendChild(host);
});

afterEach(() => {
  if (action) action.destroy();
  action = null;
  hideTip();
  host.remove();
  vi.useRealTimers();
});

function ev(type) {
  return new Event(type, { bubbles: true });
}

test("hover shows the three sentences after the delay, in one shared tooltip element", () => {
  action = tip(host, "fillAngle");
  host.dispatchEvent(ev("pointerenter"));
  // Not yet: a pass-over must not flash.
  expect(tipElement() == null || tipElement().hidden).toBe(true);
  vi.advanceTimersByTime(SHOW_DELAY_MS);
  const el = tipElement();
  expect(el.hidden).toBe(false);
  expect(el.getAttribute("role")).toBe("tooltip");
  expect(el.querySelector(".tipbox-title").textContent).toBe(HELP.fillAngle.title);
  const lines = [...el.querySelectorAll(".tipbox-line")].map((p) => p.textContent);
  expect(lines[0]).toBe(HELP.fillAngle.what);
  expect(lines[1]).toBe("Changes: " + HELP.fillAngle.changes);
  expect(lines[2]).toBe("When: " + HELP.fillAngle.when);
  // And the host is described by it, for a screen reader.
  expect(host.getAttribute("aria-describedby")).toBe(el.id);

  host.dispatchEvent(ev("pointerleave"));
  expect(el.hidden).toBe(true);
  expect(host.hasAttribute("aria-describedby")).toBe(false);
});

test("leaving before the delay cancels the show", () => {
  action = tip(host, "fillAngle");
  host.dispatchEvent(ev("pointerenter"));
  host.dispatchEvent(ev("pointerleave"));
  vi.advanceTimersByTime(SHOW_DELAY_MS * 2);
  expect(tipElement() == null || tipElement().hidden).toBe(true);
});

test("keyboard focus shows at once; Escape and blur hide", () => {
  action = tip(host, "border");
  host.dispatchEvent(ev("focusin"));
  expect(tipElement().hidden).toBe(false);
  expect(tipElement().querySelector(".tipbox-title").textContent).toBe("Border");
  host.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true }));
  expect(tipElement().hidden).toBe(true);
  host.dispatchEvent(ev("focusin"));
  expect(tipElement().hidden).toBe(false);
  host.dispatchEvent(ev("focusout"));
  expect(tipElement().hidden).toBe(true);
});

test("a second host takes the same element over, and the first stops being described", () => {
  action = tip(host, "jumps");
  const other = document.createElement("button");
  document.body.appendChild(other);
  const action2 = tip(other, "trims");
  host.dispatchEvent(ev("focusin"));
  expect(tipElement().querySelector(".tipbox-title").textContent).toBe("Jumps");
  other.dispatchEvent(ev("focusin"));
  expect(tipElement().querySelector(".tipbox-title").textContent).toBe("Trims");
  expect(host.hasAttribute("aria-describedby")).toBe(false);
  expect(other.getAttribute("aria-describedby")).toBe(tipElement().id);
  action2.destroy();
  other.remove();
});

test("an unknown key attaches nothing and does not throw; update swaps the copy", () => {
  action = tip(host, "not-a-key");
  host.dispatchEvent(ev("focusin"));
  expect(tipElement() == null || tipElement().hidden).toBe(true);
  action.update("curve");
  host.dispatchEvent(ev("focusin"));
  expect(tipElement().querySelector(".tipbox-title").textContent).toBe("Curve");
});

test("destroy removes the listeners and closes a tip it owns", () => {
  action = tip(host, "rotation");
  host.dispatchEvent(ev("focusin"));
  expect(tipElement().hidden).toBe(false);
  action.destroy();
  action = null;
  expect(tipElement().hidden).toBe(true);
  host.dispatchEvent(ev("focusin"));
  expect(tipElement().hidden).toBe(true);
});
