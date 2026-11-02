// The artwork lane decision (architecture review item 8, 2026-11-02): a down
// digitizer service no longer sends an uploaded image to the browser engine
// unannounced. Three states: healthy, down with no choice, down with the
// customer's explicit browser-engine choice.
import { describe, expect, test } from "vitest";
import {
  routeArtwork, resolveArtworkType, engineLabel, toBrowserEngineElement,
  defaultDigitizedElement, addElement, defaultProject,
} from "./project.js";

describe("routeArtwork", () => {
  test("service healthy routes to the service lane", () => {
    expect(routeArtwork({ status: "ok" })).toEqual({ type: "digitized", via: "service", unreachable: false });
    // A browser choice made earlier does not override a healthy service.
    expect(routeArtwork({ status: "ok" }, "browser").type).toBe("digitized");
  });

  test("service down with no choice routes nowhere and sets the unreachable state", () => {
    const r = routeArtwork(null);
    expect(r).toEqual({ type: "digitized", via: null, unreachable: true });
    expect(resolveArtworkType(null)).toBe("digitized");
  });

  test("explicit browser choice routes to the JS lane and marks via", () => {
    expect(routeArtwork(null, "browser")).toEqual({ type: "image", via: "browser", unreachable: false });
    expect(resolveArtworkType(null, "browser")).toBe("image");
  });

  test("adding art with the service down keeps it as a digitized element", () => {
    const p = addElement(defaultProject(), resolveArtworkType(null), 100);
    expect(p.elements.at(-1).type).toBe("digitized");
  });
});

describe("engineLabel", () => {
  test("uses the Download step's via words", () => {
    expect(engineLabel("service")).toBe("Digitizer service");
    expect(engineLabel("browser")).toBe("Browser engine");
    expect(engineLabel(null)).toBeNull();
  });
});

describe("toBrowserEngineElement", () => {
  test("keeps the artwork and marks via: browser", () => {
    const el = { ...defaultDigitizedElement("e3"), name: "logo.png", sourcePng: "AAAA" };
    const img = toBrowserEngineElement(el, 38);
    expect(img).toMatchObject({ id: "e3", type: "image", name: "logo.png", sourcePng: "AAAA", sizeMm: 38, via: "browser" });
  });
});
