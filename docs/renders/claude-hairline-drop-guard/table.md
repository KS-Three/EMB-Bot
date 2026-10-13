# Hairline drop guard: before -> after (2026-10-12)

Before = `cfg.hairline` ON with the guard off (`tools.hairline_logo_bill run --no-guard`), after = ON with the guard (default). Scorecard row 80mm/left_chest, 40 wt; hair fixtures forced flat at their drawn width. File properties, not a sew-out (ROADMAP gate 1). Rows: `before/rows.json`, `after/rows.json`.

Columns: shapes the gate captures; strands dropped (the dry walk, summed per shape / the plan's own HAIRLINE_TIER_SEWN count); ink area of captured shapes that lose a strand; new ARTWORK_UNCOVERED and bare-fabric mm2 vs OFF; stitches vs OFF.

| fixture | shapes captured | strands dropped (walk / plan) | ink in shapes that lose a strand mm2 | new ARTWORK_UNCOVERED mm2 | bare fabric added mm2 | stitches vs OFF | handed back |
|---|---|---|---|---|---|---|---|
| drone_render.png | 35 > 26 | 20/9 > 0/0 | 40.1 (9 shapes) > 0 (0) | +4.1 > +0.0 | +23.8 > +17.6 | -1716 (-9.0%) > -1183 (-6.2%) | 9 shapes, 40.08 mm2 |
| enthusiast_logo.png | 14 > 7 | 8/5 > 0/0 | 5.0 (7 shapes) > 0 (0) | +0.0 > +0.0 | +2.6 > +2.1 | -357 (-15.6%) > -246 (-10.7%) | 7 shapes, 4.97 mm2 |
| logo_bridge_bar.jpg | 32 > 26 | 11/9 > 0/0 | 24.3 (6 shapes) > 0 (0) | +0.0 > +0.0 | +7.1 > +5.1 | -2473 (-14.0%) > -2303 (-13.1%) | 6 shapes, 24.35 mm2 |
| logo_gaulke_roofing.png | 5 > 2 | 3/3 > 0/0 | 20.9 (3 shapes) > 0 (0) | +4.8 > +0.0 | +10.6 > +3.9 | -286 (-5.8%) > -256 (-5.2%) | 3 shapes, 20.92 mm2 |
| logo_golden_tee.jpg | 20 > 14 | 11/11 > 2/2 | 83.3 (7 shapes) > 54.4 (1) | +0.0 > +0.0 | +4.2 > +3.7 | -2217 (-26.6%) > -1981 (-23.7%) | 6 shapes, 28.9 mm2 |
| logo_hotel_fremont.webp | 139 > 65 | 77/12 > 1/1 | 73.1 (75 shapes) > 2.1 (1) | +0.0 > +0.0 | +2.3 > +0.9 | -1635 (-11.4%) > -1396 (-9.8%) | 74 shapes, 71.02 mm2 |
| screenshot_phone_ui_golke.jpg | 57 > 38 | 39/25 > 0/0 | 44.0 (19 shapes) > 0 (0) | +7.7 > +8.6 | +41.9 > +36.3 | -1675 (-20.3%) > -1388 (-16.8%) | 19 shapes, 43.98 mm2 |
| summit_badge.png | 16 > 9 | 12/9 > 0/0 | 18.5 (7 shapes) > 0 (0) | +2.1 > +1.1 | +11.9 > +7.9 | -315 (-1.2%) > -266 (-1.0%) | 7 shapes, 18.5 mm2 |
| hair_fine.png | 2 > 2 | 4/3 > 4/4 | 407.9 (1 shapes) > 407.9 (1) | +0.0 > +0.0 | +0.9 > +1.2 | -6340 (-23.6%) > -6334 (-23.6%) | 0 shapes, 0 mm2 |
| hair_strands.png | 2 > 2 | 2/2 > 2/2 | 564.6 (1 shapes) > 564.6 (1) | +0.0 > +0.0 | +2.5 > +2.1 | -5637 (-20.9%) > -5670 (-21.1%) | 0 shapes, 0 mm2 |

## Survey behind the 2 % share (every shape the unguarded tier drops from)

Share = dropped path length over the shape's strand length, 10 fixtures, `DROP_GUARD` off.

```
hair_strands.png n 1 min 0.0033 median 0.003 <=2%: 1 <=10%: 1
hair_fine.png n 1 min 0.0047 median 0.005 <=2%: 1 <=10%: 1
enthusiast_logo.png n 7 min 0.1655 median 0.388 <=2%: 0 <=10%: 0
screenshot_phone_ui_golke.jpg n 19 min 0.0569 median 1.000 <=2%: 0 <=10%: 1
logo_hotel_fremont.webp n 75 min 0.0193 median 1.000 <=2%: 1 <=10%: 1
logo_golden_tee.jpg n 7 min 0.0011 median 0.200 <=2%: 1 <=10%: 3
logo_bridge_bar.jpg n 6 min 0.0285 median 0.426 <=2%: 0 <=10%: 2
logo_gaulke_roofing.png n 3 min 0.2618 median 0.292 <=2%: 0 <=10%: 0
summit_badge.png n 7 min 0.1442 median 0.367 <=2%: 0 <=10%: 0
drone_render.png n 9 min 0.1286 median 1.000 <=2%: 0 <=10%: 0
```
Of the 133 logo shapes that drop anything, 131 drop 2.8 % or more (94 drop all of their strand length); the two under 2 % are golden_tee S70a35fa2 (54 mm2 outline, 0.08 mm lost, 0.11 %) and Fremont Scead5d18 (0.12 mm lost, 1.9 %). hair_strands drops 0.33 % (2 of 51 paths) and hair_fine 0.47 %.

Guard on ANY drop (first cut, measured on the same code before the share was added): hair_strands -152 stitches instead of -5,637, hair_fine -200 instead of -6,340. The network was handed back for two stubs.
