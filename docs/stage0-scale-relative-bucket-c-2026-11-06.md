# stage0_scale_relative_grad ON: what the nine flat-lane tests say, with renders — 2026-11-06

> **Ruling, Kent 2026-11-07: "Accept the plan (Recommended)"** on PR #1301's
> bucket (c). Each row's resolution in that PR:
>
> - **Rows 1, 3, 7, 10: re-pinned to the flip + cure values.** Row 1 is 9 bean
>   letters, and its spine gate goes 0.98 -> 0.95 (one letter, Saa1fcd57, keeps
>   0.96 of its spine inside). Row 3: 7 of the 12 labels still exist at 80 mm,
>   and the one word has 7 members, 4 of them carried labels. Row 7 is 119.8 /
>   127.2 mm² in one cone. Row 10: 4 holes in both arms, and no counter to tag.
> - **Rows 8, 9: held on the pre-flip route (`PRE_FLIP`)**, where their
>   premise lives. Row 9's `robust_region_colour` is the gradient lane's
>   statistic, so the whole Bridge section of that file holds the route.
> - **Rows 5, 6: the screenshot's hand labels re-read** onto the new engine's
>   shape ids by polygon IoU. All 35 letters carry (IoU >= 0.72, same thread);
>   one id moved, S0b58b7a7 -> S91804e04. 13 of the 36 ignore ids split on the
>   flat lane and were dropped. The old lines are kept as
>   `lines_pre_flip_route` for the pre-flip-tagger arms, which run on that
>   route.
> - **Row 4: re-pinned to the refusal set {S643e40d2}. Kent to eyeball later**
>   (golden_tee's house-only swash the ink link now refuses).
> - Row 2 was repaired by the cure; nothing to pin.

Evidence for Kent's call on the nine tests PR #1282 left failing. A count is not
a verdict; the render is. Every image is committed test art
(`digitizer/testdata/photo/logo_bridge_bar.jpg`, `logo_golden_tee.jpg`,
`screenshot_phone_ui_golke.jpg`) digitized the Studio's way
(`tools.pro_pair.digitize`) once with `stage0_scale_relative_grad` False (the
shipped engine until this PR) and once True, rendered by
`digitizer_core.stitchviz`. No third-party stitch file is read or drawn.
Instrument: `digitizer/tools/stage0_flip_renders.py`. Sheets:
`docs/renders/stage0-scale-relative-2026-11-06/` (left OFF, right ON, whole
design at 10 px/mm; `*_lettering.jpg` is a 30 px/mm crop of the text band).

## The sheets

| sheet | size | OFF lane / stitches / trims / regions / colours | ON lane / stitches / trims / regions / colours |
|---|---|---|---|
| [bridge_hat](renders/stage0-scale-relative-2026-11-06/bridge_hat.jpg), [lettering](renders/stage0-scale-relative-2026-11-06/bridge_hat_lettering.jpg) | 113.5 mm hat | gradient / 33,996 / 45 / 56 / 7 | flat / 41,853 / 157 / 204 / 6 |
| [bridge_lc](renders/stage0-scale-relative-2026-11-06/bridge_lc.jpg), [lettering](renders/stage0-scale-relative-2026-11-06/bridge_lc_lettering.jpg) | 96 mm left chest | gradient / 17,648 / 36 / 55 / 6 | flat / 28,048 / 131 / 162 / 6 |
| [golden_tee](renders/stage0-scale-relative-2026-11-06/golden_tee.jpg), [lettering](renders/stage0-scale-relative-2026-11-06/golden_tee_lettering.jpg) | 80 mm left chest | gradient / 11,858 / 41 / 46 / 10 | flat / 14,237 / 57 / 94 / 7 |
| [screenshot](renders/stage0-scale-relative-2026-11-06/screenshot.jpg), [lettering](renders/stage0-scale-relative-2026-11-06/screenshot_lettering.jpg) | 80 mm left chest | gradient / 7,761 / 55 / 149 / 7 | flat / 11,607 / 131 / 287 / 6 |

Bridge hat/left chest are rendered at the 113.5 and 96 mm widths. The other two
at 80 mm left chest; no reference size is read for them.

## What the render shows (my read, from the pictures)

- **Bridge, both sizes: a loss.** The teal ring, anchor and "BAR & RESTAURANT"
  sew olive-brown and pale blue instead of teal (hat threads: 0501/1720/4531/5010
  OFF -> 0442/1521/4752/6156 ON; black and 0713 in both); the lettering band turns to yellow-over-blue
  blotches, the red "Bridge" gets yellow flecks along its edges, and every
  spoke and the ring gain a pale-blue outline pass. Trims 45 -> 157 (hat),
  36 -> 131 (left chest); stitches +23% / +59%.
- **golden_tee: mixed, leaning acceptable.** ON sews the red edge strokes of
  "GT" the source art has (rust brown) and drops the cream gradient bevel;
  "GOLF" reads darker-outlined with an orange face. All three swashes (tee arc,
  tee stem, shadow) are still sewn.
- **screenshot: an improvement.** The truck goes from dark grey to black, and
  "Done", "Photo", "835" are legible where OFF garbled them ("Dane", "Phoe");
  a little white speckle appears on the truck's front.

## The nine assertions

| # | test | what it measures | OFF value | ON value | read |
|---|---|---|---|---|---|
| 1 | `test_bean_outlined_ink::test_on_bridge_keeps_its_eight_bean_letters` | Bridge letters (80 mm) tagged as bean letters | 8 | 15 | **loss** on the render: the extra bean runs are the blotchy lettering above |
| 2 | `test_bean_letters_pipeline[bridge]::test_bridges_words_are_tagged_and_sew_as_runs_along_their_ink` | members of the text cluster vs members tagged bean, must be equal | every member tagged (>= 6) | 15 members, 7 tagged | **unknown**: half the cluster no longer takes the bean route; render shows mixed run/fill letters |
| 3 | `test_words[bridge]::test_bridge_50mm_bar_and_restaurant_is_freed_from_the_badge` | labelled letters of "BAR & RESTAURANT" that the position-carry finds at 50 mm | 12 | 4 | **loss/unknown**: the letters' regions no longer exist as labelled (merged/fragmented by the flat lane's trace) |
| 4 | `test_column_capture::test_ink_link_keeps_golden_tees_swashes` | house-group swashes the ink-link guard refuses | 0 | 1 (`S643e40d2`) | **unknown**: the render still sews every swash; whether the refused piece matters needs Kent's eye on that shape |
| 5 | `test_column_capture::test_ink_link_sees_the_screenshot_icons_once_the_text_clusters_are_one_ink` | hand-labelled letters (shape ids) of the screenshot fixture | labels match | no label matches (ids moved with the lane) | **not a verdict**: needs the census re-read; the screenshot render itself **improves** |
| 6 | `test_column_capture::test_icon_guard_refuses_the_screenshot_captures_and_no_letter` | same labels, icon guard arm | labels match | no label matches | same as 5 |
| 7 | `test_work_grid::test_bridges_teal_words_survive_tracing_on_the_working_grid` | teal mm2 kept at 4 px/mm (the defect) and at 8 px/mm (shipped) | 78.9 mm2 (defect) / 186.9 mm2 (shipped) | 119.8 / 142.4 | **loss**: shipped teal drops 187 -> 142 mm2 (-24%); the 4 px/mm defect is gone only because the flat lane loses teal differently |
| 8 | `test_clip_keep_pieces::test_bridge_halo_lever_takes_most_of_the_flips_halo` | grey JPEG-ringing pieces kept, lever (`dissolve_phantom_blends`) OFF / ON | 25.6 -> 4.1 mm2 | 8.9 -> 8.9 mm2 (the lever does nothing on the flat lane) | **loss, minor**: 4.1 -> 8.9 mm2 of ringing stays on the shipped setting |
| 9 | `test_robust_region_colour[bridge_pair]::..._sews_the_disc_limelight_and_the_shipped_one_sews_the_artworks_yellow` | thread the yellow disc sews: pre-flip colour arm / shipped colour arm | 6031 Limelight / 0501 Sun (1.0 dE00) | 0713 Lemon / 0713 Lemon (2.1 dE00) | **loss, minor**: the disc yellow moves 1.0 -> 2.1 dE00 off the artwork; the test's pre-flip arm no longer reproduces the Limelight loss it documents |

Measured with `PipelineConfig(target_width_mm=80.0, garment_id="left_chest")`
for rows 1, 7, 8, 9 (the tests' own helpers); rows 2-6 are the failing
assertion values from CI run 42293897109.

## Options per row (the foreman asked for no re-pin before the ruling)

- **Re-pin to the ON value** only where the read is "improvement" or "minor" and Kent agrees (5, 6 after a census re-read; 8, 9 are minor losses).
- **Pin OFF** (bucket (b) posture) where the premise is a pre-flip engine arm (9's OFF arm, 5/6 labels) and the behaviour is judged elsewhere.
- **Hold the flip** if Kent reads the Bridge render as a loss: rows 1, 3, 7 are the same Bridge teal/lettering loss counted three ways.

## Re-flip with the flat soft-edge cure (PR #1301, CI run 42344423957)

Kent, 2026-11-06, after `docs/flat-fringe-soft-ramp-2026-11-06.md`: "Re-open
flip + both flags (Recommended)". `stage0_scale_relative_grad`,
`flat_page_fringe_soft_ramp` and `flat_ramp_blend_dissolve` are ON together.
Bridge's flat-lane render is the right-hand panel of
[bridge_hat](renders/flat-fringe-soft-ramp-2026-11-06/bridge_hat.jpg) /
[bridge_lc](renders/flat-fringe-soft-ramp-2026-11-06/bridge_lc.jpg) and the
two `*_lettering.jpg` crops beside them (left main, middle flip alone, right
flip + cure). golden_tee and the screenshot are byte-identical with and without
the cure (not enlarged at 80 mm), so their sheets above still stand.

| # | test | OFF (main) | flip alone | **flip + cure** | read |
|---|---|---|---|---|---|
| 1 | `test_on_bridge_keeps_its_eight_bean_letters` | 8 | 15 | **9** | near main; the render's lettering reads as main's |
| 2 | `test_bridges_words_are_tagged_and_sew_as_runs_along_their_ink` | pass | 7 of 15 | **pass** | repaired by the cure |
| 3 | `test_bridge_50mm_bar_and_restaurant_is_freed_from_the_badge` | 12 | 4 | **7** | better than flip, short of main |
| 4 | `test_ink_link_keeps_golden_tees_swashes` | 0 | 1 | **1** (`S643e40d2`) | stage-0 effect, cure does not touch it |
| 5 | `test_ink_link_sees_the_screenshot_icons_...` | labels match | stale | **stale** | stage-0 effect; census re-read |
| 6 | `test_icon_guard_refuses_the_screenshot_captures_...` | labels match | stale | **stale** | same as 5 |
| 7 | `test_bridges_teal_words_survive_tracing_on_the_working_grid` | 78.9 / 186.9 mm² | 119.8 / 142.4 | **119.8 / 127.2**, one cone 4531 | art's teal ~96 mm² (the test's docstring); main's 187 counts the waves it sews teal; the 4 px/mm defect no longer reproduces |
| 8 | `test_bridge_halo_lever_takes_most_of_the_flips_halo` | 25.6 -> 4.1 mm² | 8.9 -> 8.9 | **5.8 -> 5.8** | premise gone (needs >= 10 mm² to exercise) |
| 9 | `..._sews_the_disc_limelight_and_the_shipped_one_sews_the_artworks_yellow` | 6031 / 0501 | 0713 / 0713 | **0713 / 0713** | disc Lemon (2.1 dE00) not Sun (1.0); not moved by the cure |
| 10 | `test_keep_counters::test_the_blocks_get_their_gaps_back_and_no_counter_is_sewn[flat]` | holes 0 -> 2 (flag OFF -> ON) | (not failing) | **4 -> 4** | NEW, the cure's: forced flat, the synthetic panel's four teal blocks keep all four counters even with `keep_counters` OFF (yellow gap's ramp no longer absorbed); with it ON, 4 counters kept unsewn where main kept 2. Improvement; premise (OFF has fewer) gone |

Bucket (b) in this PR, beyond #1282's 29: `test_subpixel_edges::
test_the_resolution_gate_lifts_only_with_the_flag_on` holds the cure OFF. Its
x2-enlarged synthetic disc's subpixel-OFF baseline moves 22 -> 30 vertices
(area 316.2 -> 315.8 mm², true 314.2) while the shipped subpixel-ON polygon is
unchanged (33 vertices, 312.6 mm²); it measures `subpixel_edges`' lift.
`test_flat_page_fringe.py` holds both cure flags OFF (it is about
`flat_page_fringe_exclude`).
