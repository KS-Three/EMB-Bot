# Outline loop corners: the far rail through a letter's convex corner (2026-10-25)

`cfg.outline_loop_mitre`, built OFF (`digitizer/digitizer_core/stage6_border.py`,
`_pivot_ring`). It covers the satin loop that `keyline_runs` sews round a letter:
`enclosed_white_keyline`'s keyline and `border_from_outline`'s outline. Each
sheet is one letter. A row is one convex corner, OFF | ON | the professional's,
drawn at 40 px/mm, ±3.5 mm round the corner (red circle). The thin red line is
the letter's outline, carried into the pro's frame and snapped onto his near
rail.

Each panel's header gives that arm's numbers from `tools/loop_corners.py` for the
corner:

- `pitch max`: the widest step between far ends round the arc. Above 0.8 mm
  (twice the satin pitch) is a fan's spike.
- `r`: the far ends' median distance from the corner, in loop widths. 1.00 is a
  round pivot; 1 / cos(turn / 2) is a mitre point.
- `over`: how far the furthest far end lies outside the letter grown by the
  loop's width with a round join.

`n/a` means no matching pro corner was within 1 mm after the snap.

| sheet | what to look at |
|---|---|
| `mfab_lc_M_off_on_pro.png` | MFab LC, keyline (arm d2: `silhouette_underfill`, `sew_enclosed_white`, `enclosed_white_keyline`, white-face fill OFF). Rows 1 and 4 are the M's top corners. OFF fans into spikes (pitch max 1.12 / 1.11); ON is a dense round arc (0.74), as his is (0.67 / 0.60, r 1.00 / 0.94). Row 2 is the inner V: ON = OFF, because nothing gaps there. Row 3 is the M's foot, where the touching letters' bands meet; both arms are chaotic there, and that is the follow-up, not this flag. |
| `becker_large_B_off_on_pro.png` | Becker hat large, outline loop (`border_from_outline`). Every 70°+ corner is shown, short edges included, because the B has no clean corner. Rows 4–6 are the B's left side: ON fills the fan (1.14 → 0.79, 1.05 → 0.69, 1.07 → 0.74). Rows 1–3 and 7 are traced steps, where he squares the corner and neither arm matches. |
| `becker_large_K_off_on_pro.png` | The K's serif corners. ON closes the fan (1.19 → 0.40). His top-left is a BUTT: the top column runs straight past the corner and the stem column stops square under it, which is neither a pivot nor a mitre point. Unbuilt (n too small for a rule). |
| `becker_large_E_off_on_pro.png` | The E. Row 2 (107°): ON fills the fan (1.18 → 0.53; his 0.45). Row 1 sits beside the E's top notch, where the reader's wedge picks up the notch's crosses in every arm (OFF 1.58, ON 2.65, his 2.82). |
