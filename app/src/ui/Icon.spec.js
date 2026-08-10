// @vitest-environment jsdom
//
// Component-level coverage for Icon.svelte (UI Icon System Foundation) --
// the shared inline-SVG icon renderer replacing raw Unicode/emoji glyphs
// across the app. Pure presentational component, no engine/store
// dependency, so unlike most other specs in this directory it's rendered
// directly with no test harness needed.
import { describe, expect, test } from "vitest";
import { render } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Icon from "./Icon.svelte";

function svgOf(utils) {
  return utils.container.querySelector("svg");
}

describe("known icon names", () => {
  test("renders a 24x24-viewBox svg carrying the requested icon's own markup", () => {
    const utils = render(Icon, { props: { name: "undo" } });
    const svg = svgOf(utils);
    expect(svg).toBeInTheDocument();
    expect(svg.getAttribute("viewBox")).toBe("0 0 24 24");
    expect(svg.getAttribute("data-icon")).toBe("undo");
    // No fallback marker on a real, known name.
    expect(svg.hasAttribute("data-icon-fallback")).toBe(false);
    // Actual path data renders (not an empty shell).
    expect(svg.querySelectorAll("path, circle, line, rect").length).toBeGreaterThan(0);
  });

  test("different known names render different markup, not one generic shape", () => {
    const undo = svgOf(render(Icon, { props: { name: "undo" } }));
    const close = svgOf(render(Icon, { props: { name: "close" } }));
    expect(undo.innerHTML).not.toBe(close.innerHTML);
  });

  test("every icon in the documented inventory renders without throwing", () => {
    const names = [
      "undo", "redo", "lightbulb", "close", "minus", "plus", "expand",
      "magnet", "jump", "scissors", "play", "pause", "chevron", "check",
      "warning",
    ];
    for (const name of names) {
      const svg = svgOf(render(Icon, { props: { name } }));
      expect(svg.hasAttribute("data-icon-fallback")).toBe(false);
      expect(svg.querySelectorAll("path, circle, line, rect").length).toBeGreaterThan(0);
    }
  });
});

describe("unknown icon names", () => {
  // Rendering nothing (or throwing) for a typo'd `name` is the WORSE failure
  // mode -- an empty icon slot is easy to miss in review or in the running
  // app, whereas a visibly distinct placeholder glyph is not. The fallback
  // is a dashed rounded square -- the only dashed SHAPE (`jump`'s dashed
  // line is a straight segment, not an enclosed shape) in the whole icon
  // set, so it can't be mistaken for a real icon that just happens to
  // render at a given name.
  test("falls back to the dashed placeholder instead of crashing or rendering nothing", () => {
    expect(() => render(Icon, { props: { name: "not-a-real-icon" } })).not.toThrow();
    const svg = svgOf(render(Icon, { props: { name: "not-a-real-icon" } }));
    expect(svg).toBeInTheDocument();
    expect(svg.getAttribute("data-icon-fallback")).toBe("true");
    expect(svg.querySelector("rect")).not.toBeNull();
    expect(svg.querySelector("rect").getAttribute("stroke-dasharray")).toBeTruthy();
  });

  test("data-icon still reflects the originally-requested (bad) name, for debugging", () => {
    const svg = svgOf(render(Icon, { props: { name: "totally-bogus" } }));
    expect(svg.getAttribute("data-icon")).toBe("totally-bogus");
  });
});

describe("size and class pass-through", () => {
  test("size sets both width and height (defaults to 18 when omitted)", () => {
    const withDefault = svgOf(render(Icon, { props: { name: "close" } }));
    expect(withDefault.getAttribute("width")).toBe("18");
    expect(withDefault.getAttribute("height")).toBe("18");

    const withSize = svgOf(render(Icon, { props: { name: "close", size: 24 } }));
    expect(withSize.getAttribute("width")).toBe("24");
    expect(withSize.getAttribute("height")).toBe("24");
  });

  test("class passes through onto the root svg", () => {
    const svg = svgOf(render(Icon, { props: { name: "close", class: "my-icon-class" } }));
    expect(svg).toHaveClass("my-icon-class");
  });

  test("aria-hidden defaults to true (decorative) but can be overridden by the caller", () => {
    const defaulted = svgOf(render(Icon, { props: { name: "close" } }));
    expect(defaulted.getAttribute("aria-hidden")).toBe("true");

    const overridden = svgOf(
      render(Icon, { props: { name: "close", "aria-hidden": "false" } })
    );
    expect(overridden.getAttribute("aria-hidden")).toBe("false");
  });

  test("stroke/fill defaults match the shared visual language (currentColor, 1.75px, round caps)", () => {
    const svg = svgOf(render(Icon, { props: { name: "close" } }));
    expect(svg.getAttribute("stroke")).toBe("currentColor");
    expect(svg.getAttribute("fill")).toBe("none");
    expect(svg.getAttribute("stroke-width")).toBe("1.75");
    expect(svg.getAttribute("stroke-linecap")).toBe("round");
    expect(svg.getAttribute("stroke-linejoin")).toBe("round");
  });
});
