# Per-shape border control on the canvas — design

**Date:** 2026-09-08
**Status:** approved by Kent, not yet implemented
**Base:** `origin/main` @ `00575c9`. Every line number below was re-verified against that
commit; an earlier draft of this document carried citations from `94eff57` and every one of
them had moved.

## Why this exists

Kent digitized the Instagram icon at 80 mm, 6 colours, `satin` on, **Border = "Auto (satin
where it fits)"**, edge "leave open", forced flat art — 18,391 stitches — marked up a 348%
render in green/red/white pen, and said: *"Let's FIX the border stitching."* Asked what the
render showed, he added: *"they do not follow the shape outlines of the instagram logo
properly."*

He was right, and the reason is structural.

### What was measured

Reproduced at his exact settings (`digitizer_core.pipeline.run_stages` + `plan_stitches`):

| tier | stitches | share |
|---|---|---|
| **border** | **8,099** | **45.3%** |
| fill | 8,774 | 49.0% |
| underlay | 780 | 4.4% |
| travel | 151 | 0.8% |
| satin | 86 | 0.5% |

17,890 total, 8 colour blocks, 28 trims, 18 border rings over 16 shapes.

The Instagram logo has **three** shapes — rounded square, lens, flash dot. All three are
thread 2 (white): 999.1, 414.0 and 38.0 mm². The other 13 bordered shapes are the background
gradient, sliced by quantization into bands across threads 204 (5 pieces), 172 (3), 146 (3),
114 and 230. **53.0% of border path length runs along a boundary shared with another colour
region** — a quantization contour, not an artwork edge. That is ~4,290 stitches, ~24% of the
whole design, outlining shapes the logo does not have.

It also explains the ring counts exactly. The white rounded square is an annulus, so it
legitimately draws 2 rings; the two gradient bands touching it draw those same two seams
again → 4 concentric rings. The lens: 2 legitimate + 1 duplicate → 3.

### Root cause

`border_runs()` (`digitizer/digitizer_core/stage6_border.py:546`) takes **one shape's**
`visible` geometry and lays a closed ring around all of it. Nothing in any border mode asks
what is on the *other side* of a boundary. Both of `significant`'s gates — area share and
raggedness — are properties of the shape alone.

So a border is computed per **shape**, never per **edge**. Two consequences: every shared
seam is drawn twice, once from each side; and a quantization contour is bordered as if it
were artwork.

### Modes compared

| border mode | total | border | rings | on quantization seam |
|---|---|---|---|---|
| `auto` (Kent's) | 17,890 | 8,099 (45.3%) | 18 | 53.0% |
| `significant` | 16,425 | 6,631 (40.4%) | 16 | **62.2%** |
| `off` (the default) | 9,842 | 0 | 0 | — |

`significant` earns borders by size and smoothness, so it drops the *small* shapes and keeps
the *big gradient bands* — the share sitting on invented contours goes **up**. Neither
shipped mode can express "outline the logo, not the gradient". DOCTRINE:76 already rules
blanket bordering out (*"never blanket"*), but it rules on which **shapes**, never on which
**edges**, so `significant` inherits the same blind spot.

### Two discriminators tested and rejected

- **Colour distance across the boundary.** Zero of 34 adjacent-region boundaries fall below
  ΔE76 25; the minimum is 28.2. With `max_colors=6` the ramp is sliced into six genuinely
  distant threads. There *is* a suggestive gap (white↔band 58–98, band↔band 28–51) but it is
  7 ΔE units wide on n=34 from **one image** — the exact shape of the failure recorded in
  `thresholds-on-the-wrong-population-2026-08-28`. Not proposed.
- **Split provenance.** `Region.meta` carries only `layer`, `stitched`,
  `thread_resnapped_de00`. Nothing records "sliced off one ramp", so there is no existing
  signal to key on.

A **sliver-doubling** hypothesis was also tested and killed: only 0.5% of total border path
doubles back on itself within `BORDER_WIDTH_MM` (worst single ring 21%, 23 mm).

### What Kent chose instead

Asked which edges should earn a border, Kent's answer was: *"I should have the ability to
select the shape and turn them on and off."* Manual control, not an automatic rule. Given the
history above, that is the right call — it puts the judgement on his eye rather than on a
threshold calibrated from one logo.

### The control already ships

The per-shape override is fully built end to end and honoured:

- Service validates `shape_overrides[sid].border` ∈ `{off, auto, bean}`
  (`digitizer/digitizer_service/app.py:143`).
- `digitizer_core/regions.py` sets `r.meta["border"]`; `stage7_sequence.py:1972` reads it.
- The Studio renders a per-shape Border `<select>` at
  `app/src/ui/DigitizePanel.svelte:2240` — *Design (…) / No border / Auto border / Bean
  border* — wired `setShapeBorder` (:816) → `setOverride` (:889).

Verified live in the running Studio: **21 border selects**, one per shape, correct options.
(21 rather than the 16 above because that check ran at the panel's default colour count, not
Kent's `max_colors=6` — the count tracks shapes, not anything about borders.)

It is behind a collapsed section labelled **"Edit shapes (21)"**. Nothing in that label says
"border". The product owner did not know it existed. That is the actual defect this work
addresses.

### The recipe that works today, with no code change

Content step → Border = *No borders* → Edit shapes → set the three white rows to *Auto
border*:

| | `auto` | logo-only |
|---|---|---|
| total stitches | 17,890 | **12,650** (−29%) |
| border stitches | 8,099 | **2,819** (−65%) |
| rings | 18 | 5 |
| trims | 28 | 21 |
| thread | 44.0 m | 32.7 m |

Five rings: square outer/inner, lens outer/inner, flash dot. Exactly the Instagram outline.

## What is being built

Click a shape on the design canvas of a digitized element → a chip appears beside it with
that shape's Border control, writing the same `element.shapeOverrides[id].border` field the
panel list writes.

### Decisions (Kent, 2026-09-08, via `/grill-me`)

1. **The chip inherits the existing 2 s auto-restitch.** One timing rule across both
   surfaces. Two surfaces editing one field must not have two timing rules.
2. **Where a border is provably inert, the dead options are not offered — with a stated
   reason.** The same repair is applied to the panel's dropdown.
3. **An interior hit test is added**, so clicking a shape's body selects it. Guarded: an
   interior hit may select, never start a geometry drag.
4. **The chip is Content-step only**, single selection, service healthy. Hoisting the
   debounce to `App.svelte` is filed, not done here.
5. **The timer-death bug is fixed**, scoped to remount-within-session.
6. **A per-shape echo is added to the review payload**, so the chip can report what was
   actually sewn rather than only what was asked for.

### Why decision 2 matters most

On a satin-tier shape a border override is a **total no-op**. `stage7_sequence.py` returns at
`:1549`, `:1590` and `:1634` (run tier, width floor, satin) — all of them before the border
block reads `p.region.meta.get("border")` at `:1972`. Kent's real client logos are
satin-dominated (`real-artwork-trim-truth`). So the default outcome of using this chip on a
real logo, unfixed, is: set Auto border → burn a full restitch → get a byte-identical design
→ chip still reads "Auto border". The panel's existing dropdown has this same hole today.

Tier is already on the wire and needs no new Python: `app.py:531 _sew_facts` reads it off the
**emitted plan**, not a prediction, and `app/src/lib/digitizer.js:948` already stores it as
`row.tier`.

**Explicitly rejected:** making "Auto border" on a satin shape also flip its tier to fill. A
border control that silently restructures every stitch in a shape is the kind of hidden
coupling that costs a sew-out to discover.

### Why decision 3 matters

"Click a shape" is not a gesture that exists today. `hitOverlay`
(`app/src/lib/shapeOverlay.js:291`) matches only within `NODE_GRAB_PX = 9` of a vertex or
`EDGE_GRAB_PX = 6` of a segment — there is no interior test. Shape outlines are **off by
default** (`EmbroideryField.svelte:140`). And an interior click clears the selection and
starts an element drag. The chip would otherwise be reachable only by hitting an invisible
hairline.

The new logic goes in `shapeOverlay.js` because it is pure and already has
`shapeOverlay.spec.js`. There is **no** `EmbroideryField.spec.js`, so anything placed in the
component is effectively untestable in this repo.

### Why decision 4 matters

`EmbroideryField` renders on **every** step (`App.svelte:37`, and see the comment at `:563`
— *"EmbroideryField exposes on EVERY step"*). `DigitizePanel` — which owns
`RESTITCH_IDLE_MS` (`:428`), `scheduleRestitch` and `runDigitize` — mounts only under
`step === "content"`. A chip edit made on Garment, Create or Download would persist, hatch
the element stale forever, and never restitch. Download is exactly where a stale result
becomes a stitch file, and there is no gate there.

### Why decision 5 matters

`onDestroy(() => clearTimeout(restitchTimer))` (`DigitizePanel.svelte:450`) kills an armed
timer on step change, Next, multi-select, or element switch (`ContentStep.svelte:292`'s
`{#key el.id}`). On remount, `prevEditsKey` re-seeds from the already-dirty element (`:430`),
so the watcher sees no change and never re-fires. Edit a border, click Next inside 2 seconds,
and that edit is **permanently never sewn**. This is pre-existing and bites the panel today;
the chip makes it easy to hit.

Scoped to remount-within-session, so that opening a saved design with unapplied edits does
not start digitizing it on arrival.

## Design

### Files

| file | change |
|---|---|
| `app/src/lib/shapeOverlay.js` | interior hit kind; pure chip-anchor function (drawing px → CSS px, converted explicitly) |
| `app/src/ui/EmbroideryField.svelte` | the chip; clamped `.hoop` child mirroring `.fieldmenu`; clear `selectedShapeId` on element change |
| `app/src/ui/DigitizePanel.svelte` | lift `setOverride`/`overrideBorder` to `lib/`; inert-option repair; timer fix; delete the stale restitch comment at `:423` |
| `digitizer/digitizer_service/app.py` | one read-only `border_sewn` field on the review shape |
| `app/src/lib/digitizer.js` | carry `border_sewn` through `reviewFromJob`; contract test |

### Data flow

`pointerdown` → `hitOverlay` (now with an interior kind) → `selectedShapeId`
→ chip change → `dispatch("elupdate", { id, patch: { shapeOverrides } })`
→ `App.svelte:515 elUpdate` → `element.shapeOverrides`
→ `buildDigitizeConfig` → `cfg.shape_overrides` → service → `meta["border"]` → stage 7.

### Implementation choices (not Kent's to make, recorded so they are not re-derived)

- **Native `<select>`**, the same control the panel uses for the identical field. It inherits
  the Delete/Backspace guard for free (that handler already skips `SELECT`) and gets
  OS-native keyboard and screen-reader behaviour.
- **Chip is a clamped `.hoop` child**, mirroring `.fieldmenu`'s structure and its capture-phase
  outside-press dismissal — but **clamped**, which `.fieldmenu` is not. Unclamped positioning
  is the most likely source of an off-screen chip.
- **Drawing px → CSS px converted explicitly.** Assuming 1:1 is correct on a dpr-1 desktop
  and wrong on HiDPI, during the `ResizeObserver` catch-up frame, and in the narrow
  breakpoint.
- **Reuse `setOverride`'s prune rule**, do not copy `EmbroideryField`'s own non-pruning merge
  idiom. `setOverride` deletes any key whose value is `== null`; a copied merge would make
  "Design (…)" — the option that *removes* a border — silently do nothing while every other
  option worked.
- **Do not touch the canvas resize path.** `paint()` calls `stopSim()`, so a resize routed
  through `paint()` instead of `repaintView()` kills a starting simulator.
- **Only `theme.css` tokens that are actually defined.** `var(--x, fallback)` with an
  undefined name silently renders a bespoke value; there are already 3 such names at 24 call
  sites and this change adds none.

### Bugs closed beyond the feature

- The cancelled-restitch data-loss path (decision 5).
- `selectedShapeId` leaking across a digitized → digitized element switch, so the chip would
  anchor to a shape that is not there and dirty the wrong element.
- The panel's Border dropdown offering inert options on satin shapes.
- The stale comments at `DigitizePanel.svelte:422-425` (an edit-restitch is a full stage 0–7
  run with *"no useful cache … guaranteed miss"*) and `:678` (*"only restitch on Apply"*,
  contradicted by the debounce sitting 250 lines above it and by the UI's own
  *"Restitching on its own in a moment"*). `digitizer_service/jobs.py:81`
  `EDIT_KEYS` strips `shape_overrides` out of the `generation_key`, so stages 0–4 replay from
  the generation cache. That comment sent one session (2026-09-08, this one) to the wrong
  cost model while designing the waiting UX.

## Out of scope, filed

- **Hoist the debounce and restitch to `App.svelte`**, where `elUpdate` already funnels every
  patch, so the chip works on every step. Relocates the most load-bearing timer in the app
  plus `runDigitize`'s phase / `rerunWanted` / error ownership. Its own PR.
- `hitOverlay`'s node branch returns the **first** outline within 9 px in array order, not the
  nearest, so on a shared edge it picks the wrong shape.
- Deleted and unstitched shapes are invisible but still hit-testable; `deleteSelectedShape`
  already acts on shapes that cannot be seen.
- **Border double-draw** — one shared seam drawn once, not once per side. The structural half
  of the original diagnosis; needs no discriminator and no calibration.
- **Curve serration** — the flash dot sews as a visible sawtooth. Kent's standing *"shapes are
  accurate but smoothness is not"*.

## Testing

- Unit, `app/src/lib/shapeOverlay.spec.js`: interior hit; anchor placement; clamping at all
  four edges; drawing→CSS px conversion at dpr ≠ 1.
- Unit, lifted `setOverride`: the prune rule, including "Design (…)" removing a key.
- Contract: `border_sewn` survives `reviewFromJob`; unknown border spellings still dropped by
  `SHAPE_BORDERS` (`digitizer.js:247`).
- Python: `_review_payload` emits `border_sewn` with the right value for a satin shape (none,
  with reason), a bordered fill shape, and a too-narrow shape.
- Every spec watched **red before green**. A spec in this app has already passed with the bug
  re-introduced (`studio-display-layer-2026-08-25`).
- Then driven in a real browser reading **computed** styles, not source — the last four UI
  defects here were invisible in the rule being read.

## Risk

This is a UI affordance. It makes an existing capability findable and honest. **It does not
improve a single stitch.** The two geometry defects underneath — double-draw and serration —
survive it, and on the Instagram logo the logo-only recipe above is what changes the sewn
output today.
