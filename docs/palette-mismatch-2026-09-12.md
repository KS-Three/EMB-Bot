# The review screen's cone list, re-measured — defect 30 (2026-09-12)

**Re-measured on tree `ee41697`** (`digitizer/` engine sources untouched since
`12078c1`; the two commits on top of it are DOCTRINE prose and a JS crossval
test). Python 3.12.3, `digitizer/.venv/bin/python`.

**Read-only session.** Nothing in `digitizer_core/`, `digitizer/tools/` or
`app/` was edited. The fix in §6 is a proposal, not a change.

> **STATUS 2026-09-12, added after the fact: §6 IS BUILT.** Kent ruled the
> same day, and it shipped on this branch as `cfg.layer_palette_from_regions`
> — `stage3_segment.layer_palette_threads`, **now DEFAULT ON** (Kent flipped
> it 2026-09-12 on the corpus pass he asked for first:
> `docs/palette-flip-corpus-2026-09-12.md`), plus the phantom
> column §4 asks for on `tools/palette_mismatch.py`. **The measurement above
> still stands as written** (every number taken on tree `ee41697` with the
> engine unmodified), but §6 is no longer open work. Read it as the rationale
> for what is now in the tree, not as a proposal waiting for someone.

## 0. The short version

| claim in MASTER_SCOPE defect 30 (measured 2026-09-07) | today |
|---|---|
| `PALETTE_THREAD_MISMATCH` fires on **6 of 26** fixtures | **3 of 26** |
| **34 shapes** | **24 shapes**, of which only **6 actually sew** (largest 7.2 mm²) |
| "on **all six** fixtures the thread those shapes sew is on no review layer at all" | **0 of 3** — every sewn thread IS on some review layer, just not the layer that names it |
| the survivor is "the re-snap whose target NO layer declares" | **not one surviving shape is a bare re-snap.** Every diverged region on the corpus carries `color_cap_merged_from`; `enforce_color_cap` is the producer now |
| "Nothing renders the layer list as a cone list … customer-visible impact today is nil" | **still true, and re-checked consumer by consumer** (§3) |
| (not in the entry) | at the Studio's shipped `max_colors=6`, **76 diverged regions on two real-customer fixtures** — three times the published corpus number (§1.2) |

The entry went stale on **2026-09-10**, when Kent flipped the colour bundle
(`26627a2` — `enforce_color_cap`, `bind_resnap_all_classes`,
`revalidate_small_shapes`, `resnap_mask_matches_grader` all ON). That commit
updated MASTER_SCOPE defects 15, 28 and 31. It did not touch 30, whose numbers
and whose named mechanism both moved underneath it.

**And the instrument undercounts the thing that actually matters.**
`PALETTE_THREAD_MISMATCH` only sees a region whose layer names a different
cone. It is blind to a layer that names a cone **no region sews at all** — the
phantom entry — which is the direction that would sell a customer a spool.
**Phantom cones are on 9 of 26 fixtures (14 cone entries), and 6 of those 9
never fire the warning at all.**

## 1. What I ran

```
cd digitizer && .venv/bin/python -m tools.palette_mismatch
```

Verbatim output:

```
fixture                                  shapes  layers
----------------------------------------------------------------------------------------
photo/drone_render.png                       12  [5, 6, 14, 15]
                                           the layer lists ['0015', '0931', '1565', '2564'], the shapes sew ['0111', '0145', '1310']
photo/summit_badge.png                        7  [12]
                                           the layer lists ['0134'], the shapes sew ['4174']
photo/logo_golden_tee.jpg                     5  [0, 13]
                                           the layer lists ['0015', '0230'], the shapes sew ['0532', '3971']

3 of 26 fixtures fire PALETTE_THREAD_MISMATCH, and on 0 of them the thread those shapes sew is on NO
review layer at all — so the review screen cannot show it, not merely show it in the wrong place.
The OPERATOR list (plan.palette against plan.blocks) is consistent on 26 of 26 — checked, not assumed.
Everything above is the REVIEW screen's per-layer list, which is what a user reorders and recolours by.
```

3 of 26, 12 + 7 + 5 = **24 shapes**. The operator list is still 26 of 26
consistent, so the one claim in defect 30 that was load-bearing for
"harmless at the machine" survives unchanged.

Because the tool only reports fixtures that FIRE, I ran a second, read-only
audit over the same 26 fixtures at the same config
(`PipelineConfig(target_width_mm=80.0, garment_id="left_chest")`, engine
default `max_colors=12`), comparing the whole per-layer list against the whole
per-block list and attributing every divergence to the pass that caused it
(`digitizer/tools/palette_mismatch.py` is the shipped instrument; my audit
script lives only in the session scratchpad and is reproduced in §7).

### 1.1 The 12 fixtures of 26 where the two lists differ at all

`phantom` = a cone the LAYER list names that no block sews. `missing` = a cone
a block sews that the layer list does not name. `diverged` = regions whose own
cone differs from their layer's entry (this is the warning's population).
The other 14 fixtures are clean in all three columns.

| fixture | layers | blocks | phantom | missing | diverged | producer |
|---|---:|---:|---|---|---:|---|
| `logo_alpha.png` | 6 | 6 | `0020` | — | 0 | unstitched layer |
| `logo_whitebg.png` | 6 | 6 | `0015` | — | 0 | unstitched layer |
| `photo/drone_render.png` | 16 | 13 | `0015 0931 1565 2564` | — | **12** | colour cap (11 cap, 1 cap+resnap) |
| `photo/enthusiast_logo.png` | 3 | 3 | `0015` | — | 0 | unstitched layer |
| `photo/gradient_ramp_linear.png` | 1 | 6 | — | 4 shades | 0 | blend tier, by design |
| `photo/gradient_ramp_radial.png` | 1 | 6 | — | 4 shades | 0 | blend tier, by design |
| `photo/region_blobs.png` | 4 | 17 | `2153 3630` | 13 shades | 0 | blend tier, by design |
| `photo/repro_gradient_white_icon.png` | 2 | 6 | — | 3 shades | 0 | blend tier, by design |
| `photo/summit_badge.png` | 13 | 13 | `0134` | — | **7** | colour cap |
| `logo_script_tires.png` | 2 | 2 | `0015` | — | 0 | unstitched layer |
| `photo/logo_gaulke_roofing.png` | 3 | 3 | `0020` | — | 0 | unstitched layer |
| `photo/logo_golden_tee.jpg` | 14 | 12 | `0015 0230` | — | **5** | colour cap |

Totals at `max_colors=12`:

- **diverged: 24 regions on 3 fixtures** — matching `tools/palette_mismatch.py`
  exactly (12 + 7 + 5). **Producer attribution: 24 of 24 carry
  `color_cap_merged_from`. Zero are re-snap-only.**
- **only 6 of those 24 regions actually sew.** The rest are `stitched: False`
  (sub-millimetre enclosed shards). Largest SEWN diverged region on the whole
  corpus: **7.2 mm²** on `drone_render`. `logo_golden_tee`'s 304.7 mm²
  diverged shape does not sew.
- **phantom: 9 of 26 fixtures, 14 cone entries** — three times the warning's
  reach, and **6 of those 9 fixtures never fire the warning at all**.
- missing: 4 fixtures, all blend/shade tier, all with `diverged = 0`. **No
  sewn cone is absent from the layer list because of a divergence** — which is
  the tool's "0 of 26 … on NO review layer at all", independently reproduced.
- `reviewFromJob`'s grey-swatch hole (§4.4): **0 regions corpus-wide.**
- operator list (`plan.palette` vs `plan.blocks`): **26 of 26 consistent.**

`photo/repro_gradient_white_icon.png` — fix #6.3's own motivating fixture, and
the one `rehome_resnapped_regions`' docstring names as live proof — now
diverges on **nothing**. The re-snap half of this defect is closed on the
corpus.

The `producer` column is read off the phantom layer's own regions, not
inferred:

```
logo_alpha        phantom 0020 -> layer  4: all regions carry 0020, none stitched
enthusiast_logo   phantom 0015 -> layer  2: all carry 0015, none stitched (4)
logo_script_tires phantom 0015 -> layer  0: all carry 0015, none stitched (2)
gaulke_roofing    phantom 0020 -> layer  2: all carry 0020, none stitched (45)
region_blobs      phantom 2153 -> layer  1: one STITCHED region carrying 2153  (blend shades)
drone_render      phantom 2564 -> layer  5: regions carry 0111, STITCHED       (cap)
drone_render      phantom 0015 -> layer 14: regions carry 0145, STITCHED       (cap)
summit_badge      phantom 0134 -> layer 12: regions carry 4174, none stitched  (cap)
golden_tee        phantom 0230 -> layer 13: region carries 0532, STITCHED      (cap)
```

So the phantom has two genuinely different shapes: a layer that **sews
nothing** (its cone is honest but unused) and a layer that **sews something
else** (its cone is simply wrong). Only the second is a labelling defect; §6
fixes that one and deliberately leaves the first alone.

Two worked layers, straight out of the audit:

```
summit_badge  COLOR_CAP_APPLIED 13 -> 12, 1 dropped, 7 shapes moved
  layer 12 lists 0134 ; its 7 regions all sew 4174 (cap merged 0134 -> 4174),
  every one stitched=False, largest 1.2 mm2        -> phantom cone 0134

drone_render  COLOR_CAP_APPLIED 16 -> 12, 4 dropped, 12 shapes moved
  layer  5 lists 2564 ; regions sew 0111, stitched, 3.2 and 2.4 mm2
  layer  6 lists 1565 ; regions sew 0111, unstitched
                                                   -> phantoms 0015 0931 1565 2564
```

### 1.2 At the setting the Studio actually ships (`max_colors=6`)

Every number above is at the engine default of 12. Studio's slider defaults to
**6** (`DigitizePanel.svelte:1556`, `PipelineConfig.max_colors = 12`). The cap
is the producer, so the shipped setting is the one that matters. Re-run over
the seven real-customer fixtures plus `logo_whitebg`:

| fixture | layers | blocks | phantom | diverged | producer |
|---|---:|---:|---|---:|---|
| `logo_whitebg.png` | 6 | 6 | `0015` | 0 | unstitched layer |
| `becker_marine_logo.png` | 1 | 2 | — | 0 | — |
| `logo_script_tires.png` | 2 | 2 | `0015` | 0 | unstitched layer |
| `photo/logo_bridge_bar.jpg` | 6 | 6 | — | 0 | — |
| `photo/logo_gaulke_roofing.png` | 3 | 3 | `0020` | 0 | unstitched layer |
| `photo/logo_golden_tee.jpg` | 7 | 8 | `0015` | **5** | colour cap |
| `photo/logo_hotel_fremont.webp` | 3 | 4 | — | 0 | — |
| `photo/screenshot_phone_ui_golke.jpg` | 7 | 7 | `0015` | **71** | colour cap (70 cap, 1 cap+resnap) |

**76 diverged regions on two fixtures — against 24 on the whole corpus at 12.**
`screenshot_phone_ui_golke` alone triples the published number: its cap fires
7 → 6 and moves 71 shapes, layer 6 lists `0015` while its regions sew `3971`.
Only 5 of the 76 sew (largest 2.9 mm²), and the grey-swatch population is
still 0. Phantoms: 5 of 8 fixtures.

**The measured population of this defect is roughly three times larger at the
setting customers use than at the setting it has always been measured on.**

## 2. The mechanism, line by line

`result.palette` is built once, at the very end of `run_stages`:

- `digitizer/digitizer_core/pipeline.py:950` —
  `thread_indices, layer_warnings = compact_layers(regions, quant_indices)`
- `digitizer/digitizer_core/pipeline.py:1188` —
  `palette = [_cone(chart, t) for t in thread_indices]`

`thread_indices` is **stage 2's quantize-time layer→cone list**, filtered and
reordered. `compact_layers`
(`digitizer/digitizer_core/stage3_segment.py:589-621`) drops a slot only when a
layer has **no regions left**; it never re-reads a surviving region's thread.
So `palette[i]` answers "what colour did stage 2 call layer i", not "what
cone do the shapes in layer i sew".

Three passes change a region's thread after stage 2, and **none of them
writes `meta["layer"]`**:

| pass | file:line | writes | stamp it leaves |
|---|---|---|---|
| `revalidate_threads` | `stage4_vectorize.py:786-788` | `thread_index`, `thread_number` | `meta["thread_resnapped_de00"]` |
| `enforce_color_cap` | `stage4_vectorize.py:884-888` | `thread_index`, `thread_number` | `meta["color_cap_merged_from"]` |
| `apply_shape_edits` (recolor) | `regions.py:313-327` | `thread_index`, `thread_number` **and `meta["layer"]`** | — |

Only the third moves the layer with the thread, which is why a review-screen
recolor never produces this defect.

One pass repairs the divergence — `rehome_resnapped_regions`
(`stage4_vectorize.py:939-951`) — and it is **keyed on the re-snap stamp
alone**:

```python
    for r in regions:
        if "thread_resnapped_de00" not in r.meta or r.meta.get("step_key"):
            continue
        target = home.get(r.thread_index)
```

Two consequences, and together they are the whole of today's defect:

1. **The colour cap runs AFTER the rehome.** `pipeline.py:705` re-snaps,
   `pipeline.py:717` rehomes, `pipeline.py:728-735` caps. A region the cap
   remaps is therefore never rehomed — and could not be even if the order were
   swapped, because it carries `color_cap_merged_from`, not
   `thread_resnapped_de00`. **This is the producer of every diverged region on
   the corpus today.**
2. **A layer whose regions all leave still keeps its slot**, and its slot still
   names the cone they left. That is the phantom entry, and it has a second,
   older source that has nothing to do with threads moving at all: a layer
   whose every region is unstitched (`SHAPES_LEFT_UNSEWN`, the
   enclosed-background default). `tests/test_unsewn_shapes_are_loud.py`
   records that exact failure being fixed in 2026-08-14 — **for the plan's
   palette. The layer palette was never fixed**, and still is not. Measured
   above: that source alone accounts for 6 of the 9 phantom fixtures.

A third phantom source is **legitimate and must be left alone**: a blend/tonal
layer (`region_blobs.png`) keeps its regions' base cone while the blocks it
produces are `shade_thread_index` shades, so the cone it names is genuinely
never loaded. That is the contract `StitchPlan.palette` and `_stats_payload`
both describe, not a defect — which is why the invariant in §6 is about the
layer's own regions and never about the block list.

The warning itself (`pipeline.py:1207-1231`) is computed per REGION against
`palette[r.meta["layer"]]["number"]`, with an explicit exemption for a user
`layer` override. It is correct about what it measures. It simply does not
measure the phantom: a layer nobody is left in cannot produce a mismatched
region.

## 3. Is it harmless? Yes — and the fixture that shows why that is not obvious

**The property that makes it harmless is one sentence: every surface that
prints a cone to a human reads `stats.blocks` or `design.colors`, both built
from `plan.blocks`, and nothing reads `review.palette` as a list.** Not "the
list happens to be right" — the list is wrong, and nobody reads it.

Consumer inventory, re-checked today by grep over `app/src`, `digitizer/tools`,
`digitizer_core` and `digitizer_service`:

| surface | what it prints | source |
|---|---|---|
| Quality report, "Threads to load" (`QualityReport.svelte:111-155, 205-216`) | the shopping list, one row per SPOOL, folded by number since 2026-09-11 | `stats.blocks` + `thread_m_by_color` |
| Download step, "Threads" (`DownloadStep.svelte:233-236`) | one row per BLOCK, labelled "block N" | `design.colors` (adapter, per block) |
| Worksheet PDF (`DownloadStep.svelte:396-410`) | the sheet that goes to the machine | `design.colors` |
| Sequencer rows (`DigitizePanel.svelte:1812-1836`, `digitizer.js:464-482`) | one row per LAYER, labelled `blockRows[0].threadNumber` — the shape's OWN number | per-shape review fields |
| Sequencer "sews as N threads" (`digitizer.js:491-495`) | the cones a layer really sews | `stats.blocks` |
| Layers list swatch/name (`DigitizePanel.svelte:2120, 2148`) | per shape | per-shape `rgb`/`threadNumber` |
| `reviewFromJob` (`digitizer.js:933-947`) | resolves a shape's colour | `byNumber.get(s.thread_number)` **by number, not by index**, with a `stats.blocks` fallback keyed by `sew_block` |
| `reviewFromJob` | `brandId` | `palette[0].brand_id` — uniform across the list, so a wrong entry cannot change it |
| `QualityReport.svelte:114-117` | — | refuses the layer palette in a comment |
| every engine instrument (`flip_sheet.py`, `halo_spools.py`, `cone_revisits.py`, `preflight.py:1363`) | cone counts | `plan.palette` |

`review.palette` has exactly **two** readers in the whole product, and neither
is positional.

### The walkthrough — `logo_whitebg.png`, and it does NOT fire the warning

```
cd digitizer && PYTHONPATH=$PWD .venv/bin/python  # script in §7
# PipelineConfig(target_width_mm=80.0) — tests/conftest.cfg() exactly
```

```
REVIEW palette (what a per-layer cone list would print):
   0  1704 Candy Apple
   1  3902 Colonial Blue
   2  1305 Fox Fire
   3  2905 Iris Blue
   4  0015 White          <-- sewn by nothing
   5  5510 Emerald

stats.blocks folded by spool (what QualityReport prints):
   1704 Candy Apple   6.2 m
   3902 Colonial Blue   5.2 m
   1305 Fox Fire   1.1 m
   2905 Iris Blue   1.1 m
   5510 Emerald   0.6 m

SHAPES_LEFT_UNSEWN: 1 shape (159.6 mm², largest 159.6 mm²) in thread 0015 was
planned but not sewn — enclosed background, showing the garment through.
PALETTE_THREAD_MISMATCH: not emitted
```

Layer 4 holds one region, the enclosed ring hole, `stitched=False`. Its cone
`0015 White` is in the review list and in no block.

**The customer sees the right thing: five spools, 14.2 m.** A cone list built
from `review.palette` would say six, and the sixth is a white spool bought for
a hole that is meant to show the garment through. The warning that exists for
this defect says nothing, because no region in that layer disagrees with its
label — they all sew `0015`; they just do not sew.

So: **today, no. A customer is never shown a spool they do not need, and never
missing one they do.** Not because the list is right, but because the list is
unread.

## 4. What would break that property

In rough order of how easily it happens:

1. **One new consumer.** Any screen that renders `review.palette` — a "colours
   in this design" chip row, a layer legend, a print sheet built off the
   review payload instead of the design — ships the phantom immediately. It
   looks like the obvious list to use: it is per layer, it is in sew order,
   and it is the list the review screen already has in hand.
2. **A positional read.** `palette[shape.layer]` is the natural way to colour a
   layer row, and it is wrong for exactly the 24 diverged shapes above. This
   is the same mistake `StitchPlan.palette`'s comment records shipping
   `golf_hat`'s black block as "0020 Tangerine" until 2026-08-14.
3. **A COUNT, not even a list.** `review.palette.length` looks like "how many
   colours this design uses" and is not: `drone_render` at 12 reads **16
   layers against 13 blocks and 12 cones**, so anything quoting it would
   contradict the "Colors (max N)" promise the cap exists to keep. This is
   the cheapest possible way to ship the bug — one `.length`.
4. **A third-party integrator.** The service is an HTTP API in a public repo
   and the field is called `palette`. Nothing on the wire says it is not the
   cone list; `stats.blocks`' own docstring says so, in the server's source.
5. **`stats.blocks` going missing.** `reviewFromJob`'s fallback chain is
   `byNumber.get(thread_number) || cones[sew_block].rgb || null`, and
   `effRgb` turns `null` into grey `#888`. A shape whose cone is off the
   review list AND which produced no stitches renders grey. **Measured: 0
   regions, at both 12 and 6 colours** (§1) — but that is a coincidence of
   today's data, not a guarantee: it needs only a sewn cone absent from the
   layer list, which is exactly what the re-snap used to produce on all six
   fixtures a week ago.
6. **The Studio ships `max_colors=6`; every published number for this defect
   is at the engine's 12.** Measured in §1.2: **76 diverged regions on two
   real-customer fixtures at 6, against 24 on the whole corpus at 12**. The
   defect is already three times bigger than its own entry says, in
   production, today. Nothing about the harm changes — no consumer reads the
   list either way — but the number a future reader would quote does.

## 5. What in defect 30 is contradicted

Flagging these because a stale claim here is worse than no claim:

1. **"fires on 6 of 26 fixtures (34 shapes)"** — now 3 of 26, 24 shapes.
2. **"on all six fixtures the thread those shapes sew is on no review layer at
   all"** — now 0 of 3. The tool's own summary line says so. This was the
   sentence that made the defect sound like a missing spool; it is no longer
   true in either direction on this corpus.
3. **"`revalidate_threads` re-snaps individual shapes … what survives is the
   re-snap whose target NO layer declares"** — the surviving population is not
   re-snaps. It is `enforce_color_cap` remaps, a pass that did not exist as a
   default when the entry was written and that `rehome_resnapped_regions`
   structurally cannot repair (wrong stamp, wrong order).
4. **"Kept as a regression detector"** — there is no detector. No test asserts
   the warning fires, its count, or the invariant; `grep PALETTE_THREAD_MISMATCH
   digitizer/tests/` finds two docstring mentions and nothing else. The only
   instrument is a corpus tool that takes 10-25 minutes by hand.
5. **Scope.** The entry frames the defect as the mismatch warning's population.
   The phantom entry — a layer naming a cone nothing sews — is larger, is what
   would actually cost a customer money, and is invisible to the warning.

Two code comments also still carry the claim DOCTRINE recorded as false on
2026-09-07 — that the operator loads the wrong cone:

- `digitizer/digitizer_core/pipeline.py:1197-1199`: *"The operator loads a cone
  that sews nothing while the thread that IS sewn is missing from the list"*.
- `digitizer/digitizer_core/warnings_codes.py:161-162`: *"it is the palette,
  i.e. the cone list a human loads and the review screen shows, that is
  wrong"*.

The operator loads `plan.palette`. Both sentences should say "the review
screen's per-layer list".

The same comment block's worked example is stale too:
`pipeline.py:1195-1196` cites *"drone_render's L1 carries re-snapped t0/t17 in
t16's layer, live proof"*. `drone_render` still diverges — on 12 regions —
but **the producer is the cap, not the re-snap** (§1.1), and the affected
layers are 5, 6, 14 and 15.

And one test name is a false claim about its own body:
`digitizer/tests/test_pipeline.py:30` —
`test_palette_never_lists_a_thread_with_nothing_to_sew` — asserts only that
`len(result.palette) == len(layers)`. It passes on `logo_whitebg`, whose
palette lists `0015 White` with nothing to sew (§3).

### 5.1 A replacement for defect 30, ready to paste

MASTER_SCOPE is at its 800-line budget and this session did not edit it. The
line below is one line, same as the one it replaces, so it needs no
retirement:

> 30. **The review screen's per-layer cone list names threads its layer does
> not sew — REAL, TRACKED, and currently HARMLESS.** `PALETTE_THREAD_MISMATCH`
> fires on **3 of 26** fixtures (24 shapes, only **6 of which sew**, largest
> 7.2 mm²) — down from 6/26 and 34 when the colour bundle flipped on
> 2026-09-10, which also **changed the mechanism**: all 24 carry
> `color_cap_merged_from`, none is a bare re-snap, because `enforce_color_cap`
> runs AFTER `rehome_resnapped_regions` and carries the wrong stamp for it to
> repair. The old claim that the sewn thread is on no review layer is **false
> on all three** (0 of 3). **The warning also undercounts the defect**: a
> layer whose cone NO block sews is invisible to it and sits on **9 of 26**
> fixtures (14 cones), 6 of them silent — `logo_whitebg` lists `0015 White`
> for an unstitched ring hole while the machine loads five spools. At the
> Studio's shipped `max_colors=6` the divergence is **76 regions on two real
> customer fixtures**. Still harmless for one reason only: **every
> customer-facing cone list reads `stats.blocks` or `design.colors`, and
> `review.palette` has exactly two readers, neither positional** — one
> `.length` or one layer legend ends that. Fix, tests and consumer inventory:
> `docs/palette-mismatch-2026-09-12.md`. *(re-measured 2026-09-12 —
> `digitizer/tools/palette_mismatch.py` + a per-layer audit; tree `ee41697`)*

## 6. The fix — one sitting, review-only, byte-identical for exports

**Rule: `palette[i]` must name a cone that a region in layer i actually
carries.** Derive it from the regions instead of from stage 2's memory.

**Where.** `digitizer/digitizer_core/pipeline.py:1188`, the single line

```python
    palette = [_cone(chart, t) for t in thread_indices]
```

becomes a call to a new function next to `compact_layers` in
`digitizer/digitizer_core/stage3_segment.py` (same file, same subject — that
function already owns the layer↔cone list):

```python
def layer_palette_threads(regions, thread_indices, shape_overrides):
    """The cone each layer actually carries -> a thread index per layer.

    `thread_indices` is stage 2's memory of what a layer WAS. Three passes
    move a region's thread without moving the region (revalidate_threads,
    enforce_color_cap, and any future one), and `rehome_resnapped_regions`
    repairs only the first. Elect a representative instead:

      * the largest STITCHED region in the layer wins; a layer that sews
        nothing falls back to its largest region, stitched or not;
      * a shape carrying an explicit `layer` override is NOT eligible — the
        user put it there, it does not get to rename the layer (the same
        exemption PALETTE_THREAD_MISMATCH already makes);
      * a layer with no eligible region keeps `thread_indices[i]`, which is
        today's answer, so nothing regresses.
    """
```

Tie-break on `(stitched, area_mm2, -thread_index)` — largest first, lowest
chart index on a tie, matching the earliest-wins convention used by
`rehome_resnapped_regions` and `merge_duplicate_cone_layers`.

**Flag.** `cfg.layer_palette_from_regions: bool = False`, placed in
`config.py` beside `rehome_resnapped` and `merge_duplicate_cones` (the other
two layer-repair flags), with the house sentence: *False is the pre-flip engine
byte for byte.* Flip after one corpus pass, the same shape as the colour
bundle. No ROADMAP gate applies — gate 1 is physical constants (nothing here
touches cloth), gate 3 is default-OFF **tiers**, and this is a label list.

**Blast radius is genuinely small, and that is checkable rather than asserted.**
`result.palette` feeds exactly one thing: `_review_payload["palette"]`
(`digitizer_service/app.py:587`). `plan.palette`, `design.colors`,
`thread_m_by_color`, every export and every preflight number are built from
`plan.blocks` and cannot move. Studio persistence is unaffected —
`reviewFromJob` keeps only `brandId` and per-shape fields, so no `.embproj`
migration.

**Tests that pin it** (new file `digitizer/tests/test_layer_palette.py`, plus
two edits):

1. `test_a_capped_region_does_not_leave_its_layer_naming_a_dropped_cone` —
   synthetic regions over N > `max_colors` threads, one per layer; run
   `enforce_color_cap`, build the palette; assert every palette number is
   carried by a region in its own layer. Red today on the cap path.
2. `test_a_layer_that_sews_nothing_names_its_own_shapes_cone` — the
   `logo_whitebg` ring hole: palette[4] is `0015` either way, and
   `set(palette) - set(plan.palette)` is still `{0015}`. This pins that the
   fix does NOT try to delete phantom cones — an unstitched layer is a real
   review row and must keep a real colour. **The phantom is the review list
   telling the truth about a layer that sews nothing; the fix is about the
   list telling the truth, not about hiding the row.**
   The same test should cover the blend case (`region_blobs.png`, §1): a
   tonal layer's regions keep their base cone while the blocks they produce
   are `shade_thread_index` shades, so its listed cone is legitimately
   unsewn. **So the invariant to pin is `palette[i].number ∈ {r.thread_number
   for r in layer i}` — never `palette ⊆ block cones`, which the blend tier
   breaks by design.**
3. `test_a_user_layer_override_cannot_rename_the_layer_it_joins` — a large
   shape moved by `shape_overrides[sid]["layer"]` into another layer leaves
   that layer's palette entry unchanged.
4. `test_the_layer_palette_is_review_only` — on one flat and one gradient
   fixture, `plan.palette`, `plan.blocks` digests and `plan_to_design`'s
   `colors` are identical with the flag OFF and ON.
5. Rename `test_pipeline.py::test_palette_never_lists_a_thread_with_nothing_to_sew`
   to what it checks (`..._has_one_entry_per_layer`) and add the real
   invariant beside it: for every layer i,
   `palette[i]["number"] in {r.thread_number for r in layer i}`.
6. Extend `tools/palette_mismatch.py` to report the phantom count per fixture
   (`set(review) - set(block numbers)`), so the instrument stops being blind
   to the direction that costs money.

**Not in scope, deliberately.** `merge_duplicate_cone_layers` folds on the
DECLARED cone; after this fix two layers can carry the same DERIVED cone and
still not fold. Folding on the derived cone changes sew order and moves
goldens — a separate, measured decision.

## 7. Scripts

Both live in the session scratchpad, not in the repo — they are throwaway
readings of shipped code, and `tools/palette_mismatch.py` is the instrument
that should grow the phantom check (§6, test 6).

**The walkthrough (§3).** `PipelineConfig(target_width_mm=80.0)` is
`tests/conftest.cfg()` exactly, so the numbers are the ones the test suite
sees.

```python
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import run_stages, plan_stitches
from tests.conftest import TESTDATA

cfg = PipelineConfig(target_width_mm=80.0)
r = run_stages(TESTDATA / "logo_whitebg.png", cfg)
p = plan_stitches(r, cfg)
m = [round(v / 1000.0, 2) for v in p.stats.thread_mm_by_color]
for i, c in enumerate(r.palette):
    print(f"   {i}  {c['number']} {c['name']}")
fold, order = {}, []
for c, mm in zip(p.palette, m):          # fold by spool, as QualityReport does
    k = c["number"]
    if k not in fold:
        fold[k] = [c["name"], 0.0]; order.append(k)
    fold[k][1] += mm
for k in order:
    print(f"   {k} {fold[k][0]}   {fold[k][1]:.1f} m")
```

**The corpus audit (§1).** Per fixture: the layer list, the block list, the
set differences both ways, and — the part `tools/palette_mismatch.py` does not
have — an attribution of every diverged region to the stamp its mover left
(`color_cap_merged_from` vs `thread_resnapped_de00`).

```python
for fx in FIXTURES:
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                         max_colors=MAXC)
    result, plan = digitize(TESTDATA / fx, cfg)
    layer_cones = [str(c["number"]) for c in result.palette]
    block_cones = [str(c["number"]) for c in plan.palette]
    diverged = [r for r in result.regions
                if r.meta.get("layer") is not None
                and r.meta["layer"] < len(layer_cones)
                and layer_cones[r.meta["layer"]] != str(r.thread_number)]
    why = collections.Counter(
        "+".join([t for t, k in (("color_cap", "color_cap_merged_from"),
                                 ("resnap", "thread_resnapped_de00"))
                  if k in r.meta]) or "none"
        for r in diverged)
    print(fx, sorted(set(layer_cones) - set(block_cones)),   # phantom
              sorted(set(block_cones) - set(layer_cones)),   # missing
              len(diverged), dict(why))
```
