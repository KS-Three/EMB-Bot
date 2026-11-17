# `text_cluster_mixed_caps` — before | after, 2026-11-17

**Fault** (prime grader scorecard 2026-11-17, `toat_machine_hat` and `toat_beanie`): the small capital A of
"To A T" sews as a clump of mixed-direction patches with stray crossing stitches and its counter shut.

**Cause**, traced by eye and by number: the row's letters are T and T (11.9 mm tall), o (7.2 mm) and A (7.7 mm).
The letter door links two glyphs only within 0.8 of each other's height, so the T's pair, the o and A pair, no
pair reaches the 3-member minimum, nothing is tagged as lettering, and the column lane never sees the row. The A
falls to the generic satin: a left leg that folds over the top into a fan, a crossbar piece that runs into the leg.
The professional's A (read stitch by stitch from his hat file) is two level-crossed leg columns with a narrow open
gap and a short crossbar between them: not a thread limit, the counter is open in his file.

**Flag** `text_cluster_mixed_caps` (default OFF; byte-identical OFF): glyphs no cluster took are clustered once more
at a 0.6 height ratio (the existing `HEIGHT_BAND_MIN`), every other link unchanged; groups of 3+ tag.

**Population:** the 9 committed pro jobs, flag OFF vs ON. **2 designs moved, 7 are byte-identical** (Becker hat
large, Gaulke roofing hat, Fremont hat, MFab hat, Precision Drone, Tires hat 3D, Golden Tee hat).
**Both movers are pictured, every changed region of each (10 images).** Stitches / trims: hat 17,430 / 21 ->
17,319 / 19; beanie 17,357 / 24 -> 17,267 / 23.
Original is placed by fitting its ink box to the design box (approximate, not the kit's registration).
The professional's renders are not committed (public repo, `tests/pro_renders_allowlist.txt`).

| Design | Picture | What moved | By eye |
|---|---|---|---|
| hat | `toat_machine_hat__zoom2.jpg` | the small A | **better**: two legs, flat top, open triangle counter, short crossbar; the fan over the apex and crossing patches are gone |
| hat | `toat_machine_hat__zoom1.jpg` | first T and the o | T **better** (clean level bar, no diagonal patch over it); o no visible change |
| hat | `toat_machine_hat__zoom3.jpg` | second T | **better**: flat bar, no fanned crossing stitches |
| hat | `toat_machine_hat__zoom4.jpg` | second T's bar, left end | **better**: square end, no lumpy bulge |
| hat | `toat_machine_hat__whole.jpg` | whole design | the rest of the badge unchanged |
| beanie | `toat_beanie__zoom3.jpg` | the small A | **better**: legs and flat top read as the art; counter open; the crossbar patch is still a little lumpy |
| beanie | `toat_beanie__zoom1.jpg` | first T and the o | T **better**; o no visible change (inner edge slightly more faceted, not worse by eye) |
| beanie | `toat_beanie__zoom2.jpg` | second T | **better** |
| beanie | `toat_beanie__zoom4.jpg` | the i-dot of Machine | **neutral to better**: the dot now leans like the art's instead of a flat stack |
| beanie | `toat_beanie__whole.jpg` | whole design | the rest of the badge unchanged |

**Worse: none seen.** The remaining TOAT faults (script "Machine" pen flow, speed-line weight) are other
faults and do not move.

---

# Census, 2026-11-17 (director's request): 26 fixtures + the other pro rows

Settings: the Studio request at 80 mm on `left_chest` for the 26 `corpus_scorecard.FIXTURES`; each other
`pro_baseline.JOBS` row at its own garment and width. Compared by md5 of `design["stitches"]`, flag OFF vs ON.

**Fixtures: 3 of 26 moved; 3 pictured (every changed region); 23 byte-identical.**
**Other pro rows that resolve here (9 beyond the first 9): 2 moved, both pictured (9 images); 7 byte-identical**
(Becker hat small, Becker chest small, Becker LC large, Becker beanie, Gaulke LC, Gaulke beanie, Hotel Fremont
patch). 18 of the 22 JOBS rows resolve in this container (not Bridge hat / LC, ProSeal hat / beanie).
For photographs and for art with an unstitched margin the ORIGINAL panel is fitted by bounding box and is only
approximate; judge BEFORE against AFTER.

## WORSE (named first): none in the second run

**First run (flag as first built): 1 worse.** `screenshot_phone_ui_golke`: the "Photo" label tagged as a
mixed-height word (ascender over x-height) and the small-text re-set grew it to about twice its drawn size, low and
crowding the chevron (`first_run_golke_worse/`, 11,024 stitches).

**Fix (second run):** a line that tags only through the mixed-height pass is marked (`text_cluster_mixed_caps` in
the regions' meta) and goes to the column lane at its DRAWN size: `small_text.enlarge_small_text` and
`restore_small_text` skip it, and `regularize_text_clusters` never redraws it. A line that tags without the pass
is untouched. OFF is byte-identical (nothing is marked).

| Design | Pictures | By eye, second run |
|---|---|---|
| `screenshot_phone_ui_golke` (fixture) | `fixture_screenshot_phone_ui_golke__whole.jpg`, `__zoom1`, `__zoom2` | **no visible change.** "Photo" is back at its drawn size, the same as OFF. The two remaining changed regions (the truck's chrome, a grille patch) show no visible difference. 10,864 -> 10,858 stitches, trims 125 -> 127. |

The TOAT jobs and every other mover are unchanged by this fix (identical stitch counts in both runs), so their
pictures above stand.

## Better

| Design | Pictures | By eye |
|---|---|---|
| `toat_machine_beanie` (pro row) | `otherrow_toat_machine_beanie__zoom1..3`, `__whole` | **Better**, as the other TOAT jobs: the small A has two legs, a flat top and an open counter; the T bars lose the fanned patch (the first T's bar ends in a slant cut, as the art's does). 17,012 -> 16,961 stitches, trims 21 -> 19. |

## No visible change

| Design | Pictures | By eye |
|---|---|---|
| `drone_render` (fixture) | `fixture_drone_render__zoom1..4`, `__whole` | no visible change: a few grey patches in the hero art shift at the sub-millimetre level. 18,337 -> 18,342 stitches. |
| `repro_gradient_white_icon` (fixture) | `fixture_repro_gradient_white_icon__zoom1`, `__whole` | no visible change at the size shown (the lower-right border's thread differs by a few stitches). 22,911 -> 22,813. |
| `mfab_lc` (pro row) | `otherrow_mfab_lc__zoom1..4`, `__whole` | no visible change: connector and fan stitches shift inside the lettering. 17,906 -> 17,966, trims 24 -> 26. |

**Totals (second run):** 9 + 9 pro rows + 26 fixtures = 44 designs; 7 moved (the 3 TOAT rows are one artwork, plus 3
fixtures and `mfab_lc`), every mover pictured. By eye: 3 better (all TOAT), **0 worse**, 4 no visible change
(`drone_render`, `repro_gradient_white_icon`, `golke screenshot`, `mfab_lc`).

---

# Flip withdrawn, 2026-11-17: the gradient icon's bands were tagged as lettering

Kent's "Flip ON" was given on "none worse across 44". With the flag ON as the default, CI's digitizer shard 1/6
failed `tests/test_borders_last.py::test_repro_fixture_border_satin_sews_after_its_cone_s_fills`: on
`repro_gradient_white_icon` (90 mm) six of the icon's own gradient shapes (a 645 mm2 ramp body, a 258 and a 114 mm2
band, three slivers of 34-83 mm2) were tagged as LETTERING by the mixed-height pass and left the satin/fill ladder,
which reordered a block (a satin at rank (1,3) sewed before a fill of its own cone at (1,4)).
`repro_icon_shapes_tagged_as_lettering.png` draws them (red). **The census above called this design "no visible
change", and it was: the sewn picture hid a wrong tag.** The test caught what the eye did not. The flip is reverted;
the flag is built OFF again. A bound on what the pass may admit is a separate follow-up.
