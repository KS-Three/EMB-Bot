# two_tone_snap flipped ON (2026-10-08)

OFF left, ON right, one PNG per fixture, drawn by `digitizer/tools/two_tone_probe.py --render`
(`digitizer_core.stitchviz.render_design`) at the Studio's config (80 mm, left_chest, 6 colours),
downscaled to 1600 px wide. **Nothing here has been sewn.**

| file | colours off → on | stitches off → on | trims off → on | read |
|---|---|---|---|---|
| `logo_golke_roofing.png` | 5 → 2 | 5,043 → 5,328 | 33 → 34 | better: roof chevron, window cross and the zigzag under the sun sew white (`two_tone.keep_lines`) |
| `logo_gaulke_roofing.png` | 2 → 2 | 4,574 → 4,860 | 31 → 35 | better: roof chevron and window cross, lost OFF, sew white |
| `logo_mfab_lc.png` | 6 → 2 | 10,907 → 9,743 | 75 → 54 | better: white linework sews white, not four greys |
| `logo_toat_machine.png` | 6 → 2 | 6,783 → 6,601 | 40 → 29 | better: speed lines in one colour |

The other fixtures (mfab_hat, toat_beanie, script_tires, black_ground_holes, and the controls
screenshot_phone_ui_golke, logo_bridge_bar, logo_hotel_fremont) are in the PR body's table; the
controls and black_ground_holes are byte-identical OFF and ON.

Reproduce: `cd digitizer && .venv/bin/python -m tools.two_tone_probe --render OUT`.
