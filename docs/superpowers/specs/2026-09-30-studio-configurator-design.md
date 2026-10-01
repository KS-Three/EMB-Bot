# The Studio as a configurator — design

*2026-09-30. Kent's brief: "modern and sleek, like an Apple, SpaceX or Tesla
website"; he dislikes the "Choose your garment" tile blocks and the Step
1·2·3·4 stepper. Six decisions taken in brainstorm, one layout picked from
three mockups (`.superpowers/brainstorm/1233-1790804287/content/layout.html`,
`layout-a-v2.html`). This is the spec the implementation plan is written
from. App-layer only — `src/` untouched.*

## 0. Decisions already taken

| # | Question | Kent's pick |
|---|----------|-------------|
| 1 | What replaces the four-step wizard | **Tesla configurator**: design fills the screen, one right-hand panel scrolls through sections, no numbers |
| 2 | Colour scheme | **Light, Tesla-like**: white, black type, one filled CTA, hairline borders |
| 3 | First screen | **Ready garment + one prompt**: left-chest polo already on screen, first control is *Add text / Upload logo* |
| 4 | Review and Download | **Sticky summary bar** at the panel's foot; Download opens a sheet holding formats + quality report |
| 5 | Power tools | **Progressive disclosure**: essentials visible, the rest behind *Advanced ›*; canvas right-click untouched |
| 6 | Layout (mockup A/B/C) | **A — Tesla classic**: fixed white right panel, one continuous scroll |
| 7 | Stage default | **Stitches close-up**: the hoop at working zoom, an *Original* chip, no "on garment" silhouette view |
| 8 | Stage surround | **Keep the dark `--surround` (#22252c)** shipped this morning; panel and page white |

Not changing: `EmbroideryField` behaviour (render, zoom, scale bar, drag,
click-to-edit popover, node editing, right-click tool menu), the engine, the
digitizer service, project file format, every export path.

## 1. Where this starts

`App.svelte` (1,257 lines) keys the LEFT panel off `step` — one of
`lib/flow.js`'s `STEPS = ["garment", "content", "create", "download"]` — and
`StepNav.svelte` draws the numbered badges, labels and Back/Next.
`lib/stepHistory.js` maps the browser's Back button onto step moves.
`GarmentStep.svelte` is the tile grid ("Choose your garment", ten
`garmentArt` tiles) plus `TemplateRow`, fabric swatches and the hoop strip.
The "create" step is a review recap (`designSummary`, `sewFacts`,
`QualityReport`, `SizePanel`) and `DownloadStep.svelte` is the format list
with the machine picker and save-to-folder.

The panel sits on the left, the field on the right. Today's 09-30 pass
already flattened the cards (no shadows, 1px borders, radii 4/6/10), rounded
the fabric swatches, made the hoops a segmented strip, and put the hoop on a
dark surround. That work stays; this spec builds on it.

`defaultProject()` already opens on `garmentId: "left_chest"` with one empty
text element — decision 3 costs no data change.

## 2. Structure

```
┌─ topbar ───────────────────────────────────────────────────────────┐
│ EMB·BOT   undo redo          Project name          My designs  ?   │
├───────────────────────────────────────────┬────────────────────────┤
│                                           │ Configurator (scroll)  │
│  [Original]                               │   Your design          │
│                                           │   Left chest polo·4×4  │
│         ┌───── dark surround ─────┐       │   [Add text|Upload]    │
│         │   hoop + thread render  │       │   ── Design ──         │
│         └─────────────────────────┘       │   ── Colors ──         │
│                                           │   ── Garment ──        │
│              zoom bar · scale             │   Advanced ›           │
│                                           ├────────────────────────┤
│                                           │ 76×18 mm 3,412 1 color │
│                                           │ [      Download      ] │
└───────────────────────────────────────────┴────────────────────────┘
```

### 2.1 Removed

- `lib/flow.js` `STEPS`, `nextStep`, `prevStep`, `canAdvance`. `isSewable`
  stays (it feeds the summary bar and the Download button's enabled state).
- `StepNav.svelte`, its spec and harness.
- `lib/stepHistory.js` and `App.stepHistory.spec.js`. The only history entry
  left is the Download sheet (§2.4).
- `GarmentStep.svelte`'s tile grid and the "Choose your garment" heading.
  `garmentArt.js` survives — the *More ›* popover uses it.
- The "create" review step in `App.svelte`; its content moves into the sheet.
- `topbar-download` (the shortcut that jumped to the download step) — the
  summary bar's button is the one Download.

### 2.2 `Configurator.svelte` (new; replaces the `{#if step === …}` chain)

One `<aside class="panel">` with a scrolling body and a sticky foot. Sections
in order, each a `<section>` with a 13px/500 heading, no numbers, no cards:

1. **Header** — "Your design" (22px/500, centred), subtitle
   `{garment label} · {hoop label}` (11px muted). Beneath it the segmented
   control **Add text | Upload logo** → `addelement` `"text"` / `"artwork"`.
   `Design file` and *Draw shapes* move under Advanced.
2. **Design** — the element list (`ellist`, as now) and the editor for the
   selected element (`TextStep` / `ImagePanel` / `DigitizePanel` /
   `DesignPanel` / `ShapePanel` / `ManualPanel`, chosen by `el.type` exactly
   as `ContentStep` does). Only the essentials render outside Advanced (§5).
3. **Colors** — the thread swatches for the selected element (`ThreadPicker`
   trigger for text; the sewn-colour row for artwork with an *Edit* link that
   opens the colour count slider + `ImagePanel`'s ranges).
4. **Garment** — pill row `Polo · Hat · Tee · More ›` (§3), the eight round
   fabric swatches + custom, the four-hoop segmented strip. Same
   `project.garmentId / fabricRgb / hoopId` writes as today.
5. **Advanced ›** — one `<details>`-style disclosure at the panel's foot,
   closed by default, remembered per session (not persisted). Holds
   everything in §5's second column.

`ContentStep.svelte` becomes the Design + Colors sections' body: keep the file,
drop its `<h2>What are you making?</h2>`, and split its template into the two
sections. `SizePanel` stays with the selected element, its fine controls
under Advanced.

### 2.3 `SummaryBar.svelte` (new)

Sticky foot of the panel, hairline top border. Three figures from what
already exists — `designDims` (mm), `sewFacts` (stitches, est. minutes,
trims), `sewnColors.length` — in a 12px/600 figure over a 10px muted label,
and one filled **Download** button (`--accent`, full width, 6px radius),
`disabled` with `title="Add text or a logo first"` until
`project.elements.some(isSewable)`. When the design has no stitches the
figures read `—`.

### 2.4 `DownloadSheet.svelte` (new)

A sheet sliding up over the panel (right-anchored, panel-width, full height,
`role="dialog"`, Escape and a close button dismiss). Contents, top to bottom:
the review recap rows (`designSummary`, `sewFacts` under the existing
`qualityIsTheWholeDesign` rule), `QualityReport`, then `DownloadStep`'s body
unchanged — machine picker, the one filled format button, "All formats",
save-to-folder. `DownloadStep.svelte` keeps its logic and spec; it is
rendered inside the sheet instead of as a step. Opening pushes one history
entry so browser Back closes it; closing pops it. Every `data-testid` and
button name in `DownloadStep` is unchanged so `download-machine.spec.js`
needs only a new opener.

### 2.5 Panel side

The panel moves to the RIGHT. `.studio` grid columns swap; nothing else in
the field depends on side. `e2e/field-chrome.spec.js`'s fabric-bbox test
reads pixels off the canvas, not page position — re-run, not rewritten.

## 3. Garment row

Pills (20px radius, 11px, `--bg` fill, selected = ink fill + white text) for
the three commonest placements — **Polo** (`left_chest`), **Hat**
(`hat_front`), **Tee** (`full_back`) — and **More ›**, which opens a popover
(the existing popover pattern from `ShapePopover`/`ProjectsDrawer`
elevation) listing all ten garments as `garmentArt` icon + label in two
columns. Picking one closes the popover and, when it is not one of the three,
shows it as a fourth selected pill (`Beanie ✓`). The subtitle under the
panel title follows.

The templates row (`TemplateRow`) leaves the garment section; the segmented
control is the new "start here". `TemplateRow` is re-homed as a **Start from
a template** row at the top of the My designs drawer (`ProjectsDrawer`,
which today lists saved projects only), firing the same `template` event
`App.svelte` already handles via `pickTemplate`. `applyTemplate` and
`TEMPLATES` are unchanged.

## 4. Stage: the Original chip

When the selected element carries a `workImage` (artwork or digitized), a
64×64 chip sits top-left of the field surround: thumbnail, "Original" caption,
white, 8px radius, one elevation shadow (popover level — it floats OVER the
surround, so it is one of the few things allowed a shadow). Click toggles
`showOriginal`; while true the field draws the source image fitted to the
hoop's placement box in place of the thread render and the chip inverts to
"Stitches". Any edit that re-renders flips it back to stitches. View-only
state — same lifecycle as zoom/pan, never saved. Drawn as HTML over the
field, not on the canvas (DOCTRINE: no chrome on sewable field;
`field-chrome.spec.js` pins it).

No garment silhouette view. `garmentArt` stays an icon set.

## 5. Progressive disclosure

What renders by default versus under **Advanced ›**:

| Element | Visible | Advanced |
|---------|---------|----------|
| text | text field, font trigger, size slider, thread swatch | letter spacing, stitch density, underlay, satin options, `SizePanel` fine controls |
| artwork (auto-digitize) | upload/replace, colour count, sewn colours, digitize status line | `DigitizePanel` options and its warning list, `ImagePanel` ranges/merge/reset, calibrate, background/enclosed toggle, `SizePanel` fine controls |
| design file | file name, colours, size | `DesignPanel` details |
| manual / shape | shape list, colour | `ManualPanel` side canvas, trace import, preset params |
| all | — | Layers panel, "Draw shapes", "Design file" add buttons |

Rule: a control is visible when a first-time customer with a logo or a name
needs it to reach a good sew-out; everything else is Advanced. Nothing is
deleted and no event or store changes — the same components render, wrapped.
Warnings that matter (the ones `QualityReport` promotes) still surface in the
Download sheet, so hiding `DigitizePanel`'s list does not hide a blocker.

## 6. Theme

Light, on the existing tokens — no new token names:

- `--bg: #ffffff`, `--surface: #ffffff`, `--border: #e6e6e6`, `--ink: #171a20`,
  `--muted` stays (already AA-tuned). `--surround` unchanged.
- `--accent` stays indigo; used ONLY by the Download CTA, selection rings and
  links. Pills and segmented controls use ink/white, not accent.
- Type: Inter, weights 400 and 500 only (drop 600/700 from the app chrome;
  figures in the summary bar use 600). Scale: title 22, section 13, body 13,
  caption 11, label 10.
- Radii 4/6 (cards, inputs) and 20 (pills). Shadows only on popovers, the
  sheet, the Original chip and the drawer.
- Transitions 150ms ease on section reveal, sheet slide and hover, all inside
  `prefers-reduced-motion: no-preference`.
- Topbar: `EMB·BOT` wordmark (12px/600, `.08em` tracking) replaces the
  "EMB" tile + "Bot Studio"; undo/redo beside it; project name centred as
  now; right: My designs, `?` (Font credits moves under it). 44px tall,
  no border, white.

Contrast is re-measured in the running app on every ground a token lands on
(the 09-30 method); numbers go in the PR body.

## 7. What the tests cost

This is most of the work and the plan budgets for it first.

- **e2e:** 80 step-navigation references across the 27 specs; every spec
  that walks *Next → Next → Next* or reads "Ready to stitch". One helper
  in `e2e/fixtures` — `openDownload(page)` clicks the summary bar and waits
  for the sheet dialog — replaces the walk. `wizard-smoke.spec.js` becomes
  `configurator-smoke.spec.js`: open → add text → (garment pill) → Download
  sheet → format button, same assertions on geometry and handoff.
- **Unit:** `StepNav.spec.js`, `App.stepHistory.spec.js`, `flow.spec.js`'s
  `canAdvance`/`nextStep` cases go. `GarmentStep.spec.js` becomes the garment
  section's spec (pills, More popover, fabric, hoop). New: `SummaryBar.spec`
  (figures, disabled state, `—` when nothing sews), `DownloadSheet.spec`
  (open/close, history entry, Escape), `Configurator.spec` (sections render
  per element type; Advanced hides the second column of §5). `ContentStep.
  reactivity.spec.js` stays.
- **Visual:** each PR is driven in a browser at 1440×900 and 375 wide.
  Under 820px `theme.css` already stacks the layout (field on top at 56vh,
  panel below with an internal scroll); the summary bar takes StepNav's
  place as the flex child pinned to the panel's foot, so the same bound
  keeps Download on screen. Screenshots in the PR body, computed styles
  read for contrast.

## 8. Phasing — four PRs, each green

1. **Structure.** `Configurator`, `SummaryBar`, `DownloadSheet`; stepper,
   flow steps, stepHistory, review step removed; panel to the right; e2e
   migrated. Garment section is the existing tiles inside the new section
   (ugly but correct). MASTER_SCOPE area 3 updated.
2. **Garment row + Original chip.** §3 and §4.
3. **Progressive disclosure.** §5 and the segmented start control.
4. **Theme pass.** §6, topbar, contrast measurements.

Each PR ready-for-review with auto-merge armed (CLAUDE.md), one lane per PR
behind the previous.

## 9. Out of scope

- Marketing/landing page (Kent chose the editor over a hero page).
- "On garment" silhouette rendering.
- Dark mode / OS-follow.
- Any engine, digitizer, or export change.
- Mobile-first redesign beyond keeping the existing under-820px stack.
