# stage0_scale_relative_grad ON: what the nine flat-lane tests say, with renders — 2026-11-06

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
