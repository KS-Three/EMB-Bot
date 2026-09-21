# Lock stitches on the browser lettering lane — ported, measured, default OFF

**2026-09-14.** The gap audit's §4.6 finding, implemented and priced. Ships behind
`ties: true` on `buildLetteringDesign`, default OFF: the flip changes every
`.dst`/`.pes` a customer exports from lettering, which is Kent's call, and the
dossier number it would have been decided on turns out to be wrong by 2.7×.

## What was missing

**Zero tie/lock records existed anywhere in `src/`.** The only `lock`/`tie`
match in the entire browser lane was the brand name *"Baby Lock"* in a
`garments.js` comment. Meanwhile `digitizer_core` has always tied every block
**unconditionally** — `stitches.apply_ties`, called from `stage7_sequence` and
`stage6_applique` with no config flag anywhere in the path.

So this was never a technique the two lanes disagreed about. It was a parity
gap: a lettering file exported from the Studio could start or end its thread
with nothing holding it, and unravel from the first wash.

## The port

`tieRun(at, toward)` mirrors `stitches.tie_run` exactly, including both rules
its docstring earns:

1. **The legs never reach past `toward`** — `leg = min(TIE_STITCH_MM, d)`.
   Python learned this on its first smoke run, where tie-offs pushed the
   design's bounding box 0.8 mm outside its own artwork; on a garment that
   reads as a stray stitch someone has to trim off.
2. **The run starts and ends at `at`**, so splicing it in front of or behind a
   run leaves the sewn path continuous and moves no existing penetration.

Placement follows `apply_ties`' own question — *"is the thread starting here,
or being cut here"*, not *"did the needle lift"*: tie in at the first run and
after every trim, tie off before every trim and at the end. A jump that was not
trimmed leaves the thread continuous and correctly gets no lock.

`TIE_STITCH_MM = 0.8` and `TIE_STITCHES = 3` are hand-ported from `machine.py`.

## The measurement — and where the dossier was wrong

All 85 shipped fonts, `buildLetteringDesign`, 5×2.25in garment box.

| text | stitches off | on | delta | trims added | ties |
|---|---|---|---|---|---|
| `KENT` (4 ch) | 274,475 | 283,563 | **+3.31%** | **0** | 2,272 |
| `Fritsch's Stitches` (18 ch) | 256,595 | 277,123 | **+8.00%** | **0** | 5,132 |
| two lines (37 ch) | 492,667 | 530,339 | **+7.65%** | **0** | 9,418 |
| three lines (74 ch) | 682,419 | 734,659 | **+7.66%** | **0** | 13,060 |

**The dossier's "+2.93% stitches" does not survive.** It is reproducible only on
a very short string — 4 characters lands at 3.31% — and any realistic customer
text costs **~7.7–8.0%**, roughly 2.7× the figure a flip decision would have
been taken on. The reason is arithmetic rather than mysterious: a lock is a
fixed 4 stitches, ties number `2 + 2×trims`, and trims scale with the number of
glyph fragments while a short word fitted to the same garment box is sewn much
larger (hence more base stitches to divide by).

**"Zero added trims" reproduces exactly**, at every length. It is structural,
not lucky: a tie bounces between a point the needle already occupies and a
point 0.8 mm into the shape, so it can introduce no travel long enough to cut.

Per-font spread on the 18-character string: min **+2.51%** (`fold_inkstitch`),
max **+47.98%** (`noble`). `noble` is not a tie defect — it sews 1,334 stitches
with **79 trims** on 18 characters, so ties are dominated by its own
fragmentation. The tie cost makes the fragmentation defect ROADMAP phase 3
names visible rather than causing it.

**Faithfulness check:** the emitted tie count equals `apply_ties`' rule
(`2 + 2×trims`) on **83 of 85** fonts. The two exceptions are
`hebrew_font_large`/`hebrew_font_medium`, which have no Latin glyphs and so emit
zero stitches, zero runs and zero ties for this text — the `unsupported` path,
not a miss.

## Safety

**Flag off is byte-identical to `origin/main` on 85/85 fonts**, verified by
re-running the corpus against the pre-change `digitize.js` and comparing a
full `x,y,type` fingerprint of every stitch record. So merging this changes no
exported file until someone passes `ties: true`.

Six mutations, all caught: overshoot guard removed, no tie-in after a trim, no
final tie-off, flag defaulted ON, lock not closing at the anchor, zero-length
guard removed.

**The overshoot guard needed `tieRun` to be exported to be testable at all.**
Its `min()` only fires when the path is shorter than one leg, which no ordinary
lettering fixture produces — deleting it passed the entire suite. That is the
third time in this one session a guard's first draft could not see the thing it
was written for (see DOCTRINE, "The verdict was already computed").

## What this turned up on the way

Adding two JS constants was supposed to be covered automatically by
`test_machine_wire.py`. **It was not, and the mutation proved it.** That file's
Python pattern anchored end-of-line immediately after the number, so **36 of
`machine.py`'s constants were invisible to it** for carrying the trailing inline
comment that is this codebase's house style — both tie constants and the whole
`APPLIQUE_*` block among them. Fixed here; the shared count goes 18 → 21.

That surfaced one divergence nobody could previously see: **`UNDERLAY_INSET_MM`
is 0.4 in `src/satinfont.js` and 1.0 in `machine.py`.** It is a **name
collision**, not drift — the browser value is a satin column's contour-underlay
inset *per side*, the Python one a region's edge-walk inset — and it is pinned
in `DELIBERATE_DIVERGENCE` rather than reconciled, because
`docs/trade-knowledge-2026-09-13.md` §3 measured that Wilcom publishes **no
underlay inset at all**. Neither number has vendor backing, so merging them
would be inventing a physical constant, which is gate 1's business. Renaming one
side is the honest fix and is a separate change.

## The open question — Kent's

Flip `ties` on by default? For: the Python lane already does it unconditionally,
and an untied lettering file is a real defect on a real garment. Against: ~8% more
stitches on every lettering export, and the tie's own geometry has never met
cloth. The 0.8 mm leg and 3-leg count are inherited from `machine.py`, where
they are also unsewn — so this is a candidate for the sew-out card, not a
desk decision.
