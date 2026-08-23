# Shade-path palette binding — the decision half of the palette escape

**Status: OPEN — Kent decides.** This doc lays out options; it deliberately
builds nothing. Companion to the mechanical half landed the same day (branch
`claude/embot-session-setup-30fk7w-palette-binding`): `revalidate_threads` now
re-snaps photo-route shapes *within* the selected palette, which took
region-level out-of-palette spools to 0 on all four acceptance portraits.
This doc is about the OTHER escape hatch, which that branch deliberately
left open.

## The remaining escape, measured (post-region-fix, four real portraits)

On the photo route (`forced_class="photo_subject"`, streamline layered), each
tonally-split region decomposes into 3–5 shades and each shade snaps to the
FULL ~400-spool chart independently of `select_palette`'s choice
(`stage6_streamline.py` `_shade_layers` → `chart.nearest_index(c)` per shade
→ `shade_thread_index` → one `StitchBlock` per distinct shade spool in
`stage7_sequence._shade_blocks`). `config.py`'s F3 note (2026-08-19) named
this open on the owl (28 vs 14 spools); today's portraits connect it to
machine stops and the cone list.

| photo             | palette | block-level threads | shade spools OUTSIDE the palette |
|-------------------|--------:|--------------------:|---------------------------------:|
| sparkler_dusk     | 15      | 43                  | 28                               |
| boat_dog_toddler  | 12      | 45                  | 33                               |
| baby_deck_laugh   | 12      | 50                  | 38                               |
| face_closeup_blur | 7       | 14                  | 8                                |

Two operator-facing consequences: the colour list under-names what sews
(12 lines, 50 cones on baby), and shades can also ORPHAN a listed cone —
on `face_closeup_blur`, palette cone `1565` sews **zero** stitches because
every shade of its regions snapped elsewhere, so the list over-names too.

Why this is NOT mechanically bindable the way the region half was: two
adjacent shades snapping to one palette spool re-collapse the shade
decomposition — the owl-body flat-mass defect's ghost (`config.py`,
`split_tonal_regions`: "a region IS the unit that owns a thread… sews as a
flat pale mass"). Trading shade fidelity for spool count is a quality call,
not an engineering default.

## Option (a) — bind the shade snap to the palette, merge same-spool shades

Mask `_shade_layers`' `nearest_index` to the palette (photo classes only,
same gate as the region fix); when adjacent shades land on one spool, merge
their membership tents into one honest fewer-shade layer (the block level
already buckets same-spool shades — `_shade_blocks`' own docstring — so the
sew side degrades gracefully today; the merge makes the *decomposition*
honest too, so reports and shade counts say what actually sews).

All numbers below were computed from today's post-region-fix job JSONs by
binding every block's colour to its nearest palette spool (CIEDE2000):

- **Spool delta:** block-level threads 43→15 / 45→12 / 50→12 / 14→6 —
  the cone list becomes loadable, which is the whole point.
- **Stop delta (upper-bound estimate):** adjacent same-bound-spool blocks
  merge — up to 23 / 22 / 30 / 10 stops removed from today's 75 / 68 / 78
  / 25. A precise count needs run-level grouping; an afternoon to
  instrument if this option is chosen.
- **The cost, measured:** each escaped shade moves a **median 8.0–11.2
  dE00, worst ~20** onto its nearest palette spool, and 28 / 33 / 38 / 8
  shade distinctions per portrait collapse — real, visible flattening,
  concentrated exactly where the tonal work is (faces, sky).
- **Catch:** with today's palette (sized for region means, not shades),
  (a) alone re-ships defect 1's flatness in palette-sized steps.

## Option (b) — feed shade demand into `select_palette` itself

Size/aim the palette for the shades it will have to serve: at stage 2, add
each kept region's shade Lab targets (cheap percentile proxies for the same
light/dark extremes `_shade_layers` measures later) as weighted demand
points in the k-medoids objective, so the palette *contains* the dark/light
anchors the shades need.

- **Effect:** does NOT close the escape by itself — it makes (a)'s bind
  cheap enough to be honest. (a)+(b) is the real proposal shape.
- **Cost:** palette selection starts depending on a stage-6 model (an
  ordering inversion — needs an early proxy for the darkness field), and
  `max_colors` pressure rises: 12 spools now cover regions AND shades, so
  either mid-tones get squeezed or the cap grows — a Kent call either way
  (cones cost money, stops cost time).
- **Evidence to get first:** an offline re-fit of `select_palette` on one
  captured portrait's region+shade labs (no pipeline change, an
  afternoon). If the bind-cost median drops from ~8 toward
  `PALETTE_EXCESS_DELTAE` (4.5), (a)+(b) is defensible; if not, the cap
  itself is the binding constraint and the honest options are (c) or a
  bigger cap.

## Option (c) — leave it; cap stops elsewhere

Keep full-chart shade fidelity; attack stop COUNT only (a post-hoc stop
budget merging nearest-spool blocks, or simply surfacing cone count in
Studio before export).

- **Effect:** stops can come down; the cone list stays wrong in both
  directions (under- and over-naming, above) — the defect as lived by the
  operator stands. `PALETTE_THREAD_MISMATCH` keeps firing truthfully.
- **Cheapest engineering, and the only option that keeps today's shade
  fidelity untouched.**

## What settles it

One contact-sheet run (the existing `acceptance_ab.py` harness grew arms for
exactly this) with an experimental bound-shade arm: today's route vs (a) vs
(a)+(b)-proxy, four portraits, Kent's eyes on shade flattening plus the
per-arm cone-count table. No sew-out is needed to pick a direction; a
sew-out remains the final word on whether merged shades read as banding on
cloth (ROADMAP gate 1 territory).

## Measured 2026-08-23 — the bound_shade arm, live (this branch)

The run this doc asked for exists: `variant_matrix` grew a `bound_shade` arm
(`shade_palette_bind=True` on the classical route, nothing else — the flag is
default-OFF, `config.py`), and the four portraits went through all six arms
live (`debug_out/acceptance_2026-08-23/`, contact sheet included). Kent's
verdict is still the open item; these are the instrument's readings.
Sparkler first — it is the hard case on every axis.

| photo (classical → bound) | palette | block threads | outside | stops | zero-stitch cones |
|---------------------------|--------:|--------------:|--------:|------:|------------------:|
| sparkler_dusk             | 15      | 43 → 15       | 28 → 0  | 75 → 54 | 0 → 0 |
| boat_dog_toddler          | 12      | 45 → 12       | 33 → 0  | 68 → 45 | 0 → 0 |
| baby_deck_laugh           | 12      | 50 → 12       | 38 → 0  | 78 → 47 | 0 → 0 |
| face_closeup_blur         | 7       | 14 → 6        | 8 → 0   | 25 → 16 | **1 → 1 (`1565`)** |

- **Under-naming closes completely**: bound block-level spools == the palette
  (0 outside) on all four. Stitches/trims also drop a little (e.g. sparkler
  14,662→14,290 st, 344→269 trims) — merged plateau layers trace fewer,
  longer streamline sets.
- **Over-naming does NOT fully close**: `1565` still sews zero stitches on
  face_closeup_blur even bound — binding restricts shades to the palette but
  does not force a region's shades onto its own base cone, and every shade
  of 1565's regions binds elsewhere. The cone list still over-names by one
  there; `PALETTE_THREAD_MISMATCH` fires identically on both arms (42/22/32/
  17 shapes) — that warning is per-layer naming, not the shade escape.
- **Stop delta vs the estimate**: measured removals 21/23/31/9 against the
  "up to 23/22/30/10" upper bounds — boat and baby beat the bound by one
  (the estimate modelled adjacent-block merges only; the real decomposition
  merge also changes run interleaving).
- **The cost, measured on the real code path** (per escaped shade unit, the
  shade's own Lab, live masked snap — instrumented run of this branch):
  median dE00 **11.9 / 8.3 / 7.5 / 8.5** (sparkler/boat/baby/face), worst
  **19.8 / 15.9 / 19.7 / 15.0**. The plan-doc estimate (block-colour method:
  median 8.0–11.2, worst ~20) **holds** — re-run live it reads 11.4/8.5/8.0/
  7.5 med, 19.8/14.8/19.4/15.0 worst. Sparkler is the top of the band both
  ways. Secondary reading: the *added* perceptual error vs the shade's own
  unbound spool (dE00-to-bound minus dE00-to-unbound at the shade lab) is
  median 3.9/3.4/2.2/2.0, worst 19.5/11.8/17.2/7.2.
- **Shade distinctions collapsed**: block level, exactly the table above —
  28/33/38/8 distinct spools gone. Decomposition level (the honest merge in
  `_shade_layers`): 97/54/111/31 of 189/133/239/57 shade units merge away;
  distinct decomposition spools 47→15, 45→12, 54→12, 15→7.

Flag OFF byte-identity held everywhere it is pinned (full suite green but
for the three known Linux environment goldens, unchanged pre/post-branch;
classical arm reproduces this doc's own table exactly).
