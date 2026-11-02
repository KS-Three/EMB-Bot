// @vitest-environment jsdom
//
// The service-unreachable block (architecture review item 8, 2026-11-02):
// one actionable line with Retry and a plain "Use browser engine instead"
// choice, plus the engine label on a landed result.
import { afterEach, describe, expect, test, vi } from "vitest";
import { render, fireEvent, screen, cleanup } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import Harness from "./DigitizePanel.testHarness.svelte";
import { DEFAULT_DIGITIZE_PARAMS } from "../lib/project.js";

vi.mock("../lib/emb.js", async () => {
  const { createRequire } = await import("node:module");
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  require("../../../src/garments.js");
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  return { EMB: globalThis.EMB };
});

afterEach(() => { cleanup(); vi.useRealTimers(); });

function element(extra = {}) {
  return {
    id: "e1", type: "digitized", name: "logo.png", sourcePng: "AAAA",
    params: { ...DEFAULT_DIGITIZE_PARAMS }, result: null, warnings: [], blockColors: {},
    review: null, shapeOverrides: {}, deletedShapeIds: [], appliedEdits: null, preflight: null,
    sizeMm: null, offsetXMm: 0, offsetYMm: 0, rotationDeg: 0, ...extra,
  };
}

describe("service unreachable", () => {
  test("shows the one line with Retry and Use browser engine instead", async () => {
    const onCheckService = vi.fn();
    const onUseBrowserEngine = vi.fn();
    render(Harness, { props: { element: element(), health: null, onCheckService, onUseBrowserEngine } });
    expect(screen.getByTestId("digitizer-unreachable")).toHaveTextContent("Digitizer service not reachable; retrying…");
    await fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onCheckService).toHaveBeenCalledTimes(1);
    await fireEvent.click(screen.getByRole("button", { name: "Use browser engine instead" }));
    expect(onUseBrowserEngine).toHaveBeenCalledWith({ id: "e1" });
    // The run button stays off: nothing routes to a lane on its own.
    expect(screen.getByRole("button", { name: "Auto Digitize Image" })).toBeDisabled();
  });

  test("re-checks health on a timer while down", () => {
    vi.useFakeTimers();
    const onCheckService = vi.fn();
    render(Harness, { props: { element: element(), health: null, onCheckService } });
    vi.advanceTimersByTime(8000 * 2 + 10);
    expect(onCheckService).toHaveBeenCalledTimes(2);
  });

  test("healthy service shows neither the line nor the choice", () => {
    render(Harness, { props: { element: element(), health: { status: "ok" } } });
    expect(screen.queryByTestId("digitizer-unreachable")).toBeNull();
    expect(screen.queryByRole("button", { name: "Use browser engine instead" })).toBeNull();
  });

  test("a landed result is labelled Digitizer service", () => {
    const result = { stitchCount: 100, widthMM: 50, heightMM: 50, colorCount: 1, colors: [], stitches: [] };
    render(Harness, { props: { element: element({ result, review: { brandId: "studio", shapes: [] } }), health: { status: "ok" } } });
    expect(screen.getByTestId("engine-label")).toHaveTextContent("Digitizer service");
  });
});
