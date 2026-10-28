---
name: bean-census-2026-10-27
description: The reference digitizer beans almost nothing (17 runs, 780 mm, 8 of 1,101 regions in 17 jobs), only drawn thin lines, two passes; ours beans 137 regions (111 small letters). `bean_only_lines` (OFF) is the measured rule; region kappa -0.014 -> 0.129 ON
metadata:
  type: project
---

2026-10-27, Kent: the auto bean "doesn't recognize very well what should get a
bean stitch". `tools/bean_census.py` (one retrace detector for both files, ties
and underlay walks excluded, each run placed on OUR segmentation in the pro's
frame; `docs/bean-census-reference-2026-10-27.md`).

- **He beans almost nothing.** 17 retraced runs in 17 files, 780 mm, on 8 of
  1,101 regions: 16 are TWO passes at a median 1.31 mm pitch, one three-pass.
  627 of the 780 mm are the Drone's drawn panel and edge lines; the rest a
  line-drawn gun grip (ProSeal), the Golden Tee TM, short stubs. Edge of a
  filled body: 4 of 231, every one along a drawn outline stroke. Small letters
  under 1.2 mm: 1 of 251 (he raises them to satin). Solids under 2 mm: 0 of 81.
- **Ours beans 137 regions**: 111 small letters (bean letters, Fremont's THE /
  1895 are 58 of them), 24 thin regions, 2 bodies (run tier, edge cap).
- **Earlier numbers were ties and underlay.** `settings-vs-pro` row 19's 3,100
  pro bean stitches and `border_pro.bean_stats` counted tie-offs (3-5 retraced
  stations at every run end) and centre-walk underlay; filtered, his bean
  thread is ~1,200 stitches over 17 files. The 0.73 / 0.95 pitch figures stand
  for what little there is.
- **The rule** (`digitizer_core/bean_rule.py`, `cfg.bean_only_lines` OFF): a
  bean only on a LINE (smallest dimension <= 1.2 mm); a letter, a solid and a
  body's bare edge never. Wired into `routes_to_run` + the reactive rescue,
  `tag_bean_letters` and the bean edge cap. ON: ours 137 -> 21 bean regions,
  kappa -0.014 -> 0.129 (95% -0.010 to 0.305); Fremont's 58 bean letters sew
  satin (16,235 -> 15,755 stitches), ProSeal hat 6,781 -> 6,317; the Drone's
  thin lines keep their beans. Flat goldens byte-identical OFF.

**Why:** a bean classifier by SIZE cannot match a digitizer who beans by what the
element IS, and he barely beans at all.

**How to apply:** the flip is Kent's. The one thing he beans and we cannot is a
drawn detail line INSIDE a body our segmentation has no region for (Drone):
that is a stage-2 question (`keep_dark_thin_strokes`, #1160), not a bean rule.
Related: [[small-text-floor-2026-10-24]], [[fine-bars-satin-2026-10-25]],
[[tm-mark-golden-tee-2026-10-26]].
