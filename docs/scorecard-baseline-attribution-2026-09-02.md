# The corpus scorecard baseline cannot be re-captured yet — 2026-09-02

**Verdict: do NOT re-capture `testdata/corpus_scorecard_baseline.json` today.**
Not because the drift is small — it is enormous — but because
`tools/corpus_scorecard.py`'s own rule is that "an unattributed mover blocks
the recapture", and most movers are still unattributed. Re-capturing now would
silently bless a fixture whose stitch count more than doubled.

This file records what was measured so the next attempt starts from evidence
rather than from scratch.

## The state of the ruler

| | |
|---|---|
| Baseline last written | **2026-08-24** (`6b1ccdf`) |
| Merges since | **73** (25 touching `digitizer_core/`) |
| Entries that moved | **30 of 38** |
| Score changes | **17** |
| `captured_at_commit` / `captured_date` | **absent** |

The missing stamp is its own small defect. `capture()` has written both fields
since the very commit that last wrote this baseline (`6b1ccdf`, lines 184-185),
so the shipped artefact predates its own stamping and the tool's docstring
promise that "staleness is measured, not remembered" is not true of it. Any
recapture fixes that for free.

## What moved

Movement is in two distinct populations, and they need different treatment.

**Findings and scores — one likely cause, verified on the worst case.**
Almost every score change names `THREAD_MATCH_POOR` appearing or resolving.

**Geometry metrics — cause unknown.** `same_hole_fraction` (22 entries),
`trims_per_1000` (21), `stitch_count` (20), `coverage_max` (19),
`color_changes` (18).

## Attribution 1 — `region_blobs` 40 → 0 is a RULER change, not a regression

The scariest-looking mover in the diff: a 40-point drop with a *block*-severity
`THREAD_MATCH_POOR` appearing. It is benign.

```
is_photographic=None   score=  0  grade=F  worst_dE=10.7  THREAD_MATCH_POOR x4
is_photographic=True   score= 40  grade=D  worst_dE=10.7  THREAD_MATCH_POOR x0
```

Declaring the fixture photographic restores **exactly** the baseline score of
40 and removes all four findings — while `thread_worst_delta_e` stays
**identical at 10.7** either way. The engine's thread choice never changed;
only the yardstick applied to it did.

Cause: `2d58da8` (PR #245, "photo machinery: declare it, and ask the question in
one place"), which gates preflight's photo yardstick on `cfg.is_photographic`
instead of on a class name. Its own commit message describes the intended
effect on the other side — `owl_kent.jpg` had "twelve THREAD_MATCH_POOR
findings that were the wrong ruler rather than real mismatches". The flip side,
visible here, is that undeclared content is now graded on the strict tatami
ruler. That is the change working as designed.

Ruled out first, both by measurement, both null:

| hypothesis | result |
|---|---|
| `shade_palette_bind` (defect 9's fix) | identical with it on or off — score 0, ΔE 10.7 both ways |
| the check itself changed | only one commit touched `preflight.py` in the window, and it is `2d58da8` |

**This is also defect 15 seen from the other side.** The dashboard records that
an undeclared photograph loses the palette bind and depth sequencing; here an
undeclared fixture loses the right *grading ruler* too, on a metric nobody was
watching. Same root: the declaration is unreachable and nothing infers it.

## Attribution 2 — the geometry movers are NOT the obvious suspects

`enthusiast_logo @ 80mm/hat_front`, against a baseline of
`trims/1k 8.1 · satin_steps 1416 · link_segments 0`:

```
default              trims/1k=7.3   satin_steps=1284   link_segments=4   stitches=2477
borders_last=False   trims/1k=6.9   satin_steps=1280   link_segments=4   stitches=2469
```

Turning `borders_last` off moves trims **further** from the baseline, not back
to it, and leaves `satin_steps` and `link_segments` where they are. So the
biggest recent sew-order change does not account for this fixture's drift.

Two things in that table deserve their own look:

- **`link_segments` 0 → 4 while `chain_links` ships default-OFF.** Chaining is
  the one latent flag the dashboard says must never be flipped without
  rebuilding its instrument. Something is emitting links, or the metric changed
  meaning. Either answer matters.
- **`summit_badge` stitch_count 3839 → 8431**, coverage area 1808 → 4789 mm²,
  satin_steps 995 → 1557. The design more than doubled. MASTER_SCOPE already
  flags this fixture as saturated at F/0 so its *score* says nothing — which is
  exactly why a doubling in its geometry could sit here unnoticed.

Other unexplained geometry movement, listed so the next pass has targets:

| fixture | movement |
|---|---|
| `drone_render` | `color_changes` 23 → 18 (plausibly the re-snap rehome, defect 16's fix — untested) |
| `gradient_ramp_linear` / `_radial` | `color_changes` 1 → 3 on both |
| `repro_gradient_white_icon` | `color_changes` 5 → 2 |
| `enthusiast_logo` | `satin_steps` 1416 → 1284 |

## What would unblock a recapture

The method that worked twice above is cheap and should be reused: **run the one
fixture with the one flag flipped**, roughly ten seconds a test, rather than
bisecting 73 merges with a four-minute full capture each time.

1. Confirm the `THREAD_MATCH_POOR` population is all `2d58da8` by spot-checking
   two or three of the fixtures that *improved* (`fur_ramp` 40 → 88,
   `photo_owl_pale` 22 → 46) the same way — declare them and see the baseline
   score return.
2. Attribute the geometry population. `link_segments` and `summit_badge` first,
   since those two are the ones that could be hiding a real defect.
3. Then re-capture, listing every mover and its cause in the commit message,
   as the tool's docstring requires.

Until then the scorecard still works as a **diff** — it is how all of the above
was found. What it cannot currently do is tell a regression from eight days of
intended change, which is the job it exists for.

*(measured 2026-09-02 on `main` at `0bd9f0f`, one machine so platform numerics
cancel; `tools/corpus_scorecard.py diff`, `digitizer_core.preflight`)*
