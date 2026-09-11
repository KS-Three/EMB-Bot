# The stage-0 flat/gradient signal, re-measured — and what it now needs

**PR 5 of `docs/superpowers/plans/2026-09-08-real-logo-lane-and-thin-strokes.md`
(review item 1), 2026-09-11.** Gate-2 clean: this measures and changes
nothing. `digitizer/tools/color_diversity.py`, `tests/test_color_diversity.py`
(18).

The 2026-08-15 spec
(`docs/superpowers/specs/2026-08-15-stage0-flat-gradient-recalibration-design.md`)
rejected four approaches to stage 0's flat/gradient gate and proposed one:
**the number of distinct 3-bit-per-channel colours needed to cover 90% of
foreground pixels.** It measured that signal as invariant across a 14×
resolution range and **not sitable** — flat max 17 against gradient min 19,
a gap of 2 resting on one flat JPEG (`bridge`) versus the single gradient
positive (`drone`) — and named the blocker as the label distribution, six
flats and one gradient, not the signal. ROADMAP gate 2 is that sentence with
teeth: **no stage-0 recalibration without real TONAL artwork, and synthetic
fixtures are barred as substitutes.**

The plan's item 1 turns on re-measuring that signal on the artwork that
exists now. This is that measurement.

## 1. The instrument reproduces the published table — under one definition of "foreground"

The spec says "foreground pixels" and does not define them. The choice moves
the statistic by an order of magnitude, so the tool implements both and
reports which one produced a number:

| foreground | what it counts |
|---|---|
| `bbox` | every pixel inside the art bbox, background included |
| `engine` | the pixels stage 1 would DIGITIZE: inside the bbox and not background, by `stage1_prep.prep`'s own rule |

**`bbox` is what the 08-15 table measured**, and the agreement is close
enough to settle it: `bridge` reads **16–17** here against that table's 17,
`drone` **19–20** against its 19, `tires` 2 against 2, `gaulke` 2 against
its converged 2, `fremont` 2 against its converged 2. (`becker` reads 1 here
against its 3; becker's only file is 146 px and the difference is one cell
of halo.)

## 2. The margin today, on real artwork, at native resolution

Eight real flat artworks (the spec's six plus `logo_golden_tee` and
`screenshot_phone_ui_golke`, both arrived since) and **one** real tonal
(`drone_render`; `logo_drone_thermal_badge` is byte-identical and is not
enrolled twice). Every synthetic row — the five `make_photo_fixtures.py`
photographs, the repro of Kent's icon, `summit_badge`, both ramps — is
measured, printed and **excluded from the margin**, which is gate 2 in code.

**Under `bbox`, the spec's own definition:**

| | value | artwork |
|---|---:|---|
| flat max | **16** | `bridge` |
| tonal min | **20** | `drone` |
| **gap** | **+4** | the classes SEPARATE |

The two new real flat logos read 4 (`golden_tee`) and 1 (`screenshot`) — far
below `drone`, so enrolling them **widened** the August gap from 2 to 4
rather than closing it. That is the first new evidence this signal has had
since August, and it points the same way.

**Under `engine`, they do not separate**: `bridge` reads 39 against `drone`'s
24. Excluding the background removes the flat ground that dominates the 90%
and leaves a JPEG's compression noise to be counted on its own, so the one
compressed flat artwork climbs above the gradient. **A claim about this
signal that does not name its foreground rule is not a claim about the
artwork.** Quote `bbox`, and say so.

## 3. What it still cannot do, and the one thing that would change that

**One real tonal artwork.** The spec asked for four or five before a boundary
could be called defensible, and the tool refuses below four rather than
siting one on a single positive. Nothing about that has changed since
August: the acceptance directory
(`digitizer/testdata/photo/acceptance/`) holds only its README in a fresh
clone — it is gitignored on purpose, and nothing dropped there is ever
committed or leaves the machine — and `scratch_*` is likewise absent from a
cloud checkout. So the positives the spec is waiting for exist, if anywhere,
on Kent's box.

**The unblocking act is one drag and one command.** Drop 3–5 real tonal
artworks into `digitizer/testdata/photo/acceptance/` — the original of the
Instagram icon (the committed `repro_gradient_white_icon.png` is a synthetic
reproduction and is barred), airbrushed or shaded logos, photo patches,
badges with real ramps — and run:

```
cd digitizer && .venv/Scripts/python tools/color_diversity.py --foreground bbox
```

They are picked up automatically, labelled real/tonal, and the tool prints
the margin and then either sites the boundary or says what it still lacks.

## 4. What this means for the lane (plan §5a)

- **PR 6a — implement the spec's signal** — is *supported but not yet
  authorised*: the statistic orders the classes with a gap of 4 under its own
  definition, and gate 2 still bars siting it on one positive. Four real
  tonal artworks turn this from blocked into a measurement.
- **PR 6b — route by consequence** (segment with the flat quantizer when
  `design_ramp.fit_design_ramp` REFUSES a gradient-class design and the
  design is not photographic) needs no boundary at all: Kent's 2026-09-04
  ruling already makes the ramp gate the arbiter of "this is a sweep". Its
  known risk is `drone_render`, whose glow halos k-means may band, and it is
  A/B'd on the stitches before anything ships. Whether an evidence-based lane
  change of that shape sits inside gate 2's letter is Kent's ruling (plan §8).

Either way the `CLASSIFIED_GRADIENT` copy and the review reading row stay
honest about which lane sewed the design.

*(measured 2026-09-11 — `digitizer/tools/color_diversity.py`; the sweep
output is reproducible in one command and is not pasted here, because a
pasted table goes stale and the tool does not.)*
