// @vitest-environment jsdom
//
// StarterPicker.svelte against the REAL pack (public/starter/) and the real
// DST reader: the twelve cards a customer sees, what a card says about where
// its art came from, and what picking one hands to App. The project side
// (one undo step, save/load, fit) is lib/starterPack.spec.js.
import { beforeAll, expect, test, vi } from "vitest";
import { render, fireEvent } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const PACK = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "public", "starter");
const manifest = JSON.parse(readFileSync(join(PACK, "manifest.json"), "utf8"));

let StarterPicker;
let requests;
// When set, the next .dst request fails once (a dropped connection).
let failNextDst = false;

beforeAll(async () => {
  const require = createRequire(import.meta.url);
  globalThis.window = globalThis;
  // The real engine, as emb.spec.js loads it (emb.js refuses to import without it).
  for (const f of ["units", "garments", "fabrics", "fill", "geometry", "quantize", "flatten", "satin", "satinplay", "satinfont", "fontbin", "dst", "dstimport", "exp", "digitize"]) {
    require("../../../src/" + f + ".js");
  }
  requests = [];
  globalThis.fetch = vi.fn(async (url) => {
    requests.push(String(url));
    if (/\.dst$/.test(url) && failNextDst) {
      failNextDst = false;
      throw new TypeError("Failed to fetch");
    }
    const bytes = new Uint8Array(readFileSync(join(PACK, String(url).replace(/^starter\//, ""))));
    return {
      ok: true,
      status: 200,
      json: async () => JSON.parse(Buffer.from(bytes).toString("utf8")),
      arrayBuffer: async () => bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength),
    };
  });
  StarterPicker = (await import("./StarterPicker.svelte")).default;
});

test("twelve cards: the pack's own art, the manifest's name, and where the art came from", async () => {
  const { findAllByRole, container, getByRole } = render(StarterPicker);
  expect(getByRole("dialog", { name: "Starter designs" })).toBeInTheDocument();
  const cards = await findAllByRole("button", { name: /^Add / });
  expect(cards).toHaveLength(12);

  for (const m of manifest.designs) {
    const card = container.querySelector(`[data-starter="${m.id}"]`);
    expect(card, m.id).not.toBeNull();
    expect(card.querySelector(".sp-title").textContent).toBe(m.title);
    expect(card.querySelector("img").getAttribute("src")).toBe("starter/" + m.art);
    const credit = card.querySelector(".sp-credit");
    expect(credit.textContent).toContain(`Art by ${m.author} · ${m.license}`);
    const link = credit.querySelector("a");
    expect(link.getAttribute("href")).toBe(m.source_page_url);
    expect(link.getAttribute("rel")).toContain("noopener");
  }
});

test("no grade, score or finding is shown on the pack", async () => {
  const { findAllByRole, container } = render(StarterPicker);
  await findAllByRole("button", { name: /^Add / });
  // The manifest carries preflight grades A-C; none may reach the screen.
  expect(container.textContent).not.toMatch(/preflight|grade|score|warning|lettering/i);
  expect(container.querySelector(".warn, [role=alert]")).toBeNull();
});

test("picking a card hands App the import patch for that design's .dst", async () => {
  const picked = vi.fn();
  const { findByRole } = render(StarterPicker, { events: { pick: (e) => picked(e.detail) } });
  await fireEvent.click(await findByRole("button", { name: "Add Bumblebee" }));
  await vi.waitFor(() => expect(picked).toHaveBeenCalledTimes(1));

  const patch = picked.mock.calls[0][0];
  expect(patch.name).toBe("Bumblebee");
  expect(patch.sizeMm).toBeNull();
  expect(Object.keys(patch.blockColors)).toHaveLength(3);
  const bytes = Uint8Array.from(atob(patch.dstBase64), (c) => c.charCodeAt(0));
  expect(Array.from(bytes)).toEqual(Array.from(readFileSync(join(PACK, "bumblebee.dst"))));
  expect(requests).toContain("starter/bumblebee.dst");
  // Static files only: nothing was asked of the digitizer service.
  expect(requests.every((u) => u.startsWith("starter/"))).toBe(true);
});

test("a design that fails to load says so on its card, picks nothing, and can be retried", async () => {
  const picked = vi.fn();
  const { findByRole, container } = render(StarterPicker, { events: { pick: (e) => picked(e.detail) } });
  const owl = await findByRole("button", { name: "Add Owl" });
  failNextDst = true;
  await fireEvent.click(owl);
  await vi.waitFor(() => expect(container.querySelector('[data-starter="owl"] .sp-failed')).not.toBeNull());
  expect(picked).not.toHaveBeenCalled();
  expect(owl).not.toBeDisabled();

  await fireEvent.click(owl);
  await vi.waitFor(() => expect(picked).toHaveBeenCalledTimes(1));
  expect(picked.mock.calls[0][0].name).toBe("Owl");
});

test("Escape and the close button both ask App to close", async () => {
  const closed = vi.fn();
  const { getByRole } = render(StarterPicker, { events: { close: closed } });
  await fireEvent.keyDown(getByRole("dialog", { name: "Starter designs" }), { key: "Escape" });
  await fireEvent.click(getByRole("button", { name: "Close" }));
  expect(closed).toHaveBeenCalledTimes(2);
});
