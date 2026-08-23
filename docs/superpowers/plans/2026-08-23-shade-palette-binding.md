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
