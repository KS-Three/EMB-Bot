---
name: gaulke-through-last-2026-11-19
description: Kent 11-19 "see how the pro digitizes it, find the deltas, fix toward his" on Gaulke Roofing LC; the cut already matched him, the WALK split the T's bar and the E's stem at the junction; `lettering_columns_through_last` built OFF fixes it (E needs reading_order too); STEEI was fixed upstream
metadata:
  type: project
---

Gaulke Roofing LC at 95.2 mm against `c golke logo LC.DST` (`docs/gaulke-pro-match-2026-11-19.md`).

- **The pro at a T junction:** the butting stroke first, then the through stroke WHOLE over its root (T: stem
  then one bar; E: middle arm then one column top arm -> stem -> bottom arm).
- **Ours:** `outline_cut.find_cuts` already cuts exactly his two columns; `columns._span_graph` splits the
  through column at the junction and the postman's walk sews the halves round the branch. That, not the cut,
  is the delta.
- **`cfg.extra["lettering_columns_through_last"]` (built OFF, `columns._through_last_walk`):** branch run out
  and sewn back, then run under the through column and sew it whole, same entry and exit; kept per letter only
  if `_walk_cost` is no worse. T matches alone; the E only with `lettering_columns_reading_order` (sewn right to
  left the E's column ends facing away from the next letter, so the cost check refuses it). Sweep: 11/44 move,
  trims net -3 (one +1 on drone_render). Kappa does NOT see it (+-0.02): show pictures, not kappa.
- **STEEI** (the reading_order review defect) is ef11041f-only: the L's satin lacked its foot in BOTH arms and a
  travel run masked it OFF. On main the L is one folded column.
- **Next deltas:** the L's short first cross (0.77 vs 1.36 mm); E corner fans (`inside_stagger`, Kent's flip);
  his roof/sun ~1 mm higher (his layout, not ours).

Related: [[marine-match-2026-11-18]], [[column-corner-folds-2026-10-23]], [[corner-turn-2026-11-14]].
