// @vitest-environment jsdom
//
// Progressive disclosure (spec 2026-09-30 §5): the editor for each element
// type opens showing ONLY the Visible column of the spec's table, and the
// power tools sit behind one "Advanced ›" disclosure -- rendered, not removed,
// so every control keeps its test id and its state.
//
// The assertions are about what a customer can SEE (`toBeVisible`), which for
// a `hidden` section is the whole point: the control still exists in the DOM.
import { beforeAll, beforeEach, expect, test } from "vitest";
import { render, fireEvent, screen, cleanup } from "@testing-library/svelte";
import "@testing-library/jest-dom/vitest";
import { resetAdvanced } from "../lib/advanced.js";

let ContentStep, P;
beforeAll(async () => {
  // Same stub-before-import ordering TextStep.spec.js documents: the engine is
  // a browser global that emb.js demands at module load.
  globalThis.EMB = { getGarment: () => null, buildLetteringDesign: () => { throw new Error("not used"); } };
  globalThis.fetch = () => Promise.reject(new Error("no network in tests"));
  // jsdom has no 2D canvas; ImagePanel and ManualPanel paint on mount. Any
  // drawing call is a no-op; assigned properties (fillStyle...) just stick.
  HTMLCanvasElement.prototype.getContext = () => {
    const state = {};
    return new Proxy(state, {
      get: (t, k) => (k in t ? t[k] : () => ({ data: [], width: 0, height: 0, addColorStop() {} })),
      set: (t, k, v) => ((t[k] = v), true),
    });
  };
  ({ default: ContentStep } = await import("./ContentStep.svelte"));
  P = await import("../lib/project.js");
});
beforeEach(() => { cleanup(); resetAdvanced(); });

function projectWith(el) {
  return { ...P.defaultProject(), elements: [el], selectedId: el.id };
}
function mount(el, extra = {}) {
  return render(ContentStep, { project: projectWith(el), digitizerHealth: { ok: true }, ...extra });
}
const toggle = () => screen.getByTestId("advanced-toggle");
const open = () => fireEvent.click(toggle());

test("text: first render shows the text box, font, colour and size -- nothing else", () => {
  mount({ ...P.defaultTextElement("t1"), text: "Kent" });
  expect(screen.getByPlaceholderText("Type a name or word")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Font" })).toBeVisible();
  expect(screen.getByLabelText("Width")).toBeVisible();
  for (const hidden of [/Letter spacing/, /^Curve/, /^Rotation/, /^Slant/, "Justify lines", "Weight", "Flip upside-down"]) {
    expect(screen.getByText(hidden)).not.toBeVisible();
  }
  expect(screen.getByText(/Align in/)).not.toBeVisible();
  expect(toggle()).toHaveAttribute("aria-expanded", "false");
});

test("text: Advanced shows the second column, and closing hides it again", async () => {
  mount({ ...P.defaultTextElement("t1"), text: "Kent" });
  await open();
  for (const shown of [/Letter spacing/, /^Curve/, /^Rotation/, /^Slant/, "Justify lines", "Weight", "Flip upside-down", /Align in/]) {
    expect(screen.getByText(shown)).toBeVisible();
  }
  await fireEvent.click(toggle());
  expect(screen.getByText(/Letter spacing/)).not.toBeVisible();
});

test("the add-element row (Design file included) is Advanced; the start control is the visible way in", async () => {
  mount({ ...P.defaultTextElement("t1"), text: "Kent" });
  const row = document.querySelector(".eladd-row");
  expect(row).not.toBeVisible();
  await open();
  expect(row).toBeVisible();
  expect(screen.getByRole("button", { name: "Design file" })).toBeVisible();
});

test("the element list stays visible: it is how a second element is reached", () => {
  mount({ ...P.defaultTextElement("t1"), text: "Kent" });
  expect(document.querySelector(".ellist")).toBeVisible();
});

test("image (browser lane): upload, colour count and swatches visible; ranges, merge, reset, background Advanced", async () => {
  mount(P.defaultImageElement("i1"));
  expect(screen.getByText(/^Colors:/)).toBeVisible();
  expect(screen.getByText("Remove background")).not.toBeVisible();
  expect(screen.getByRole("button", { name: "Merge selected", hidden: true })).not.toBeVisible();
  expect(screen.getByRole("button", { name: "Reset colors", hidden: true })).not.toBeVisible();
  await open();
  expect(screen.getByText("Remove background")).toBeVisible();
  expect(screen.getByRole("button", { name: "Merge selected" })).toBeVisible();
});

test("design file: the file chooser is visible, rotation is Advanced", async () => {
  mount(P.defaultDesignElement("f1"));
  expect(screen.getByText("Choose a .dst file…")).toBeVisible();
  expect(toggle()).toHaveAttribute("aria-expanded", "false");
});

test("shape: kind and colour visible; the per-kind parameters are Advanced", async () => {
  mount({ ...P.defaultShapeElement("s1"), kind: "rect" });
  expect(screen.getByRole("button", { name: "Rectangle" })).toBeVisible();
  expect(screen.getByText("Color")).toBeVisible();
  expect(screen.getByText("Corner radius")).not.toBeVisible();
  await open();
  expect(screen.getByText("Corner radius")).toBeVisible();
});

test("manual: the shape list is visible; the drawing canvas, tools and trace import are Advanced", async () => {
  mount(P.defaultManualElement("m1"));
  const undo = await screen.findByRole("button", { name: "Undo point", hidden: true });
  expect(undo).not.toBeVisible();
  expect(screen.getByRole("button", { name: "Trace image…", hidden: true })).not.toBeVisible();
  await open();
  expect(undo).toBeVisible();
});

test("artwork (auto-digitize): upload, run and colour count visible; the rest of the settings Advanced", async () => {
  const el = { ...P.defaultDigitizedElement("d1"), sourcePng: "iVBORw0KGgo=", name: "logo.png" };
  mount(el);
  // DigitizePanel is a lazy chunk: the first import transforms 3,600 lines.
  expect(await screen.findByText("Replace file…", {}, { timeout: 30_000 })).toBeVisible();
  expect(screen.getByRole("button", { name: "Auto Digitize Image" })).toBeVisible();
  expect(screen.getByText(/^Colors \(max/)).toBeVisible();
  for (const hidden of [/^Design width/, "Satin for thin shapes", /^Fill angle/, /^Border/, /^Design edge/]) {
    expect(screen.getByText(hidden)).not.toBeVisible();
  }
  await open();
  expect(screen.getByText(/^Design width/)).toBeVisible();
  expect(screen.getByText(/^Fill angle/)).toBeVisible();
});

test("the choice survives selecting another element (the editor is rebuilt)", async () => {
  const r = mount({ ...P.defaultTextElement("t1"), text: "Kent" });
  await open();
  r.unmount();
  mount(P.defaultImageElement("i1"));
  expect(toggle()).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByText("Remove background")).toBeVisible();
});
