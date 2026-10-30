# Defect 19 re-measured on main 44ecf1cb — 2026-10-29

**Status: the defect as written is gone, and nothing new is built.** On
2026-09-11 the share of our sewn silhouette with no linear stitch on it ran
**5.9–100.0%** with the cap off. On today's main it runs **0.0–4.0%** at the
same 80 mm, cap off, on the same six fixtures. The edge work since then closes
it, not the cap. The cap's size swing (`docs/edge-cap-cliff-2026-09-12.md`) is
gone too: across 60–120 mm the largest bill on any fixture is **+5.6%**,
against the 40% budget. The brief's step 3 (a lever that keeps the cap
stable across sizes) was conditional on the swing persisting. It does not
persist, so no lever is built.

**Nothing was sewn.** Every number here is plan geometry or DST bytes.
Layout is judged in the preview (Kent 2026-10-22); gate 1 is untouched.

## The default edge cap is OFF in practice, since 2026-10-27

`cfg.edge_cap` still defaults to `"bean"`, but `bean_only_lines` (ON since
2026-10-27, PR #1161) turns the bean style into no cap at
`stage7_sequence.py` ("a filled body's edge is never a bean"). So the shipped
engine has sewn **no design-edge cap at all** for two days, and the `bean` and
`none` arms below read the same stitches, trims and cover on all six
fixtures, with 0 cap points. The satin style is the only cap style still
live.

**A Studio readout is now wrong because of it.** The Design edge select still
defaults to "Bean cap". The engine emits neither `EDGE_CAP_APPLIED` nor
`EDGE_CAP_EMPTY`, and the run index finds no `edge_cap` runs. So
`borderMenu.edgeCapState` lands on `state: "empty"`: *"Design edge found
nothing to sew"*, titled *"the design is too small or too narrow for it"*.
That is false on every design: the engine refused the style. This PR does
not fix it (it is the Studio's, and the default is Kent's call); it is in
the decision sent up.

## Re-measure at 80 mm (`tools/edge_cap_remeasure.py attrib`)

Same rule as `tools/pro_silhouette.py --ours`: the outer boundary of the
union of the sewn regions, against every satin / border / bean / run polyline
at one thread width (`COVERAGE_THREAD_W_MM`), read within
`BORDER_HOST_MARGIN_MM`. Cap OFF, all other defaults as shipped.

| fixture | 2026-09-11 bare | today bare | parts | silhouette | covered by |
|---|---|---|---|---|---|
| Fremont (`max_colors=3`, flat) | 100.0% | **0.0%** | 1 | 203.7 mm | satin 100% (the under-fill rim) |
| whitebg | 82.6% | **1.8%** | 6 | 293.3 mm | border 51.3%, satin 48.8% |
| gaulke | 76.7% | **0.3%** | 39 | 1,063.6 mm | satin 94.0%, border 5.7% |
| enthusiast | 5.9% | **4.0%** | 27 | 617.1 mm | satin 96.0% (it is satin lettering) |
| becker | — | **2.9%** | 7 | 585.0 mm | satin 97.1% |
| drone_render | — | **0.2%** | 42 | 1,353.9 mm | satin 96.3%, run 8.0% |

(The 2026-09-11 figures are MASTER_SCOPE defect 19's four named rows; Becker
and drone's were not published separately.)

**The pro, unchanged:** `tools/pro_silhouette.py` re-run today reads his five
Becker files **at least 19.1–26.1%** bordered (median 23.8%, 7,063 mm of fill
edge), to the digit what 09-11 read. The two sides are still not one
measurement: his is a LOWER bound on fill edge a certified border tracks;
ours is exact cover on the whole silhouette, and a satin shape's own edge
counts as covered. "Ours 96–100% covered vs his ≥19–26%" says our edge is no
longer open. It does not say we border more than he does.

### What each edge flag now covers

Each flag turned OFF alone, cap off, 80 mm. The cell is the bare share it
leaves. One flag off measures its cost GIVEN the others (DOCTRINE, flagcost),
so the columns do not add.

| fixture | all ON | `border_by_size` | `…_fabric_edges` | `border_from_outline` | `silhouette_underfill` | `…_underfill_rim` | `outline_loop_mitre` |
|---|---|---|---|---|---|---|---|
| Fremont | 0.0 | 0.0 | 0.0 | 0.0 | **100.0** | **100.0** | 0.0 |
| becker | 2.9 | 2.9 | 2.9 | 0.6 | 2.9 | 2.9 | 3.8 |
| enthusiast | 4.0 | 4.0 | 4.0 | 4.0 | 4.0 | 4.0 | 4.0 |
| drone | 0.2 | 0.2 | 0.2 | 0.2 | 3.5 | **7.0** | 0.2 |
| whitebg | 1.8 | **51.2** | 1.5 | 1.8 | **29.8** | **29.8** | 1.8 |
| gaulke | 0.3 | **6.0** | 0.3 | 0.3 | 0.3 | 0.3 | 0.3 |

- **`silhouette_underfill_rim`** carries the most: Fremont's whole edge
  (its rim is the satin loop round the white ground), 28 points of whitebg's,
  6.8 of drone's. `silhouette_underfill` reads the same, because the rim acts
  only under it.
- **`border_by_size`** carries whitebg's other half (49.4 points) and gaulke's
  5.7.
- **`border_by_size_fabric_edges`** is neutral on the silhouette, by
  construction: it drops only the stretches a ring shares with another sewn
  region, and the silhouette has none.
- **`border_from_outline`** and **`outline_loop_mitre`** move under a point.
  Becker reads *less* bare with `border_from_outline` OFF (0.6), because its
  letters then sew another way; that flag does not hold Becker's edge.
- **Enthusiast** moves with none of them: it is satin lettering, and its 4%
  is the corners between letters.
- PR #1185 (the satin cap lifts between arcs) acts only when the satin cap
  is on, so it shows only in the satin arm below.

## The size sweep (`tools/edge_cap_remeasure.py sweep`)

Satin cap, and the bean cap as it sewed 09-11 to 10-27 (`bean_only_lines`
OFF, since ON turns it into no cap; that also moves bean letters and the run
tier, so its stitch counts carry more than the cap). Cell: cap points
(+% of the artwork's own stitches) / bare share left with the cap.

**Becker, on the 2026-09-12 cliff's own widths:**

| width | bare, no cap | satin cap | bean cap (legacy) |
|---|---|---|---|
| 60 | 0.9% | 0 (+0.0%) / 0.9% | 0 (+0.0%) / 0.9% |
| 70 | 1.3% | 0 (+0.0%) / 1.3% | 0 (+0.0%) / 1.3% |
| 80 | 2.9% | 33 (+0.3%) / 1.9% | 52 (+0.5%) / 1.1% |
| 86 | 3.2% | 77 (+0.6%) / 1.2% | 58 (+0.5%) / 1.1% |
| **88** | 3.4% | 92 (+0.7%) / 1.4% | 81 (+0.6%) / 0.7% |
| 90 | 3.8% | 106 (+0.8%) / 1.5% | 81 (+0.6%) / 1.1% |
| **91** | 3.8% | 81 (+0.6%) / 1.7% | 87 (+0.7%) / 0.9% |
| 92 | 4.1% | 117 (+0.9%) / 1.3% | 110 (+0.8%) / 0.6% |
| 95 | 4.3% | 125 (+0.9%) / 1.3% | 122 (+0.9%) / 0.6% |
| **95.7** | 4.5% | 142 (+1.0%) / 1.3% | 133 (+0.9%) / 0.4% |
| 96 | 4.6% | 128 (+0.9%) / 1.4% | 136 (+0.9%) / 0.3% |
| **100** | 5.1% | 175 (+1.1%) / 1.3% | 157 (+1.0%) / 0.3% |
| **110** | 6.8% | 274 (+1.5%) / 1.4% | 204 (+1.1%) / 0.9% |
| 120 | 11.4% | 484 (+2.3%) / 1.5% | 414 (+1.9%) / 0.6% |

The bold rows billed **+53.4% to +58.7%** on 2026-09-12. Today they bill
+0.6% to +1.5%, and the bill rises with size instead of jumping on it. The
one dip (satin 106 → 81 points, 90 → 91 mm) is 25 points, 0.2% of the design.
Becker's art now covers 88.6–99.1% of its edge with satin at every width
(falling smoothly as it grows), so the
`classify_ribbon` verdict on the BECKER banner (the cause on 09-12) no longer
decides the cap's input. **That verdict was not re-probed here.** The cap
stopped depending on it; whether the banner still flips on
`_PROMOTE_EXPLAINED_MIN` is `classify_ribbon`'s own question, and Kent ruled
09-12 to leave it alone.

**The other five, 60–120 mm** (`remeasure.jsonl` has every cell):

| fixture | bare, no cap | satin cap bill | bean cap (legacy) bill |
|---|---|---|---|
| enthusiast | 4.0–4.7% | +0.0% to +4.5% | +4.3% to +5.6% |
| whitebg | 1.8–6.0% | +0.2% to +0.7% | +0.1% to +1.0% |
| gaulke | 0.1–3.2% | +0.0% to +3.9% (60 mm only over +0.2%) | +0.0% to +2.9% |
| drone_render | 0.2–1.4% | +0.0% to +0.4% | +0.0% to +0.2% |
| Fremont | 0.0% | 0 points at 60, 80, 120 | 0 points |

Nothing comes near `EDGE_CAP_BUDGET_PCT` (40). The largest bill anywhere is
the legacy bean cap on enthusiast at 60 mm, +5.6%. Satin on enthusiast leaves
4.0–4.7% bare up to 90 mm, where the bean cap closes it to under 1%: the
satin emitter declines those stretches (probably its `BORDER_MIN_LOOP_MM`
floor; not traced).

## The renders: OFF | ON | pro on the paired jobs

[`renders/edge-cap-2026-10-29/`](renders/edge-cap-2026-10-29/README.md):
`tools.flip_sheet_renders`, the Studio request at the pro's width, hat
preset (Fremont at Kent's 92.5). Rows `edge_cap_satin` and
`edge_cap_bean_legacy`. OFF is the shipped engine (no cap). The pro's crops
are local only (Kent 2026-10-27).

| job | OFF | satin cap | bean cap (legacy) | pro |
|---|---|---|---|---|
| hotel_fremont_hat | 15,865 st / 25 tr / 3 cc | **byte-identical** | 15,839 / 25 / 3, 0 cap runs (the bean-letter change, not a cap) | 17,067 / 21 / 10 |
| becker_hat_small | 10,270 / 13 / 1 | 10,286 / 13 / **2**, 1 cap run | byte-identical | 8,694 / 11 / 4 |
| gaulke_roofing_hat | 7,446 / 30 / 1 | **byte-identical** | 7,474 / 31 / 2, 2 cap runs | 6,138 / 42 / 0 |
| precision_drone | 14,491 / 83 / 9 | **byte-identical** | 14,457 / 83 / 10, 1 cap run | 14,552 / 59 / 22 |

At the pro's own sizes, the satin cap moves one job of four. On Becker it
sews a 16-point satin sliver on MARINE's M and **costs a colour change for
it** (1 → 2), because the cap is its own block in the edge's cone. That is
the whole cap on the paired corpus.

## What this leaves

1. **Defect 19 is closed by the upstream edge work**, chiefly
   `silhouette_underfill_rim` and `border_by_size`, both ON. Nothing in this
   PR changes a stitch.
2. **The Studio's Design edge readout says "too small or too narrow" on
   every design** while the engine is refusing the style. That is a real
   defect in what the operator reads. It is not a stitch problem.
3. **`edge_cap="satin"` is cheap now and almost inert**: +0–4.5% from 60 to
   120 mm, 0 points on three of four paired jobs. Its one visible act
   (Becker) costs a stop for 16 points.
4. **The 09-12 budget (`EDGE_CAP_BUDGET_PCT`, `"warn"`) stays.** It costs
   nothing while the bill is this small, and it is what would speak if a
   future flag reopened the edge.

Reproduce: `tools/edge_cap_remeasure.py attrib|sweep OUT.jsonl` (about 70
minutes each on 4 workers on Kent's laptop; Fremont is 9 minutes a cell), then
`table OUT.jsonl`. The renders: `python -m tools.flip_sheet_renders run
--flags edge_cap_satin edge_cap_bean_legacy`, then `report` with the same
flags and fixtures.
