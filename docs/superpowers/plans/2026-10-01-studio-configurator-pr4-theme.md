# Studio Configurator — PR 4: Theme Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Studio look like the Tesla-style configurator Kent picked: white page and panel, near-black type at two weights, a smaller type scale, one accent used only where it means something, and a 44 px wordmark top bar.

**Architecture:** Almost entirely `app/src/ui/theme.css` — the app is already token-driven, so the pass is (1) new palette values plus one new neutral-fill token, (2) a new type scale and a two-weight rule, (3) taking accent off hover states, (4) a small top-bar markup change in `App.svelte`, (5) a motion/shadow audit. A new Playwright spec measures text contrast across the panel, top bar, sheet and drawer so the next palette change cannot ship white-on-white again.

**Tech Stack:** CSS custom properties, Svelte 5, `@playwright/test`. No new dependencies; Inter (`@fontsource-variable/inter`) stays.

**Spec:** `docs/superpowers/specs/2026-09-30-studio-configurator-design.md` §6. Runs BEFORE PR 3 (progressive disclosure) by Kent's call 2026-10-01 — so the panel is still long; this PR changes how it looks, not what is in it.

## Global Constraints

- `app/` only. `src/*.js` (the engine) is never touched. No component behaviour changes; class names stay stable.
- Palette (exact): `--ink: #171a20`, `--bg: #ffffff`, `--surface: #ffffff`, `--border: #e6e6e6`, NEW `--fill: #f4f4f4` (neutral control fill and hover). `--muted` (#616875), `--accent` (#4f46e5), `--accent-dark`, `--tint`, `--tint-border`, `--danger*`, `--warn*`, `--field-bg` and every `--surround*` token are UNCHANGED.
- Accent is used ONLY for: the Download CTA (`button.primary`), selection (rings, `--tint` backgrounds, checked/selected states), links (`.linklike`, `a`), and focus (`:focus-visible`, input focus borders). Never for a plain hover.
- Type scale (exact): title 22 px, body 13 px, small 12 px, caption 11 px, label 10 px, drawer/dialog heading 16 px. Weights: 400 and 500 only in the app chrome; the summary bar's figures are the one 600.
- iOS guard: under 820 px, `input`, `textarea` and `select` are 16 px (Safari zooms the page into any focused field under 16 px).
- Top bar: 44 px tall, white, no bottom border; wordmark text exactly `EMB·BOT` (middle dot U+00B7), 12 px / 600 / `.08em` tracking — the wordmark is the second and last 600 in the chrome; the Font credits control keeps the accessible name `Font credits`.
- Text contrast: every text element in `.topbar`, `.panel`, `.sheet`, `.drawer` reads ≥ 4.5:1 against its effective background (≥ 3:1 for text ≥ 24 px or ≥ 18.66 px at weight ≥ 700); disabled controls are exempt. Measured by the new spec, not asserted by eye.
- Transitions are 150 ms ease and live only inside `@media (prefers-reduced-motion: no-preference)`. Shadows only on floating surfaces (popovers, menus, the sheet, the drawer, tooltips).
- Unit: `cd app && npx vitest run --hookTimeout=90000 --testTimeout=60000`; e2e: `npx playwright test <files> --workers=1 --reporter=list > ../log 2>&1; echo "EXIT=$?" >> ../log` and read the EXIT line. Plain separate shell commands in this worktree (no `cd`, no loops, no `&&` chains containing git). Edit tool only — never a PowerShell regex round-trip (theme.css has non-ASCII).
- Branch `claude/configurator-theme`, stacked on PR #586; merge `origin/main` once #586 lands. Commit after every task: subject, blank line, `Co-Authored-By:` trailer. PR ready-for-review, auto-merge armed while `mergeable_state` is `blocked`.

---

## File map

| File | Change |
|------|--------|
| `app/src/ui/theme.css` | palette values, `--fill`, type scale, weights, headings, hovers, top bar, motion, shadows |
| `app/src/App.svelte` | top-bar markup: wordmark, `?` credits button |
| `app/src/ui/DigitizePanel.svelte`, `FontBrowser.svelte`, `FontCredits.svelte` | scoped-style token swaps only (`--bg` → `--fill`, weights → 500) |
| `app/e2e/theme-contrast.spec.js` | create — the contrast sweep |
| `MASTER_SCOPE.md`, `docs/scope/3-studio-app-wizard.md` | area 3 status |

---

### Task 1: Palette — white page, and a neutral fill

**Files:**
- Modify: `app/src/ui/theme.css` (`:root` palette block; every `var(--bg)` consumer)
- Modify: `app/src/ui/DigitizePanel.svelte` (2 scoped rules), `app/src/ui/FontBrowser.svelte` (1 scoped rule)

**Interfaces:**
- Produces: token `--fill` — Tasks 3 and 4 use it for neutral hovers and the badge.

- [ ] **Step 1: The tokens**

In `:root`, change three values and add one token directly under `--bg`:

```css
  --ink: #171a20;
  --bg: #ffffff; /* the page — white, like the panel (2026-10-01 theme pass) */
  /* The neutral fill: pills, segmented controls, hover grounds, read-only
     inputs. It is what --bg used to be for controls before the page went
     white — on a white page a white hover is no hover at all. */
  --fill: #f4f4f4;
  --border: #e6e6e6;
```

`--surface` is already `#ffffff`. Leave the long comment above `--muted` alone (its numbers are re-measured in Task 6).

- [ ] **Step 2: Move every control fill off `--bg`**

Run: `grep -n "var(--bg)" src/ui/theme.css src/ui/*.svelte src/App.svelte`
Expected: 13 hits in `theme.css`, 2 in `DigitizePanel.svelte`, 1 in `FontBrowser.svelte`. The `body { background: var(--bg) }` rule KEEPS `--bg`. Every other hit — hover grounds (`.projectname:hover`, `.zoombtn:hover`, `.hooptile:hover`, `.undo-btn:hover`, `.dp-upload-btn:hover`, `.gmenu-item:hover`), control fills (`.startseg`, `.gpill`, the two rules near `.tcard`/template previews, the drawer rule near line 465), and `.sizeinput[readonly]` — becomes `var(--fill)`. Change each with the Edit tool, one at a time.

- [ ] **Step 3: Verify**

Run: `grep -n "var(--bg)" src/ui/theme.css src/ui/*.svelte src/App.svelte`
Expected: exactly one hit — the `body` rule.
Run: `npx vite build` — Expected: succeeds.

- [ ] **Step 4: Commit**

```bash
git add app/src/ui/theme.css app/src/ui/DigitizePanel.svelte app/src/ui/FontBrowser.svelte
git commit -m "theme: a white page, and --fill for the controls that used the old ground"
```

---

### Task 2: Type — a smaller scale and two weights

**Files:**
- Modify: `app/src/ui/theme.css` (type tokens; `.cfg-body h2`; the section-label rule; every `--fw-bold` / `--fw-semibold` consumer; the 820 px block)
- Modify: `app/src/ui/DigitizePanel.svelte`, `FontBrowser.svelte`, `FontCredits.svelte` (scoped weight fallbacks)

- [ ] **Step 1: The scale**

Replace the six size tokens and delete `--fw-bold`:

```css
  --fs-2xs: 0.625rem;   /* 10 — labels under figures */
  --fs-xs: 0.6875rem;   /* 11 — captions */
  --fs-sm: 0.75rem;     /* 12 — small / secondary */
  --fs-md: 0.8125rem;   /* 13 — body, and every control */
  --fs-lg: 1rem;        /* 16 — drawer and dialog headings */
  --fs-xl: 1.375rem;    /* 22 — the panel title */
```

```css
  --fw-normal: 400;
  --fw-medium: 500;
  --fw-semibold: 600; /* the summary bar's figures and the wordmark — nothing else */
```

- [ ] **Step 2: Two weights**

Run: `grep -n "fw-bold\|fw-semibold" src/ui/theme.css src/ui/*.svelte src/App.svelte`
Every `var(--fw-bold)` and `var(--fw-semibold)` becomes `var(--fw-medium)`; in the Svelte scoped styles the fallbacks go with them (`var(--fw-semibold, 600)` → `var(--fw-medium, 500)`, `var(--fw-bold, 700)` → `var(--fw-medium, 500)`). The ONE rule that keeps `var(--fw-semibold)`: `.summarybar-figure b`. (`.logomark` and `.logo` are deleted in Task 4 — change them here anyway so the grep below is clean.)

Run the grep again. Expected: `--fw-bold` nowhere; `--fw-semibold` only in the token definition and `.summarybar-figure b`.

- [ ] **Step 3: Headings**

Replace the `.cfg-body h2` rule and the section-label rule (and rewrite the long comment above the label rule — the "eyebrow" rationale no longer describes it):

```css
.cfg-body h2,
.sheet h2 {
  margin-top: 0;
  font-size: var(--fs-xl);
  font-weight: var(--fw-medium);
}

/* ---- Section heading ------------------------------------------------------
   Heads a control group: "Garment", "Hoop size", "Threads", and the two
   span-labels that rank with them (.tp-label "Color", .alignlabel "Align in
   hoop"). Sentence case at body size, medium weight, full ink — the Tesla
   configurator's voice: the heading is the same size as what it heads and
   outranks it by weight alone. (It was a 12 px uppercase muted eyebrow until
   2026-10-01; with the body at 13 px an eyebrow one pixel smaller read as
   noise, not rank.) Keyed on ROLE, not tag, for the reason the old comment
   gave: the labels rank the same on screen whatever element carries them.
   A FIELD label — "Letter spacing", "Curve" — still does not take this. */
.cfg-body h3,
.sheet h3,
.tp-label,
.alignlabel {
  font-size: var(--fs-md);
  font-weight: var(--fw-medium);
  letter-spacing: 0;
  text-transform: none;
  color: var(--ink);
}
```

Keep the follow-on `.cfg-body h3, .sheet h3 { margin-bottom: var(--space-2); }`. If a later rule re-applies `text-transform: uppercase` or `--tracking-wide` to one of these four selectors (grep `text-transform: uppercase`), report it rather than deleting blind — some uppercase labels elsewhere (e.g. a chip) are deliberate.

- [ ] **Step 4: The iOS guard**

Inside the existing `@media (max-width: 820px)` block, add:

```css
  /* Safari on iOS zooms the whole page into any focused field under 16px,
     and the body is 13px now. Fields keep 16px at phone widths only. */
  input, textarea, select { font-size: 16px; }
```

- [ ] **Step 5: Verify**

Run: `npx vite build` — Expected: succeeds.
Run: `npx vitest run src/ui/Configurator.spec.js src/ui/SummaryBar.spec.js src/ui/DownloadSheet.spec.js src/ui/GarmentPicker.spec.js` — Expected: pass (no test reads sizes).

- [ ] **Step 6: Commit**

```bash
git add app/src/ui/theme.css app/src/ui/DigitizePanel.svelte app/src/ui/FontBrowser.svelte app/src/ui/FontCredits.svelte
git commit -m "theme: a 13px body, a 22px title, and two weights"
```

---

### Task 3: Accent means something

**Files:**
- Modify: `app/src/ui/theme.css` (ten hover rules; `.mydesigns .badge`)

- [ ] **Step 1: Hovers go neutral**

Run: `grep -n "hover.*var(--accent)\|var(--accent).*hover" src/ui/theme.css`
Expected ten rules. `.linklike:hover { color: var(--accent); }` STAYS (a link). `.font-credits-btn:hover` is rewritten in Task 4 — set it to `color: var(--ink)` here. The other eight change like this — border to ink, text stays ink, tinted grounds to fill:

```css
.drawer-close:hover { border-color: var(--ink); color: var(--ink); }
.drawer-new:hover { border-color: var(--ink); background: var(--fill); }
.drawer-row-actions button:hover { border-color: var(--ink); color: var(--ink); }
.eladd:hover { border-color: var(--ink); color: var(--ink); }
.tp-brand:hover { border-color: var(--ink); }
.autofit:hover { border-color: var(--ink); }
.tp-trigger:hover { border-color: var(--ink); }
.threadreset:hover { border-color: var(--ink); color: var(--ink); }
```

`.drawer-row-actions button.danger:hover` and any `:focus` / `:focus-visible` rule keep their colours. Also check the Svelte scoped styles: `grep -n "hover" src/ui/*.svelte | grep "accent"` — apply the same rule to any plain hover found, and list them in the report.

- [ ] **Step 2: The badge**

```css
.mydesigns .badge {
  /* …unchanged layout lines… */
  background: var(--fill);
  color: var(--ink);
  font-size: var(--fs-xs);
  font-weight: var(--fw-medium);
}
```

(Only the `background`, `color` and `font-weight` lines change.)

- [ ] **Step 3: Verify and commit**

Run: `grep -n "hover.*var(--accent)\|var(--accent).*hover" src/ui/theme.css`
Expected: `.linklike:hover` only.
Run: `npx vite build` — succeeds.

```bash
git add app/src/ui/theme.css
git commit -m "theme: accent is for the CTA, selection, links and focus — not for hover"
```

---

### Task 4: The top bar

**Files:**
- Modify: `app/src/App.svelte` (the `<header class="topbar">` block, ~L1088–1110)
- Modify: `app/src/ui/theme.css` (`--topbar-h`; `.topbar`, `.logomark`, `.logo`, `.mydesigns`, `.font-credits-btn`, `.undo-btn`; the 820 px block's `.logo, .font-credits-btn { display: none; }`)

- [ ] **Step 1: Markup**

In `App.svelte` replace

```svelte
    <span class="logomark" aria-hidden="true">EMB</span>
    <span class="logo">Bot Studio</span>
```

with

```svelte
    <span class="wordmark">EMB·BOT</span>
```

and change the Font credits button's content only — keep `class`, `bind:this` and `on:click` exactly as they are:

```svelte
    <button type="button" class="font-credits-btn" aria-label="Font credits" title="Font credits" bind:this={creditsBtn} on:click={() => openCredits(creditsBtn)}>?</button>
```

- [ ] **Step 2: CSS**

`--topbar-h: 44px;`. In `.topbar`: delete `border-bottom`, keep everything else. Delete the `.logomark` and `.logo` rules; add:

```css
.wordmark {
  font-size: var(--fs-sm);
  font-weight: var(--fw-semibold);
  letter-spacing: 0.08em;
  white-space: nowrap;
  color: var(--ink);
}
```

`.mydesigns`: `min-height: 32px; padding: var(--space-1) var(--space-3); border-color: transparent; font-weight: var(--fw-medium);` and `.mydesigns:hover { background: var(--fill); }` (replace the border-colour hover).

`.font-credits-btn`: a 28 px round control —

```css
.font-credits-btn {
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-full);
  background: none;
  color: var(--muted);
  font: inherit;
  font-size: var(--fs-sm);
  cursor: pointer;
}
.font-credits-btn:hover { border-color: var(--ink); color: var(--ink); }
```

`.undo-btn`: if its height exceeds 32 px, set `height: 28px; width: 28px` (read the rule first; keep its icon size).

In the 820 px block replace `.logo, .font-credits-btn { display: none; }` with nothing — the wordmark is short and the `?` is 28 px, both fit; rewrite that block's comment to say so. Check the top bar at 375 px in Task 7's screenshots; if the project name is squeezed below ~80 px, hide `.font-credits-btn` again there and say so.

- [ ] **Step 3: Verify**

Run: `grep -rn "logomark\|class=\"logo\"\|\.logo\b" src/ e2e/` — Expected: no hit.
Run: `npx vite build` — succeeds.
Run: `npx playwright test e2e/configurator-smoke.spec.js e2e/field-chrome.spec.js --workers=1 --reporter=list > ../e2e-pr4-t4.log 2>&1; echo "EXIT=$?" >> ../e2e-pr4-t4.log` — Expected: `EXIT=0` (the smoke suite's phone-width sheet test measures `.topbar`'s height at run time, and field-chrome's canvas-fills-the-pane test gains 20 px of height).

- [ ] **Step 4: Commit**

```bash
git add app/src/App.svelte app/src/ui/theme.css
git commit -m "theme: a 44px top bar with a wordmark"
```

---

### Task 5: Motion and shadow audit

**Files:**
- Modify: `app/src/ui/theme.css`

- [ ] **Step 1: Motion**

Inside `@media (prefers-reduced-motion: no-preference)`: every `transition` duration becomes `150ms` (the shared rule is `140ms` today). Then `grep -n "transition" src/ui/theme.css src/ui/*.svelte` — any `transition` OUTSIDE that media block is a finding: move it inside (theme.css) or wrap it in the same media query (scoped styles). List what you moved.

- [ ] **Step 2: Shadows**

Run: `grep -n "box-shadow" src/ui/theme.css src/ui/*.svelte`
Keep a shadow only where the element FLOATS over other content: `.fieldmenu`, `.gmenu`, `.sheet`, `.drawer`, the font/thread popovers, the shape popover, tooltips, the simulator bar if it overlays, and the selection/focus RINGS (`--ring`, `--ring-inset`, `.fabricswatch` inset hairlines — those are borders drawn as shadows, not elevation). Remove `box-shadow` from anything that sits in the flow (cards, rows, buttons, the top bar, the zoom bar). Report the full list with a keep/remove verdict per rule.

- [ ] **Step 3: Verify and commit**

Run: `npx vite build` — succeeds.

```bash
git add app/src/ui/theme.css app/src/ui
git commit -m "theme: 150ms motion behind the reduced-motion gate; shadows only where something floats"
```

---

### Task 6: The contrast sweep

**Files:**
- Create: `app/e2e/theme-contrast.spec.js`

**Interfaces:**
- Consumes: `startStudio`, `typeText`, `openDownload`, `closeDownload` from `./helpers.js`.

- [ ] **Step 1: Write the spec**

```js
// Text contrast across the Studio's chrome, measured in the running app.
//
// Every palette change this project has made by reading the CSS has shipped
// at least one unreadable surface — the wizard's Next button was white on
// white for weeks (2026-08-25), and two tokens sat under 4.5:1 on their own
// grounds until someone measured. This sweep reads COMPUTED colours, walks
// up to the first opaque background, and holds every text element in the
// top bar, the panel, the Download sheet and the My designs drawer to WCAG
// AA. Disabled controls are exempt, as WCAG exempts them.
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

  for (const root of [".topbar", ".panel"]) {
    const res = await sweep(page, root);
    expect(res.checked, `${root}: nothing was measured`).toBeGreaterThan(5);
    expect(res.failures, `${root} — empty design`).toEqual([]);
  }

  await typeText(page, "FRITSCH");
  const panel = await sweep(page, ".panel");
  expect(panel.failures, ".panel — with a design").toEqual([]);

  await page.getByRole("button", { name: "More garments" }).click();
  const menu = await sweep(page, ".gmenu");
  expect(menu.checked).toBeGreaterThan(5);
  expect(menu.failures, ".gmenu").toEqual([]);
  await page.keyboard.press("Escape");

  await openDownload(page);
  const sheet = await sweep(page, ".sheet");
  expect(sheet.checked).toBeGreaterThan(10);
  expect(sheet.failures, ".sheet").toEqual([]);
  await closeDownload(page);

  await page.getByRole("button", { name: /^My designs/ }).click();
  const drawer = await sweep(page, ".drawer");
  expect(drawer.checked).toBeGreaterThan(3);
  expect(drawer.failures, ".drawer").toEqual([]);
});
```

- [ ] **Step 2: Run it, and prove it bites**

Run: `npx playwright test e2e/theme-contrast.spec.js --workers=1 --reporter=list > ../e2e-pr4-t6.log 2>&1; echo "EXIT=$?" >> ../e2e-pr4-t6.log`
Expected: `EXIT=0`. If it reports failures, they are REAL findings about the theme — fix the CSS (darken the token on that ground, or change which token the rule uses; never loosen the threshold, never exclude the element), re-run, and list every fix in the report with before/after ratios.
Mutation: temporarily set `--muted: #9aa0a6;` in `theme.css`, re-run — the test must FAIL listing muted text; restore, re-run, `EXIT=0`. Report both outputs.

- [ ] **Step 3: Commit**

```bash
git add app/e2e/theme-contrast.spec.js app/src/ui/theme.css
git commit -m "e2e: text contrast across the chrome is measured, not assumed"
```

---

### Task 7: Screenshots, docs, verify, PR (controller)

- [ ] **Step 1: Screenshots.** Serve the worktree (`npm run dev -- --port 5190 --strictPort`, background) and capture, headless, at 1440×900 and 375×812: the empty Studio, a typed design, the More menu, the Download sheet, the My designs drawer. Read each image. Check by eye: white panel and page, no accent on anything that is not the CTA/selection/link, headings sentence-case 13/500, top bar 44 px with the wordmark, nothing clipped at 375. Stop the server.
- [ ] **Step 2: Docs.** Area doc: a dated paragraph at the top — the tokens that changed and their values, `--fill` and why it exists, the scale, the two-weight rule, the accent rule, the top bar, the iOS guard, the contrast spec and what it found. MASTER_SCOPE row 3: one sentence with a `(verb date — source)` pointer; no net line growth. If the contrast sweep changed `--muted` or any token's stated ratio, update the comment above that token in `theme.css` with the newly measured numbers.
- [ ] **Step 3: Full unit suite** — `EXIT=0`.
- [ ] **Step 4: e2e, no-service group** plus `theme-contrast` — `EXIT=0`.
- [ ] **Step 5: Merge `origin/main`** (PR #586 must have landed; otherwise the PR says it is stacked).
- [ ] **Step 6: Final whole-branch review**, one fix wave, one scoped re-review.
- [ ] **Step 7: Open the PR ready-for-review** with the screenshots described, the contrast findings, counts with recorded exit codes; flag for Kent: the body text drops 16 → 13 px and labels to 10 px (one token each to change back). Arm auto-merge while `mergeable_state` is `blocked`.
