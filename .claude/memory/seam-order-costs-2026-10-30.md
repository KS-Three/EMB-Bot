---
name: seam-order-costs-2026-10-30
description: fill_seam_order's two costs, read per job -- Becker beanie's rise is one knockdown walk (ProSeal beanie goes the OTHER way, so no blanket skip); the drone's +6 cuts are the chord picking the wrong progression; two OFF switches, the lay read before the price
metadata:
  type: project
---

Kent flipped `fill_seam_order` ON 2026-10-30 (#1198), then ruled "Render and
attribute" on two rows that went the wrong way. Full record:
`docs/seam-order-attribution-2026-10-30.md`.

- **Becker beanie 38.6 -> 105.8 mm exposed, 3.72 -> 14.84 mm bare:** ONE
  knockdown walk, 38.7 -> 77.9 mm. `knockdown._stay_down` walks every lift, so a
  hop seam order adds cannot be cut. Garment colour, bare in the 0.20 band only.
- **ProSeal beanie goes the other way:** held out of seam order its knockdown
  goes 150 -> 298 mm. So `knockdown_shorter_walk` (OFF) sews both, keeps the shorter.
- **Drone 87 -> 93 cuts:** `_order_for_seams` picks its progression by flown
  chord, which cannot see a walled-in section; `fill_bridge_cut_exposed` cuts it.
- **`fill_seam_order_priced` (OFF):** ridges + flips first (`_seam_faults`), then
  `_score`. Letting `_score` choose outright put flips back (beanie 0 -> 6).
  17 pairs: flips 59 -> 2, ridges 1 -> 0, cuts 399 -> 396, exposed 509 -> 429 mm.
  Costs: crest +15 cuts, MFab hat +4, ProSeal hat +2, drone bare +0.34 mm.

**Why:** a corpus total hid the beanie, and "skip the knockdown" looked right on
the one job read. **How to apply:** read a flip per job, in both directions,
before building the cure. A plan-side reader that reports 0 on every arm has not
proved anything: check it on a job known to have the fault. From a subfolder,
`git add` of a root-relative path stages nothing, and a background job hides that.
Related: [[trim-defects-4-6-2026-10-29]], [[beanie-knockdown-2026-10-21]],
[[layout-judged-in-preview-2026-10-22]].
