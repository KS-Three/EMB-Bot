// Text contrast across the Studio's chrome, measured in the running app.
//
// Every palette change this project has made by reading the CSS has shipped
// at least one unreadable surface — the wizard's Next button was white on
// white for weeks (2026-08-25), and two tokens sat under 4.5:1 on their own
// grounds until someone measured. This sweep reads COMPUTED colours, walks
// up to the first opaque background, and holds every text element in the
// top bar, the panel, the Download sheet and the My designs drawer to WCAG
// AA. Disabled controls are exempt, as WCAG exempts them.
//
// It does NOT measure:
//   - form-field values, select text and placeholders (not text nodes);
//   - hover and focus states;
//   - anything on the stage (`.field`);
//   - the digitize, image and manual panels;
//   - tooltips, the field menu, popovers, the font browser and font credits;
//   - disabled or inert controls (exempt by WCAG).
import { test, expect } from "@playwright/test";
import { startStudio, typeText, openDownload, closeDownload } from "./helpers.js";

async function sweep(page, rootSelector) {
  return page.evaluate((rootSel) => {
    const parse = (c) => {
      const m = c.match(/rgba?\(([^)]+)\)/);
      if (!m) return null;
      const p = m[1].split(",").map((x) => parseFloat(x));
      return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
    };
    const lum = ({ r, g, b }) => {
      const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
      return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
    };
    const over = (top, under) => ({
      r: top.r * top.a + under.r * (1 - top.a),
      g: top.g * top.a + under.g * (1 - top.a),
      b: top.b * top.a + under.b * (1 - top.a),
      a: 1,
    });
    const groundOf = (el) => {
      const layers = [];
      for (let n = el; n; n = n.parentElement) {
        const c = parse(getComputedStyle(n).backgroundColor);
        if (c && c.a > 0) { layers.push(c); if (c.a === 1) break; }
      }
      let g = { r: 255, g: 255, b: 255, a: 1 };
      for (let i = layers.length - 1; i >= 0; i--) g = over(layers[i], g);
      return g;
    };
    const opacityOf = (el) => {
      let o = 1;
      for (let n = el; n; n = n.parentElement) o *= parseFloat(getComputedStyle(n).opacity);
      return o;
    };
    const root = document.querySelector(rootSel);
    if (!root) return { missing: rootSel, failures: [], checked: 0 };
    const failures = [];
    let checked = 0;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const seen = new Set();
    for (let t = walker.nextNode(); t; t = walker.nextNode()) {
      if (!t.nodeValue.trim()) continue;
      const el = t.parentElement;
      if (!el || seen.has(el)) continue;
      seen.add(el);
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0 || cs.visibility === "hidden" || cs.display === "none") continue;
      if (el.closest(":disabled, [aria-disabled='true'], [inert]")) continue;
      const fg0 = parse(cs.color);
      if (!fg0) continue;
      const ground = groundOf(el);
      const fg = over({ ...fg0, a: fg0.a * opacityOf(el) }, ground);
      const L1 = lum(fg), L2 = lum(ground);
      const ratio = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
      const px = parseFloat(cs.fontSize);
      const large = px >= 24 || (px >= 18.66 && parseInt(cs.fontWeight, 10) >= 700);
      checked++;
      if (ratio < (large ? 3 : 4.5)) {
        failures.push(`${ratio.toFixed(2)} "${t.nodeValue.trim().slice(0, 30)}" <${el.tagName.toLowerCase()} class="${el.className}"> ${cs.color} on rgb(${Math.round(ground.r)},${Math.round(ground.g)},${Math.round(ground.b)})`);
      }
    }
    return { failures, checked };
  }, rootSelector);
}

test("every text element in the chrome reads at WCAG AA against its own ground", async ({ page }) => {
  await page.route("**/health", (r) => r.abort());
  await page.setViewportSize({ width: 1440, height: 900 });
  await startStudio(page);

  // The `checked > 0` expectations only prove each root was found and
  // something was measured; they are not contrast thresholds. Failures are
  // collected across every root so one red run lists every failing element.
  const all = [];
  const collect = (label, res) => all.push(...res.failures.map((f) => `${label}: ${f}`));

  for (const root of [".topbar", ".panel"]) {
    const res = await sweep(page, root);
    expect(res.checked, `${root}: nothing was measured`).toBeGreaterThan(0);
    collect(`${root} — empty design`, res);
  }

  await typeText(page, "FRITSCH");
  const panel = await sweep(page, ".panel");
  expect(panel.checked, ".panel — with a design: nothing was measured").toBeGreaterThan(0);
  collect(".panel — with a design", panel);

  await page.getByRole("button", { name: "More garments" }).click();
  const menu = await sweep(page, ".gmenu");
  expect(menu.checked, ".gmenu: nothing was measured").toBeGreaterThan(0);
  collect(".gmenu", menu);
  await page.keyboard.press("Escape");

  await openDownload(page);
  const sheet = await sweep(page, ".sheet");
  expect(sheet.checked, ".sheet: nothing was measured").toBeGreaterThan(0);
  collect(".sheet", sheet);
  await closeDownload(page);

  await page.getByRole("button", { name: /^My designs/ }).click();
  // The drawer is a lazy chunk; wait for it before measuring.
  await page.locator(".drawer").waitFor();
  const drawer = await sweep(page, ".drawer");
  expect(drawer.checked, ".drawer: nothing was measured").toBeGreaterThan(0);
  collect(".drawer", drawer);

  expect(all, "contrast failures").toEqual([]);
});
