// @vitest-environment jsdom
//
// A tile whose preview PNG fails to load must show a neutral placeholder, not
// the browser's broken-image glyph. Not hypothetical: build-previews skips
// writing a blank tile for a font whose letters do not stitch (it prints
// "EMPTY preview for <key>"), so the file genuinely is not there —
// infinipicto and paquerette are both in that state in the personal build,
// paquerette because only 72 of its 1,641 runs carry an authored stitch
// length and 52 of its 82 letter glyphs sew nothing.
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";

vi.mock("../lib/fontLoader.js", () => ({
  loadManifest: () => Promise.resolve({
    fonts: [
      { key: "good_font", name: "Good Font", group: "Sans" },
      { key: "no_preview", name: "No Preview", group: "Sans" },
    ],
  }),
  ensureFont: () => Promise.reject(new Error("not used by this spec")),
}));

let FontBrowser;
beforeAll(async () => {
  const require = createRequire(import.meta.url);
  require("../../../src/units.js");
  // lib/emb.js throws unless the engine global is already complete; this spec
  // never renders a live tile (that needs a font decoded into EMB.SATIN_FONTS,
  // which the mocked loader never does), so a throwing stub is enough and
  // keeps the spec from depending on the whole engine.
  globalThis.EMB.buildLetteringDesign =
    globalThis.EMB.buildLetteringDesign || (() => { throw new Error("not used by this spec"); });
  globalThis.EMB.SATIN_FONTS = globalThis.EMB.SATIN_FONTS || {};
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  ({ default: FontBrowser } = await import("./FontBrowser.svelte"));
});

const tick = () => new Promise((r) => setTimeout(r, 0));

test("a tile whose preview fails to load falls back to a placeholder", async () => {
  const { container } = render(FontBrowser, { props: { selected: null, currentText: "" } });
  await tick();

  const imgs = [...container.querySelectorAll(".fb-tile-img img")];
  expect(imgs.length, "both fonts should start with an <img> tile").toBe(2);
  const broken = imgs.find((i) => i.getAttribute("src").includes("no_preview"));
  expect(broken, "the tile for the font with no preview must exist to begin with").toBeTruthy();

  await fireEvent.error(broken);
  await tick();

  expect(container.querySelectorAll(".fb-tile-noimg").length,
    "the failed tile should render exactly one placeholder").toBe(1);
  expect([...container.querySelectorAll(".fb-tile-img img")]
    .some((i) => i.getAttribute("src").includes("no_preview")),
  "the broken <img> must be gone, not merely hidden").toBe(false);
  // The healthy tile is untouched — a per-key flag, not a global one.
  expect([...container.querySelectorAll(".fb-tile-img img")]
    .some((i) => i.getAttribute("src").includes("good_font"))).toBe(true);
});
