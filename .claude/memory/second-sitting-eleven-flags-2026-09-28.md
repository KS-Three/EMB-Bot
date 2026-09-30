---
name: second-sitting-eleven-flags-2026-09-28
description: 2026-09-28 — Kent judged all 77 labelled pairs (eleven flags + the 08-27 engine on nine logos): "VERY hard to tell"; today beats 08-27 on 7 of 9; rail_comp the only flag leaning better; four logos bad under every setting; screenshot to be retired
metadata:
  type: project
---

Kent finished the rebuilt labelled page (PR #514) over four sittings, 2026-09-20
to 09-28, and summed it up himself: *"The changes were VERY hard to tell the
differences with the before and after by the human eye."* 77 pairs: 16 after
better, 8 before better, 30 no difference, 23 both bad; "can't tell" on 59 of
68 job questions; no per-arm ruling set. Full table and his notes verbatim:
`docs/kent-review-2026-09-28.md`; the store: `docs/eye-pairs-2026-09-28/kent-notes.json`.

**What changes what you do:**

- **Today's engine beats the 08-27 engine in his eye, 7 of 9**, with notes naming
  cleaner trims and borders, letters in place, becker's C border. First direct
  evidence the month's work registered at full size. It says nothing about the
  distance to Ember; that datum is still [[kent-eye-vs-instruments]].
- **`satin_rail_comp` is the one flag with a positive lean** (5 after / 0 before /
  4 both bad; job yes on 3; tires note: I and S improved, top of the r lost
  thread). A flip is Kent's call and may be a ROADMAP gate 1 question (it moves
  where pull compensation is applied). Do not propose flipping `directional_comp`
  (1/4/4), `lettering_min_column_mm` (0/2/1) or `wide_columns` (0/1/5) on the look.
- **gaulke, golden_tee, screenshot, drone are bad under both settings of most
  arms.** They are engine work, not flag work; no flag rescued any. **Kent's note
  on screenshot: "don't use this one anymore"** — retiring it from `REAL_ART` (nine
  tools read it) is a change of its own, pending his go.
- **The page needs a change locator** — 30 "no difference" and 59 "can't tell" with
  no pointer to where a pair changed; the 09-18 review measured the changes as local.
  **Built 2026-09-29** (`change_hotspots` in the gallery: 0.6 mm blur, per-channel
  threshold, up to three boxes; outlined on both renders, *zoom to change*). It
  marks 72 of the 77; the five it cannot are angle-only changes the blur removes.
- **Kent's picks on the sitting (2026-09-28):** flip `satin_rail_comp` ON — done
  2026-09-29, the sew-out still owed — and build the locator. Not picked: retiring
  screenshot from the corpus.
- **The flip's price, read by the suite and invisible on the page (2026-09-29):**
  MARINE 80 mm 9 → 22 trims at +15% stitches (hops 3 → 6; both 09-19 levers on
  8 → 17); ENTHUSIAST `lost_frac` 0.2748 → 0.2565 — under its bar at last — for
  bare artwork 6.27 → 7.10%; Becker 114 mm under `wide_columns` 5.38 → 7.47. NOT
  the rail model's under-reach (that share fell 19.3 → 14.7%): Becker's junction bare
  reads 1.39 → 3.80% on the satin-only instrument but two thirds of it is the C's bowl
  routed to FILL by the sewn-terms width check (6.72 → 8.08% with fill counted; the rest
  sparse crosses at junctions), ENTHUSIAST's mid-rail bare doubles (cause open), and
  MARINE's letters decompose finer on the
  artwork (R 5 → 8 strokes, 8 → 14 odd nodes) — but the census says 11 of the 22
  trims were the walk's TARGET a half-width off the web (the rail-comp underlay
  starts at the cap tip); fixed the same day (start on the web, DOCTRINE
  2026-09-29): corpus trims 671 → 654, MARINE 21; the rest are cursor-side
  (`satin_walk_cursor_reach_mm`, Kent's on cloth). 29 tests in 14 files moved,
  three flat goldens re-captured
  with the pre-change proof; `docs/kent-review-2026-09-28.md` "Outcome" has the
  table. Kent took the price the same day (*"Take the price, let it merge"*):
  an accepted price, not open defects; the junction tuck and the artwork
  decomposition are the levers, not the rail model (`rails_follow_edge` is measured
  to worsen the headline and the wobble, and read no-difference on 8 of 9).
- **The C's bowl is the cover's fill by design, and the tuck was a pull short
  (2026-09-29):** rendered both ways (`docs/renders/rail-comp-junctions-2026-09-29/`),
  BECKER's C holds an 8 mm blob no 5 mm column spans; on the grown polygon a
  connector's crosses covered it by accident, on the artwork the cover sews it as
  tatami (part C) and the satin-only bare instrument read that as bare — count the
  cover's fill before calling a junction bare. The tuck's entry floor and reach-in
  read the artwork's half-width under rail comp (the third seam of that shape);
  in sewn terms MARINE bare 7.38 → 7.03% at +32 stitches, bridge 99 → 96 trims,
  corpus trims 654 → 651; the bowl's hole shrinks 1 mm². The other
  construction for such a blob is Kent's parked `satin_patch_junctions="satin"`,
  recorded not decided.
- **golden_tee's +65% stitches were the on-rails polygon's SEAMS (2026-09-29):**
  stage 5 hands satin the artwork ∪ underlap reach − earlier layers, a hairline
  notch or sliver wherever two independently vectorised edges meet, and the
  medial axis branches at each (178 → 494 strokes, 148 → 473 satin runs at half
  the points, the same 0.21 mm pitch). The grown polygon's `buffer(pull)` had
  swallowed them. Fixed: the skeleton reads that polygon with the seams of its
  construction closed — hairline fills touching boundary stage 5 ADDED, nothing on
  the artwork's own (a closing at the pull re-cut MARINE 37 → 28 strokes; the
  width test alone cost MARINE four folds and ENTHUSIAST an element) — golden_tee
  11,377 → 7,966, MARINE byte-identical, corpus 651 → 640. Count RUNS before
  stitches; a morphological fix needs a WHERE.
- **The far rail's under-reach has an envelope (2026-09-30, OFF):** `satin_rails_follow_edge="envelope"`
  extends a rail only where its side is short by 0.3 mm and only to the running minimum of
  its edge over ±3 stations — half of `True`'s coverage (golden_tee bare 10.35 → 7.20,
  Becker 100 8.14 → 7.35) at a quarter of its jitter and none of its overshoot, a no-op on
  ENTHUSIAST where `True` breaks the headline (0.257 → 0.290). Does not reach bulges
  shorter than the window or the C's bowl, by design. Kent's flip; the same sew-out.
- **Four photo-lane tests go red wherever `rembg_isolated/venv` exists** (the
  stub's shade demand, the two-square depth sort, the owl's merge and its
  declared-photographic report) — on the pre-change tree too, and never in CI.
  Not a regression of anything; #553, DOCTRINE 2026-09-29 and COOKBOOK "Running
  things" class 4 carry it. Attribute against a worktree with the same venv.
- **Blinding is spent on these nine logos**: all eleven flags and the ref arm have
  been seen labelled. A blind sitting needs new fixtures.

Related: [[flag-before-after-2026-09-18]], [[six-flags-invisible-at-viewing-size-2026-09-18]].
