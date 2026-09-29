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
  bare artwork 6.27 → 7.10%; Becker 114 mm under `wide_columns` 5.38 → 7.47. The
  under-reach of the symmetric-offset rail model, hidden by the grown polygon,
  lands on the artwork. 29 tests in 14 files moved, three flat goldens re-captured
  with the pre-change proof; `docs/kent-review-2026-09-28.md` "Outcome" has the
  table. Whether Kent takes the price was asked with the PR.
- **Four photo-lane tests go red wherever `rembg_isolated/venv` exists** (the
  stub's shade demand, the two-square depth sort, the owl's merge and its
  declared-photographic report) — on the pre-change tree too, and never in CI.
  Not a regression of anything; #553, DOCTRINE 2026-09-29 and COOKBOOK "Running
  things" class 4 carry it. Attribute against a worktree with the same venv.
- **Blinding is spent on these nine logos**: all eleven flags and the ref arm have
  been seen labelled. A blind sitting needs new fixtures.

Related: [[flag-before-after-2026-09-18]], [[six-flags-invisible-at-viewing-size-2026-09-18]].
