// @vitest-environment jsdom
//
// Thread chips drawn as satin strands. What is pinned:
//  - the chip's mean colour stays within dE00 3.0 of the thread (20 chart
//    threads, both chip sizes, plus the whole Studio chart and the extremes);
//  - the chip's BOX does not move: the inline style carries colour and custom
//    properties only, and the theme rule sets a background-image only;
//  - the theme.css rule is the module's gradient, byte for byte;
//  - opening a 400-thread grid costs well under the 30 ms budget.
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, render, fireEvent, waitFor } from "@testing-library/svelte";
import ThreadPicker from "../ui/ThreadPicker.svelte";
import { loadPalette, STUDIO_PALETTE, PALETTE_INDEX } from "./threads.js";
import { rgbToLab, ciede2000 } from "./colorMatch.js";
import { SWATCH_BACKGROUND, swatchStyle, swatchMean, solveSwatch } from "./threadSwatch.js";

afterEach(cleanup);

const dE = (a, b) => ciede2000(rgbToLab(a), rgbToLab(b));
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
// vitest empties css imports (even ?raw), so read the file; specs run from app/.
const css = readFileSync(resolve(process.cwd(), "src/ui/theme.css"), "utf8");

async function chartThreads() {
  const out = [...STUDIO_PALETTE.threads];
  for (const p of PALETTE_INDEX) {
    if (p.id === "studio") continue;
    out.push(...(await loadPalette(p.id)).threads);
  }
  return out;
}

describe("swatch mean colour", () => {
  it("20 sampled chart threads sit within dE00 3.0, at both chip sizes", async () => {
    const all = await chartThreads();
    expect(all.length).toBeGreaterThan(400);
    const picks = [];
    for (let i = 0; i < 20; i++) picks.push(all[Math.floor((i * all.length) / 20)]);
    for (const t of picks) {
      for (const size of [20, 24]) {
        const m = swatchMean(t.rgb, size, 3);
        expect(dE(t.rgb, m), `${t.name} @${size}`).toBeLessThanOrEqual(3.0);
      }
    }
  });

  it("holds for the extremes and every Studio thread", () => {
    const extremes = [[0, 0, 0], [255, 255, 255], [255, 0, 0], [0, 255, 0], [0, 0, 255], [128, 128, 128], [250, 250, 245], [10, 10, 12]];
    for (const rgb of [...extremes, ...STUDIO_PALETTE.threads.map((t) => t.rgb)]) {
      expect(dE(rgb, swatchMean(rgb, 20, 2)), rgb.join(",")).toBeLessThanOrEqual(3.0);
    }
  });

  it("every 10th thread across all charts sits within dE00 3.0", async () => {
    const all = await chartThreads();
    let worst = 0;
    for (let i = 0; i < all.length; i += 10) worst = Math.max(worst, dE(all[i].rgb, swatchMean(all[i].rgb, 20, 2)));
    expect(worst).toBeLessThanOrEqual(3.0);
  }, 60000);

  it("shows real shading on a mid-tone thread and goes flat only where it has no headroom", () => {
    expect(solveSwatch([200, 16, 46]).k).toBeGreaterThanOrEqual(0.5);
    expect(solveSwatch([30, 90, 160]).k).toBeGreaterThanOrEqual(0.5);
    expect(solveSwatch([255, 255, 255]).k).toBeLessThanOrEqual(0.2);
  });
});

describe("chip box", () => {
  it("the inline style only carries colour and custom properties", () => {
    for (const rgb of [[0, 0, 0], [200, 16, 46], [255, 255, 255]]) {
      const decls = swatchStyle(rgb).split(";").map((d) => d.trim().split(":")[0]).filter(Boolean);
      for (const d of decls) expect(d === "background-color" || d.startsWith("--t"), d).toBe(true);
    }
  });

  it("the theme rule sets a background-image and nothing that sizes the chip", () => {
    const m = /\.tp-thread \{([^}]*)\}/.exec(css);
    expect(m).toBeTruthy();
    const props = m[1].split(";").map((d) => d.trim().split(":")[0].trim()).filter(Boolean);
    expect(props).toEqual(["background-image"]);
    expect(m[1]).toContain(SWATCH_BACKGROUND);
  });

  it("the picker renders the chips with the same classes and no layout style", async () => {
    const { container, getByRole } = render(ThreadPicker, { props: { rgb: [200, 16, 46] } });
    const sw = container.querySelector(".tp-swatch");
    expect(sw.className).toBe("tp-swatch tp-thread");
    expect(sw.getAttribute("style")).toContain("--tb");
    await fireEvent.click(getByRole("button", { name: /Thread color/ }));
    await waitFor(() => expect(container.querySelectorAll("button.tp-cell").length).toBeGreaterThan(10));
    const cells = [...container.querySelectorAll("button.tp-cell")];
    for (const c of cells.slice(0, 50)) {
      expect(c.className.startsWith("tp-cell tp-thread")).toBe(true);
      expect(c.getAttribute("style")).not.toMatch(/width|height|padding|margin|border|display/);
    }
  });

  it("compact keeps the swatch-only trigger", () => {
    const { container } = render(ThreadPicker, { props: { rgb: [30, 90, 160], compact: true } });
    expect(container.querySelector(".threadpicker.compact .tp-swatch.tp-thread")).toBeTruthy();
    expect(container.querySelector(".tp-name")).toBeNull();
  });
});

describe("cost", () => {
  it("styling 400 threads is far under the 30 ms budget", async () => {
    const all = (await chartThreads()).slice(0, 400);
    swatchStyle(all[0].rgb);
    const times = [];
    for (let r = 0; r < 15; r++) {
      const t0 = performance.now();
      for (const t of all) swatchStyle(t.rgb);
      times.push(performance.now() - t0);
    }
    times.sort((a, b) => a - b);
    expect(times[7]).toBeLessThan(10);
  });
});
