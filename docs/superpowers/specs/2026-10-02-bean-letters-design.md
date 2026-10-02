# Bean letters — small traced lettering sewn along its skeleton (design)

**Date:** 2026-10-02 · **Status:** REVISED the same day after two spikes (see "What the spikes
found"); this revision awaits Kent's review. No engine code and no plan until he approves it.

## Kent's rulings this rests on (2026-10-02)

> "We shouldn't have to warn the user of anything. the tool needs the ability
> to identify the image it's being given and follow a path to produce the best
> output possible."

That **withdraws** his 2026-10-01 approval of "warn sooner on small files"
(never started). His calls after it, in order:

1. When an upload lacks detail: rebuild, and **show what changed** — a quiet
   note, not a warning and not a task for the customer.
2. A too-small traced letter is sewn as a **centreline bean run**.
3. The trigger is a **text cluster**, the whole word together.
4. The line is the cluster's **median stroke width, starting at 1.0 mm**, set
   on renders rather than cloth (ROADMAP gate 1 names this kind of number;
   gating it without a sew-out is his call, as with
   `SATIN_UNDERLAY_MIN_EXTENT_MM` on 2026-09-03).

## What was specced first, and why it is dead

The first spec of this date converted five pixel-counted rules to millimetres.
Reading the code for its plan refuted it, and it is recorded here so it is not
proposed again:

- `cfg.work_px_per_mm` (ON at 8.0 since 2026-10-01) already traces every
  non-photo source on at least 8 px/mm. The rules were tuned at 8.4. A
  conversion that is an identity at the tuning resolution therefore changes
  almost nothing for a small file; it would move only 9–31 px/mm sources.
- Three of the five are pixel quantities on purpose, with the measurement in
  the code: `AREA_RATIO_MIN_SMALL_PX` (mm² wrongly exempted Lanczos noise
  slivers of 6–17 mm²), `THIN_INK_MIN_PX` (guards 2 px ringing; a source-pixel
  variant was measured and rejected 2026-09-30), `_CURVE_MIN_PX_PER_MM` (guards
  the staircase; already replaced chord by chord under `subpixel_edges`).
- What is left after the work grid is not tracing. `docs/fine-detail-work-grid-
  2026-09-30.md`, "What this does NOT fix": the words reach the stitch tier and
  each letter sews as one satin bar.

## Problem

`docs/renders/fine-detail-work-grid-2026-09-30/bridge-restaurant-zoom-grid8.jpg`:
bridge's "BAR & RESTAURANT", strokes about 0.7 mm, sewn as one satin blob per
letter.

## What the spikes found (2026-10-02, throwaway code, `origin/main` 0c3b7725)

All at 80 mm, `left_chest`, six colours; ENTHUSIAST, Fremont and the
screenshot downsampled to 5 px/mm.

1. **A bean along the TRACED shape has a ceiling.** Bridge's eight clustered
   teal shapes carry zero holes: the counters are closed in the region mask
   before a polygon exists (a 0.7 mm stroke is 2.5 source pixels). The builder
   works as code — every stitch inside the artwork, one trim over eight shapes
   — and sews squiggles: E and U read, R does not, S and T are one shape.
2. **The same path read from the SOURCE INK reads as letters.** Project each
   pixel of the prepared raster onto the ground-to-ink colour axis, enlarge
   3x, threshold at 0.55, skeletonise: bridge reads R E S T A U R A, the
   screenshot's "SNOW PLOWING DIVISION" comes out clean, Fremont is unchanged
   and slightly cleaner. A ridge filter was better on bridge alone and drew
   triangles at Fremont's serifs and double outlines on bold letters:
   rejected.
3. **`text_cluster_stroke_mm` is not a trigger.** It reads 0.38 for HOTEL
   FREMONT and 0.33 for a cluster holding the bold "C GOLKE INDUSTRIES".
   Stroke width measured from the ink (twice the distance transform on the ink
   skeleton, median per letter):

   | cluster | letter height | ink stroke width, per letter | engine figure |
   |---|---|---|---|
   | bridge words | 4.7–5.6 mm | 0.60–1.17, median 0.75 | 0.68 |
   | ENTHUSIAST | 6.6–6.8 | 1.50–1.92, median 1.75 | 0.82 |
   | HOTEL FREMONT | 5.6–6.2 | 0.67 | 0.38 |
   | Golke, bold line | 3.2–4.4 | about 1.0–1.45 | 0.33 (shared) |
   | Golke, thin line | 3.2–4.4 | about 0.58–0.87 | 0.33 (shared) |

   One cluster holds Golke's bold line AND its thin line, so "the whole
   cluster together" would thin the bold one.

**Not established by the spikes:** stitches (these are paths drawn on the
artwork, not a stitch render); the ink reading on a white-background file (the
probe fell back to the traced mask there, so the screenshot's widths are the
trace's); cloth.

## Goal

Small traced lettering reads letter by letter with no customer action and no
warning. Judged on renders of these four logos and the per-cluster legibility
score (`digitizer_core/legibility.py`), before and after.

## Design

**The rule.** A text cluster's members are grouped by STROKE WEIGHT. A group
whose median ink stroke width is under `cfg.bean_letter_max_stroke_mm` sews
every member as bean runs along the skeleton of its SOURCE INK: no satin, no
underlay, no pull compensation. A group switches together.

*Amended during the build (2026-10-02):* this said "lines of text". Bridge's
words run on an arc and Golke's word gaps equal its line gap, so a geometric
line splitter had no clean rule, while the quantity being decided is the
weight. A cluster splits in two only where its natural two-way split of
per-letter widths leaves at least three members each side and the line falls
between the two medians (`beanletters.weight_groups`); otherwise its median
decides for all of it. Same outcome on the four measured logos.

**The ground.** A bean letter no longer covers the hole its traced shape left
in the ground beneath it, so that ground sews through: the letter joins the
one earlier shape it shares the most edge with (`stage5_overlap`).

1. **Ink reading — new module `ink_path.py`.** For one line: the inkness
   raster (ground-to-ink colour projection; the foreground alpha for a
   cutout, whose ground is transparency), its threshold mask, the skeleton,
   and the median stroke width. One reading serves both the trigger and the
   path, so they cannot disagree.
2. **Decision.** `cfg.bean_letter_max_stroke_mm: float | None = None`; `None`
   is today's engine, byte-identical. Built OFF; Kent flips it on renders,
   intended value 1.0 (his pick, gate 1 number set without cloth).
3. **Builder — new module `stage6_beanletter.py`.** Skeleton to ordered
   strokes to bean runs (`BEAN_PASSES` 3 at `BEAN_STITCH_MM` 0.73, the
   existing constants), each letter entered at the end nearest the needle.
4. **Dispatch.** One branch in `stage7_sequence.stitch_one` ahead of the run
   and satin rungs, and the same answer in `_sews_satin` so sequencing
   predicts what is sewn.
5. **Preflight and the quiet note.** Bean runs are not satin, so
   `LETTERING_TOO_SMALL` does not name them (pinned by a test, no code). The
   engine emits an informational code with the count of lines sewn this way;
   the Studio shows one muted line, outside `ATTENTION_WARNINGS`. Wording is
   Kent's.
6. **Instrument.** A tool that renders the four logos OFF beside ON as
   STITCHES and prints legibility, stitches and trims per cluster.

## Out

- Lettering the clusterer does not tag: scripts, and unclustered strays.
- Font re-set, per-stroke narrow satin, AI enlargement, the ridge filter.
- Bridge's 47 small grey shapes (JPEG ringing sewn as thread).
- Stage 0 routing (ROADMAP gate 2).

## Testing

- Ink reading: a synthetic 0.7 mm letter with a 0.5 mm counter, drawn at
  3.5 px/mm and enlarged, keeps its counter in the skeleton; a cutout reads
  from alpha; a white-background file reads from colour.
- Decision: both sides of the line; `None` never applies; two lines of one
  cluster decide separately.
- Builder: every penetration inside the ink grown by half a thread; only run
  stitches; at most one trim inside a letter.
- OFF arm byte-identical on the committed goldens.
- Bridge integration: at 1.0 its words sew as bean and are not named by
  `LETTERING_TOO_SMALL`.

## Risks

- **Real:** HOTEL FREMONT's strokes are 0.67 mm, so at 1.0 the logo's main
  wordmark becomes bean at 80 mm. That is the rule as ruled; the stitch render
  is where Kent sees whether he wants it, and a lower line or a height cap is
  the cure.
- **Real:** two of bridge's eight letters measure 1.08 and 1.17 (fused
  pairs). The per-line median carries them; a per-letter rule would not.
- **Real:** the ink reading is unproven on white-background files.
- **Real, gate 1:** whether a 3-pass bean reads on a knit is card block 5's
  question and stays `pending sew-out`.
- Cost unmeasured: one extra raster pass per line of text.
