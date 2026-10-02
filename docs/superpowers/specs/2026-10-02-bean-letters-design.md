# Bean letters — small traced lettering sewn along its skeleton (design)

**Date:** 2026-10-02 · **Status:** design approved in chat by Kent 2026-10-02;
this file awaits his review. No engine code and no plan until he approves it.

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
letter. Pull compensation and the thread's own width close the counters before
any stitch rule runs (preflight's `SATIN_GAPS_TIGHT` puts that close at 1.0 mm
on pique knit).

Measured 2026-10-02 on `origin/main` 0c3b7725, 80 mm, `left_chest`, six
colours; the last three logos downsampled to 5 px/mm:

| logo | text clusters | member extent | `text_cluster_stroke_mm` |
|---|---|---|---|
| bridge | 1 (8 of 11 teal shapes) | 4.7–5.6 mm | 0.68 |
| ENTHUSIAST | 1 (10 shapes) | 6.6–7.5 mm | 0.82 |
| Fremont | 1 (12 shapes) | 5.6–6.7 mm | 0.38 |
| screenshot | 3 (38 shapes) | 1.4–4.6 mm | 0.11–0.33 |

Every cluster found is under 1.0 mm.

## Goal

Small traced lettering reads letter by letter with no customer action and no
warning. Success is judged on renders of these four logos and the per-cluster
legibility score (`digitizer_core/legibility.py`), before and after.

## Design

**The rule.** A region with `meta["text_candidate"]` whose
`meta["text_cluster_stroke_mm"]` is under `cfg.bean_letter_max_stroke_mm` sews
as bean runs along its skeleton: no satin, no underlay, no pull compensation.
The figure is per cluster, so a word switches together.

1. **Decision — one function.** `bean_letter_applies(region, cfg) -> bool`.
   `cfg.bean_letter_max_stroke_mm: float | None = None`; `None` is today's
   engine, byte-identical. Built OFF; Kent flips it on renders, intended value
   1.0.
2. **Builder — a new module, `stage6_beanletter.py`.** Input: the region's
   ARTWORK polygon, before pull compensation. It takes the skeleton strokes
   stage 6 already computes for satin, orders them so each travel between
   strokes lies along a stroke still to be sewn, and emits each with the
   existing bean builder (`BEAN_PASSES` 3 at `BEAN_STITCH_MM` 0.73). The line
   is the only new physical number.
3. **Dispatch.** One branch in `stage7_sequence.py`, ahead of the
   `satin_lettering_split` check that reads the same tag.
4. **Preflight and the quiet note.** A bean-sewn word does not raise
   `LETTERING_TOO_SMALL`. The engine emits an informational code carrying the
   count of words sewn this way; the Studio shows one muted line and does not
   list it in `ATTENTION_WARNINGS`. Wording is Kent's.
5. **Instrument.** A tool that renders the four logos OFF beside ON and prints
   each cluster's legibility score, stitches and trims.

## Out

- Lettering the clusterer does not tag: scripts (2026-09-30: "the script is
  not text"), and unclustered strays. Kent passed on "strays join their word".
- A letter-height cap on the rule. Built only if the renders ask for it.
- Font re-set, per-stroke narrow satin, AI enlargement.
- Bridge's 47 small grey shapes (JPEG ringing sewn as thread): a separate
  defect, `dissolve_phantom_blends`' territory.
- Stage 0 routing (ROADMAP gate 2).

## Testing

- Decision: both sides of the line; `None` never applies; an untagged region
  never applies.
- Builder, on a synthetic letter: every penetration inside the artwork polygon
  grown by half a thread; no satin stitches; at most one trim inside a letter.
- OFF arm byte-identical to `origin/main` on the committed goldens.
- Bridge integration: with the flag at 1.0 its clustered teal shapes sew as
  bean and `LETTERING_TOO_SMALL` does not name them.

## Risks

- **Real:** ENTHUSIAST's 6.6–7.5 mm letters at 0.82 mm stroke go bean too and
  may read thin at that height. The renders decide; the cure is a height cap.
- **Real:** 3 of bridge's 11 teal shapes are unclustered and stay satin beside
  bean neighbours — a mixed word. May bring "strays join their word" back.
- **Real, gate 1:** whether a 3-pass bean reads on a knit is card block 5's
  question and stays `pending sew-out` whatever the renders show.
- Minor: screenshot's 0.1–0.3 mm strokes may already sew as hairline beans;
  the change there may be nothing.
