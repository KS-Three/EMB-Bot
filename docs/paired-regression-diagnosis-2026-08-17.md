# Paired-regression diagnosis: `bridge_lc` vs `bridge_hat`, 2026-08-17

## Verdict, up front

**KILLED, via a documented shape-pairing failure — not confirmed, and the
qualitative "different pro file" story in
`docs/satin-gate-attribution-2026-08-16.md` §6 is superseded by a more
precise mechanism.**

The hypothesis on record said: the SAME artwork shape flips to satin in both
`bridge_lc` and `bridge_hat`, and lands on ground `bridge_hat`'s pro sewed as
satin (gain) but `bridge_lc`'s pro sewed as fill (the −0.086 kappa leak). That
requires a same-shape correspondence across the two siblings' engine-side
segmentation. **No such correspondence exists for `bridge_lc`'s one
substantial flipped shape.** Two independent checks fail it:

1. **Area-only matching** (the brief's specified method) finds a numerically
   close candidate (5.2–5.4% off, mutual nearest neighbour) — but it sits on a
   **different pro artwork colour** (yellow-green vs orange), confirmed two
   ways (polygon centroid and `representative_point`, both land on the same
   colour each time). The area agreement is coincidence, not correspondence.
2. **Colour-gated matching** (require the same pro colour, then nearest by
   area) finds **no adequate same-colour candidate** in `bridge_hat`: the
   largest yellow-green shape there is 30.3 mm², 66% smaller than the
   88.2 mm² scaled target. `bridge_hat`'s yellow-green pro ground is not
   concentrated in one shape the way `bridge_lc`'s is.

Rolling the comparison up from shapes to **colours** (artwork-invariant, even
when segmentation is not) shows why: `bridge_lc`'s flip-driven leak is
**entirely on the yellow-green region** (25 of 25 graded fill cells), while
`bridge_hat`'s flip-driven gain is **entirely on the orange region** (18 of 29
graded cells satin). The promotion does not even touch the same artwork
colour in both siblings, let alone the same shape — so "which pro file we're
scored against" cannot be the operative mechanism for this pair; the two
siblings' engine segmentation of the identical artwork, rendered at two
different sizes (LC bbox 76.2×76.2 mm vs hat 63.0×63.0 mm, a 0.68 area-scale
ratio), diverges enough that the DT-irregularity/elongation promotion gate
fires on **different colour-regions** in each one. That is sufficient by
itself to produce opposite-sign deltas without invoking reference-file
identity as a separate cause.

`hotel_fremont_hat`/`hotel_fremont_patch` (step 4) can't even be tested: **zero**
shapes in either design carry `reason == "promoted_ribbon"` in the after-run
corpus CSV. The promotion touches neither design at all — consistent with
both showing kappa delta 0.000 in Task 1 — so this promotion-era data has
nothing to say about whether the same mechanism explains the historical
stage-0 (`forced=flat`, −4.3 composite) regression on that pair; that
regression came from a different code path and a different run. Not
stretched to answer here.

## Method

All commands run from each worktree's `digitizer/` directory, with
`digitizer_core.__file__` verified to resolve inside that worktree first.
`$PY` = `<repo-root>/digitizer/.venv/Scripts/python.exe`.

### Step 1 — component story for the pair

```
cd <kappa-after-worktree>/digitizer
$PY tools/pro_parity/scorecard.py --explain \
  ../parity_out/real/bridge_lc ../parity_out/real/bridge_hat
```

(Relative `real/bridge_lc` from `digitizer/` silently matches nothing —
`parity_out/` lives one level up, at the worktree root, not inside
`digitizer/`. `scorecard.py`'s `for dd in dirs: if not (Path(dd) /
"pro_stitches.csv").exists(): continue` swallows the miss with no error and
no output at all, which is exactly what happened on the first attempt: zero
lines, exit 0. Worth flagging for the next person running this brief.)

Component breakdown, both designs, `2729ea5` (after):

| component | bridge_lc | bridge_hat |
|---|---|---|
| coverage | 0.680 | 0.691 |
| direction | 0.107 (raw 0.553, chance 0.500) | 0.250 (raw 0.625, chance 0.500) |
| **sttype** | **0.148** (raw 0.520, chance 0.437) | **0.174** (raw 0.560, chance 0.467) |
| density | 0.928 | 0.961 |
| underlay | 0.759 | 0.747 |
| travel | 0.776 | 0.781 |
| **composite score** | **51.8** | **55.9** |

`coverage`, `density`, `underlay`, `travel` are all within ~0.03–0.05 of each
other between siblings — not where the divergence lives. `direction` differs
more in absolute after-run terms (0.107 vs 0.250) but that is a downstream
consequence of the same shapes being sewn satin vs fill, not an independent
cause. `sttype` is where the brief predicted the loss would concentrate, and
it does: `bridge_lc`'s own kappa fell 0.234 → 0.148 (Task 1 table) while
`bridge_hat`'s rose 0.130 → 0.174 — the pair moved in opposite directions on
exactly the corrected-kappa component the promotion targets.

### Step 2 — flipped shapes, full 15-design corpus

```
cd <kappa-after-worktree>/digitizer
$PY tools/pro_parity/gateprobe.py --features --csv corpus_after.csv \
  (all 15 real/* dirs, absolute paths)

cd <kappa-before-worktree>/digitizer
$PY tools/pro_parity/gateprobe.py --csv corpus_before.csv \
  (all 15 real/* dirs, absolute paths)
```

`kappa-before` (`26ceaa3`) does **not** support `--features` at all —
`gateprobe.py: error: unrecognized arguments: --features`. That flag was
added alongside the promotion, so the before-leg CSV carries the base
columns only (no `elongation`/`explained`/etc.), which is fine: the before
run's purpose here is only to sanity-check that `promoted_ribbon` never
appears pre-promotion, not to compute discriminators pre-promotion.

Corpus-wide: `dt_irregular` drops from 149 (before) to 89 (after), and
`promoted_ribbon` appears 60 times (after only, 0 in before) — 149−89=60,
exactly accounted for. Every design's shape *count* is identical
before/after (region boundaries come from `ours_regions.json`, unaffected by
the classifier's verdict), confirming the 85-vs-79 `bridge_lc`/`bridge_hat`
shape-count gap (below) is an artifact of segmenting two differently-sized
renders of the same artwork, not of this promotion or of the before/after
diff.

Flipped (`reason == "promoted_ribbon"`) shapes per design, graded ones only
(`pro_cells > 0`, i.e. the shape actually lands on ground the pro also sewed):

| design | total flipped | graded flipped | of those, pro-fill-dominant |
|---|---|---|---|
| `bridge_lc` | 7 | 2 | 1 |
| `bridge_hat` | 19 | 6 | 2 |
| `hotel_fremont_hat` | 0 | — | — |
| `hotel_fremont_patch` | 0 | — | — |

Full row dump for `bridge_lc`'s 7 flipped shapes (from `corpus_after.csv`):

| shape_id | area_mm² | pro_dominant | pro_satin_cells | pro_fill_cells |
|---|---|---|---|---|
| Sf4300e5b | 129.06 | fill | 7 | 25 |
| Sc1b82883 | 4.09 | none | 0 | 0 |
| Scf9cb970 | 5.38 | satin | 1 | 0 |
| Sd8b2c363 | 1.59 | none | 0 | 0 |
| S36600407 | 1.00 | none | 0 | 0 |
| S9b9dd0f6 | 1.35 | none | 0 | 0 |
| S4c18355a | 0.62 | none | 0 | 0 |

`Sf4300e5b` (129.06 mm², pro-dominant **fill**, 25 fill cells vs 7 satin) is
the entire story: it carries 25 of `bridge_lc`'s 25 total flipped-shape
pro-fill cells. Everything else is sub-6 mm² noise, mostly not landing on
graded pro ground at all (`pro_dominant == "none"`).

`bridge_hat`'s 19 flipped shapes include 6 graded; 3 of those are satin-
dominant with real cell counts (`Sb50e08ea` 30.3 mm² 7sat/1fill, `Sb5c57cdc`
83.7 mm² 11sat/7fill, `Sccaae622` 32.0 mm² 5sat/3fill), 2 are single-cell
fill noise, 1 is tied/negligible.

### Step 3 — testing the hypothesis directly

Throwaway scripts (scratchpad, not committed):
`pair_shapes.py` (v1, area-only), `pair_shapes_v2.py` (v2, colour-gated),
`pair_by_colour.py` (v3, colour-level rollup).

**v1 — area only, per the brief's stated method** (match by `area_mm2` within
5% after scaling by the design bbox-area ratio). Design bboxes (union of
`ours_regions.json` "bounds" over all shapes): `bridge_lc` 76.2×76.2 mm
(5806.4 mm²), `bridge_hat` 63.0×63.0 mm (3969.0 mm²) — scale² factor 0.6836
lc→hat. `bridge_lc`'s 85 shapes vs `bridge_hat`'s 79 — already a 7% count
gap before any classification is applied.

`Sf4300e5b` (129.06 mm² → scaled 88.25 mm² in hat's frame) nearest match:
`Sb5c57cdc` (83.70 mm², **5.4% off** — just outside the brief's 5% bar, but
by far the closest candidate; next-nearest candidates are 15%+ off). Checked
mutually: `Sb5c57cdc` scaled into lc's frame (122.4 mm²) nearest-matches
back to `Sf4300e5b` (5.2% off). A clean mutual-nearest pair by the numbers
alone.

**But it's the wrong pair.** Sampled the pro artwork colour under each
shape (nearest pro stitch, in the registered pro frame, at both the polygon
centroid and — since `Sf4300e5b`'s centroid falls *outside* its own
(non-convex) polygon — the guaranteed-inside `representative_point()`; both
methods agree):

| design | shape_id | sample point | pro colour |
|---|---|---|---|
| bridge_lc | Sf4300e5b | centroid | rgb(227, 243, 91) — yellow-green |
| bridge_lc | Sf4300e5b | representative_point | rgb(227, 243, 91) — yellow-green |
| bridge_hat | Sb5c57cdc | centroid | rgb(209, 84, 0) — orange |
| bridge_hat | Sb5c57cdc | representative_point | rgb(209, 84, 0) — orange |

Different colours, confirmed two independent ways on each side. The 5.2–5.4%
area agreement is coincidental — these are not the same drawn element.

**v2 — colour-gated** (require same pro colour as a precondition, then
nearest by area within that colour group). For `Sf4300e5b`
(yellow-green, scaled target 88.25 mm²), `bridge_hat` has 27 same-colour
candidate shapes; the largest is `Sb50e08ea` at 30.30 mm² — **191% off**, not
a usable match. `bridge_hat`'s yellow-green pro ground (1257.2 mm² total,
per Step 1's `--explain` colour breakdown) is not concentrated in one shape
that corresponds to `bridge_lc`'s single 129 mm² blob. The reverse direction
(`bridge_hat`'s satin-dominant flipped shapes on yellow-green/orange, matched
into `bridge_lc`) also fails to land within 5% (20–345% off). **Shape-level
pairing fails in both directions.** This is the documented dead end the
brief allows for: "if the shape pairing across siblings fails (different
segmentation for same artwork), that itself is a documented finding."

**v3 — colour-level rollup**, bypassing shape correspondence (colour is
artwork-invariant even when segmentation is not): sum each flipped shape's
pro cells by colour, per design.

| pro colour | bridge_lc flipped | bridge_hat flipped |
|---|---|---|
| yellow-green (227,243,91) | **dominant fill** (sat=8, fill=25) | tied, 0 graded cells |
| orange (209,84,0) | tied, 0 graded cells | **dominant satin** (sat=18, fill=11) |
| black (0,0,0) | tied, 0 graded cells | dominant fill (sat=0, fill=1) |

`bridge_lc`'s promotion-driven leak lives entirely in the yellow-green
region; `bridge_hat`'s promotion-driven gain lives entirely in orange. The
promotion does not touch the same colour in both siblings — there is nothing
for a "different pro file, same shape" story to explain, because there is no
same shape (or even same colour-region) in play.

**Applying the brief's bar literally:** CONFIRMED requires ≥half of
`bridge_lc`'s flipped-shape pro-fill cells to sit on a shape whose
`bridge_hat` twin is pro-satin — that requires a valid twin, and none exists
(v1's candidate is disqualified by colour, v2 finds nothing within
tolerance). KILLED requires both siblings' matched shape to be pro-fill —
also inapplicable, same reason. Neither literal bar is met because **the
precondition both bars share (a valid same-artwork twin) does not hold**.
Scored as KILLED because the specific proposed mechanism — reference-file
identity, holding the *same shape* constant — has no shape to hold constant
and is superseded by the segmentation-divergence mechanism demonstrated
above.

### Step 4 — `hotel_fremont_hat` / `hotel_fremont_patch`

No new probe run — reused the Step 2 corpus CSVs (`no new probe runs
needed`, per the brief). Both designs: **0 rows with `reason ==
"promoted_ribbon"`** in `corpus_after.csv`. The promotion is a no-op for
this pair — no shape in either design's segmentation ever reaches the
`dt_irregular` branch's promotion check with qualifying `explained`/
`elongation` values. This matches Task 1's kappa table exactly (both designs
delta 0.000).

Per the extra instruction on this pair: its regression was in the STAGE-0
work (forced-flat, −4.3 composite), a different code path and a different
run than this promotion. Since the promotion touches zero shapes here, the
promotion-era data available **cannot speak to** whether the same
(now-superseded) reference-file mechanism, or the segmentation-divergence
mechanism found above, explains that historical −4.3. Not stretched to
answer with data that doesn't cover it.

## Consequence

The attribution doc's §6 line — "part of each delta is which pro file we are
compared against" — does not hold up under a rigorous shape-level test for
the one pair it was proposed on. **Retract that framing.** The replacement,
evidenced above: `bridge_lc` and `bridge_hat` are the *same artwork rendered
at two different sizes* (0.68 area-scale ratio), and the engine's own
segmentation of those two renders diverges enough (85 vs 79 shapes; no
comparable-area same-colour twin for the one shape that matters) that a
promotion gate keyed to a single shape's elongation/regularity metrics can
legitimately fire on **different colour-regions** in each sibling. No
reference-file confound is needed to explain a same-artwork pair moving in
opposite directions — segmentation variance alone is sufficient, and is
demonstrated, not inferred.

Practically: per-design deltas on sibling pairs are **not safe to read as a
before/after comparison of "the same test" on "the same artwork"** — the
regions each side's engine decomposes it into can differ enough that a
gate change touches unrelated parts of the design in each sibling. This is a
stronger caution than "reference-file variance": it means single-design
deltas on ANY pair (sibling or not) can reflect segmentation accidents, not
just measurement noise. The corpus-level kappa move (0.167 → 0.193, Task 1)
remains the trustworthy number — it isn't built from this pair's shape
identity, and 6 other designs moved the same direction independently.

`MASTER_SCOPE.md` is **not** updated by this diagnosis: the brief's
instruction was to add a sentence only if the reference-file hypothesis is
confirmed, and it is not — it's killed by a documented pairing failure, with
a different (segmentation-divergence) mechanism established in its place
that doesn't map cleanly onto the "reference-file variance" framing the
brief anticipated adding.

## Reproducing

```
cd <kappa-after-worktree>/digitizer
$PY tools/pro_parity/scorecard.py --explain \
  ../parity_out/real/bridge_lc ../parity_out/real/bridge_hat

$PY tools/pro_parity/gateprobe.py --features --csv corpus_after.csv \
  ../parity_out/real/*/

cd <kappa-before-worktree>/digitizer
$PY tools/pro_parity/gateprobe.py --csv corpus_before.csv \
  ../parity_out/real/*/   # --features not supported at 26ceaa3
```

The kappa-before/kappa-after worktrees are ephemeral (plan cleanup removes
them); re-create per
`docs/superpowers/plans/2026-08-17-measurement-debt-knockout.md` Task 1
steps 1-3 with before ref `26ceaa3`.

Pairing scripts (`pair_shapes.py`, `pair_shapes_v2.py`, `pair_by_colour.py`)
were throwaway, scratchpad-only, and are not part of this repo; the tables
above are their captured output.
