# The crown cover — what defect 50 actually needs (2026-09-30)

**Status: DESIGN ONLY. No engine code until Kent rules on §7.** He picked
"design doc first, then code" after the diagnosis changed what the fix is:
this started as a rail change and five rail and pitch arms refuted that.

---

## 0. What governs this — read before changing the plan

- **When thread is missing at a junction, sew the hole — do not tune a
  cross** (DOCTRINE 2026-09-06). Four cross-length knobs moved nothing; the
  cover did. This document is that ruling applied one step wider, and §1 is
  the evidence that the same thing is true away from junctions.
- **A satin column's crowns are a DECOMPOSITION gap** (DOCTRINE 2026-09-30).
  Five arms refuted, below. Any proposal that tunes a rail, a profile, a
  smoother or a pitch is already measured and already refuted; do not revive
  one without new evidence.
- **Coverage is not the metric a customer sees — price a lettering change on
  `lost_frac`** (DOCTRINE 2026-09-30). The apex widening closed its hole and
  was retracted the same day for spending 0.0088 of `lost_frac` on overshoot.
  **A cover that spills thread outside the artwork fails for the same reason
  and must be measured the same way, from the first commit.**
- **`satin_lettering_split` is a NET WIN and is not on trial here.** Fill
  reads `lost_frac` 0.2688 against the split's 0.1800 on this fixture. The
  crowns are a cost to close, not a case for reverting the flip.
- **No tatami inside a satin shape** (Kent, 2026-09-09, why
  `satin_patch_junctions="satin"` exists beside `True`). A crown cover
  inherits that question and §7 asks it again rather than assuming.
- **The artwork skeleton is RULED** (Kent, 2026-09-19). A decomposition that
  claims the wedges is the other lever (§3c) and it moves the thing every
  lettering flip since sits on. It is proposed here, not assumed.
- ROADMAP gates 1 and 4: no physical constant moves; no quality claim on a
  raw number.

---

## 1. The defect, named (measured 2026-09-30)

MARINE at 127.4 mm, `satin_lettering_split` ON, against the same word sewn as
fill: **11 holes totalling 22.9 mm², worst 4.30 mm²**, where fill leaves
none. Rendered from the real thread path — cloth at the crowns of curved
letters and between letter parts.

**Every hole is mid-rail**, 0.38–0.76 mm from the nearest cross and 0.25–0.73
mm from the outline, with the rail **0.62–1.47 mm short of the artwork edge
along its own cross ray**. Four of the eleven sit at a node between two
sub-strokes.

That reads like a width problem. It is not one:

| arm | stitches | holes | uncovered | `lost_frac` |
|---|---|---|---|---|
| shipped | 7,168 | 11 | 22.9 | **0.1800** |
| `rails_follow_edge="envelope"` | 7,567 | 11 | 22.9 | 0.1800 |
| `rails_follow_edge=True` | 7,712 | 9 | 18.1 | 0.1937 |
| width smoother removed (median 1, 0 passes) | 7,471 | 11 | 22.3 | 0.1790 |
| pitch 0.40 → 0.20 mm | 8,735 | 10 | 21.8 | 0.1911 |

The `1.6 ×` floor cap binds on **one** of the eleven. `_fold_caps` never runs
(`fold_guard` follows `cfg.wide_columns`, default OFF).

**Every arm that moves a crown makes `lost_frac` worse.** No column parameter
reaches them because the crowns are not inside any column — the strokes'
union simply does not claim that artwork.

---

## 2. What a cover is, and what it is not

**Is:** thread laid on artwork the shape's own strokes do not reach, inside
the shape's polygon, sewn before the strokes so it ends up underneath them.

**Is not:** a wider column (§1), a denser column (§1), a new stroke (that is
§3c, the decomposition answer), or anything that may cross the artwork
boundary. The boundary clip is not a detail — it is the whole difference
between this and the retracted apex widening.

---

## 3. The construction — three parts, in the order they should be priced

**(a) Find the wedges.** Per satin shape: `polygon − union(stroke footprints)`,
where a footprint is the stroke's swept cross area, not its crosses buffered
(the 2026-09-30 lesson: a model that counts crosses over-reports by 1.07–38.9x
because it ignores every other thread kind). Then filter with the rules
`ARTWORK_UNCOVERED` adjudicated the same day and that have renders behind
them: max inscribed half ≥ **0.30 mm**, area ≥ **1.0 mm²**, fill ≥ **0.15**.
Reusing those three is deliberate — a wedge too small or too thin to warn
about is too small to spend thread on, and the thresholds already have a
corpus and a guard fixture behind them.

**(b) Sew each surviving wedge.** As a satin column along the wedge's own
medial axis where it is long enough to carry one, else as the smallest patch
that covers it. FIRST in the shape, so the arms sew over it. Clipped hard to
the artwork polygon at emit time, with the clip asserted rather than assumed.

**(c) The alternative, and it is not an add-on.** Make the decomposition not
leave the wedges — the split's sub-strokes claim the whole polygon between
them. Cheaper thread, no cover layer, and it would likely close **defect 49's
apex** too, since that is also artwork no stroke reaches. It is the higher
blast radius: the artwork skeleton is ruled, and every lettering flip since
09-19 sits on it. **(a)+(b) and (c) are alternatives, not stages** — if (c)
is wanted, (a) is still worth building as its instrument.

---

## 4. Fixtures

| fixture | why |
|---|---|
| MARINE 127.4 mm, split ON | defect 50's own case: 11 holes / 22.9 mm² |
| MARINE 80.2 mm | 2 holes / 3.9 mm² — the same mechanism at chest size |
| ENTHUSIAST 80 mm | defect 49's apex, 1.56 mm². Does the cover close it? |
| BECKER 80 / 100 mm | 17 holes; the most crowded case, and where a cover would over-fire if it is going to |
| the nine REAL_ART logos | the price, and the silent fixtures must stay silent |

---

## 5. The instrument

Already built, 2026-09-30 — this is the first construction in the lettering
plan that does not need a new one:

- `preflight.ARTWORK_UNCOVERED` (`uncovered_holes`, `uncovered_hole_mm2`)
  names the defect and is what "closed" means.
- `tools/uncovered_floor.py --corpus` for the corpus sweep.
- `tools/thread_path_render.py` for the adjudication render, drawn through
  `stitchviz.render_design` so a picture can disagree with the model.
- `tools/dropped_elements.py` for `lost_frac` / `unsewn_frac` /
  `overshoot_frac` — **the gate, not a footnote.**

---

## 6. Predictions, falsifiable

Written before the build so they can be wrong:

1. **The cover closes at least 8 of MARINE 127's 11 holes.** Falsified under
   8 — then the wedges are not what §1 says they are.
2. **`lost_frac` does not rise.** 0.1800 is the number to beat or hold;
   > 0.1810 and the cover is the apex widening again, and is retracted the
   same day.
3. **Thread cost is under +4%** (7,168 → under 7,455). The wedges total
   22.9 mm²; covering them should cost far less than the +1,567 stitches
   halving the pitch spent for one hole.
4. **It closes ENTHUSIAST's apex too** (defect 49, 1.56 mm²). If it does not,
   the two defects are not one mechanism and defect 49 needs its own answer.
5. **The six silent corpus fixtures stay silent** — golden_tee, bridge,
   screenshot, gaulke, tires, fremont report 0 holes today and must after.

---

## 7. What is Kent's

1. **(a)+(b), or (c)?** A cover under the arms, or a decomposition that does
   not leave the wedges. (c) is cleaner and closes more; it also moves the
   ruled skeleton.
2. **May a cover sew as FILL inside a satin shape?** Your 2026-09-09 ruling
   said no, which is why `satin_patch_junctions="satin"` exists. A wedge too
   short to carry a column has no satin answer.
3. **All satin shapes, or lettering only?** The mechanism is not
   lettering-specific; BECKER's 17 holes are mostly not letters.
4. **The flag and its default.** Proposed `cfg.satin_crown_cover`, built OFF,
   flipped only on the corpus table and `lost_frac`.

---

## Not this document

The junction cover (`satin_patch_junctions`, and part C of
`satin_junction_stack`) already covers junction-adjacent bare artwork and is
inert under today's defaults because the stack composes it. This is the same
idea with the junction gate removed; if (a)+(b) is built, the two should
become one mechanism rather than two flags that mean almost the same thing.
