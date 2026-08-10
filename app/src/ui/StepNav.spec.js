// @vitest-environment jsdom
//
// Component-level coverage for StepNav.svelte (bottom sidebar step nav) --
// goto/back/next event dispatch, disabled-step click being a no-op,
// aria-current on the active step, and the per-step progress badge (number
// vs. checkmark) driven by step position. The visual-only parts of this PR
// (active/hover colors, badge circle styling, the 820px breakpoint) aren't
// meaningfully unit-testable and are flagged for manual/Playwright
// verification instead -- same treatment DigitizePanel's SVG editor already
// gets in this repo (see DigitizePanel.spec.js).
import { describe, expect, test } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import StepNavHarness from "./StepNav.testHarness.svelte";
import { STEPS } from "../lib/flow.js";
import { defaultProject, updateElement } from "../lib/project.js";

// garment step always clickable once garmentId is set (defaultProject's
// default), content always advances, so a project with non-empty text on
// e1 makes every step reachable -- used where the test wants all four tabs
// enabled regardless of which one is "current".
function readyProject() {
  return updateElement(defaultProject(), "e1", { text: "Hi" });
}

function renderNav(props = {}) {
  const gotos = [];
  const backs = [];
  const nexts = [];
  const utils = render(StepNavHarness, {
    props: {
      step: "garment",
      project: defaultProject(),
      canNext: true,
      onGoto: (s) => gotos.push(s),
      onBack: () => backs.push(true),
      onNext: () => nexts.push(true),
      ...props,
    },
  });
  return { ...utils, gotos, backs, nexts };
}

function stepButtons(utils) {
  return utils.container.querySelectorAll(".stepnav-step");
}

// The passed-step badge now renders an Icon (svg, no text node) instead of a
// literal "✓" character -- resolve a badge to either the sentinel "check"
// (an Icon name="check" is present) or its plain 1-based-number text, so
// tests can assert on badge identity the same way regardless of which one a
// given step shows.
function badgeContent(button) {
  const badge = button.querySelector(".stepnav-badge");
  return badge.querySelector('[data-icon="check"]') ? "check" : badge.textContent.trim();
}

describe("step tabs", () => {
  test("renders one button per STEPS entry, in order, with the expected labels", () => {
    const utils = renderNav();
    const buttons = stepButtons(utils);
    expect(buttons).toHaveLength(STEPS.length);
    const labels = [...buttons].map((b) => b.querySelector(".stepnav-label").textContent);
    expect(labels).toEqual(["Garment", "Content", "Review", "Download"]);
  });

  test("clicking a reachable, non-current step dispatches goto with that step's id", async () => {
    // content is always reachable (canAdvance("content") is unconditionally
    // true), so from "garment" it's clickable without any project setup.
    const utils = renderNav({ step: "garment", project: defaultProject() });
    const buttons = stepButtons(utils);
    await fireEvent.click(buttons[1]); // "content"
    expect(utils.gotos).toEqual(["content"]);
  });

  test("clicking a disabled (not-yet-reachable) step is a no-op -- no goto dispatched", async () => {
    // defaultProject() has empty text, so canAdvance("create") is false --
    // maxReachableIndex walks garment -> content -> create (you're always
    // allowed ONTO the first not-yet-satisfied step to see what it needs),
    // then stops, so "download" (one step further, gated on "create" itself
    // passing) is the one that's actually disabled here.
    const utils = renderNav({ step: "content", project: defaultProject() });
    const buttons = stepButtons(utils);
    const downloadBtn = buttons[3];
    expect(downloadBtn).toBeDisabled();
    await fireEvent.click(downloadBtn);
    expect(utils.gotos).toEqual([]);
  });

  test("clicking a step already behind the current one is always allowed, even with no gates satisfied", async () => {
    const utils = renderNav({ step: "content", project: defaultProject() });
    const buttons = stepButtons(utils);
    await fireEvent.click(buttons[0]); // "garment", behind "content"
    expect(utils.gotos).toEqual(["garment"]);
  });

  test("aria-current=\"step\" is set on the active step only", () => {
    const utils = renderNav({ step: "content", project: readyProject() });
    const buttons = [...stepButtons(utils)];
    expect(buttons[1].getAttribute("aria-current")).toBe("step");
    expect(buttons[0].getAttribute("aria-current")).toBeNull();
    expect(buttons[2].getAttribute("aria-current")).toBeNull();
    expect(buttons[3].getAttribute("aria-current")).toBeNull();
  });
});

describe("progress badges", () => {
  test("a step behind the current one shows a checkmark icon (aria-hidden) instead of its number", () => {
    const utils = renderNav({ step: "create", project: readyProject() });
    const buttons = [...stepButtons(utils)];
    const garmentBadge = buttons[0].querySelector(".stepnav-badge");
    const checkIcon = garmentBadge.querySelector('[data-icon="check"]');
    expect(checkIcon).not.toBeNull();
    expect(checkIcon.getAttribute("aria-hidden")).toBe("true");
    expect(garmentBadge).toHaveClass("done");
  });

  test("the current step and every step ahead of it show their 1-based number, not a checkmark", () => {
    const utils = renderNav({ step: "content", project: readyProject() });
    const buttons = [...stepButtons(utils)];
    expect(buttons.map(badgeContent)).toEqual(["check", "2", "3", "4"]);
    // Only the truly-passed step (index 0, behind "content") gets the
    // "done" badge styling hook; the current step and steps ahead don't.
    expect(buttons[1].querySelector(".stepnav-badge")).not.toHaveClass("done");
    expect(buttons[2].querySelector(".stepnav-badge")).not.toHaveClass("done");
    expect(buttons[3].querySelector(".stepnav-badge")).not.toHaveClass("done");
  });

  test("on the very first step, no badge is a checkmark yet", () => {
    const utils = renderNav({ step: "garment", project: defaultProject() });
    const buttons = [...stepButtons(utils)];
    expect(buttons.map(badgeContent)).toEqual(["1", "2", "3", "4"]);
  });
});

// Each of these renders exactly once (testing-library appends every render
// to the shared document.body with no auto-cleanup between renders WITHIN
// a single test, so re-rendering here would make an unscoped getByRole
// match multiple buttons across renders -- one render per test avoids that,
// matching the convention this repo's other component specs already use).
describe("Back / Next controls", () => {
  test("Back is disabled on the first step", () => {
    const utils = renderNav({ step: "garment", project: defaultProject() });
    expect(utils.getByRole("button", { name: "Back" })).toBeDisabled();
  });

  test("Back dispatches back when enabled", async () => {
    const utils = renderNav({ step: "content", project: defaultProject() });
    const backBtn = utils.getByRole("button", { name: "Back" });
    expect(backBtn).not.toBeDisabled();
    await fireEvent.click(backBtn);
    expect(utils.backs).toEqual([true]);
  });

  test("Next is disabled when canNext is false", () => {
    const utils = renderNav({ step: "content", project: defaultProject(), canNext: false });
    expect(utils.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  test("Next is disabled on the last step even when canNext is true", () => {
    const utils = renderNav({ step: "download", project: readyProject(), canNext: true });
    expect(utils.getByRole("button", { name: "Next" })).toBeDisabled();
  });

  test("Next dispatches next when enabled", async () => {
    const utils = renderNav({ step: "content", project: readyProject(), canNext: true });
    const nextBtn = utils.getByRole("button", { name: "Next" });
    expect(nextBtn).not.toBeDisabled();
    await fireEvent.click(nextBtn);
    expect(utils.nexts).toEqual([true]);
  });
});
