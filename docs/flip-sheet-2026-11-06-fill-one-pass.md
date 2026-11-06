# Flip sheet 2026-11-06: OFF | ON | pro, one crop per flag and fixture

Kent's ruling 2026-10-22: stitch layout is judged in the preview; only pull and comp need fabric. Every row here is a layout flag built OFF, rendered where it changes stitches, beside the professional's file for the same job. The flips are Kent's; nothing in this PR changes a default.

Open `renders/flip-sheet-2026-11-06-fill-one-pass/index.html` for the pictures side by side. The pro's crops are not committed (Kent 2026-10-27: "Stop new ones, keep old (Recommended)"): they are written to `pro_renders/`, gitignored, and `report --inline` puts them on the local page. Regenerate with `python -m tools.flip_sheet_renders run` then `report` (see the tool's docstring; a flag not on main runs with `--engine <checkout>`).

Each cell: stitches / trims / the number the flag is about. Crops are 18 x 11 mm at 40 px/mm, placed on the window holding the most changed needle points (OFF vs ON, 0.05 mm grid); the pro's crop is the same window as a fraction of his extents, no registration. The hat preset at the pro's width (Fremont at Kent's 92.5).

| flag (PR) | fixture | engine | OFF | ON | pro | changed points | crop |
|---|---|---|---|---|---|---|---|
| `fill_one_pass_sections` (#1270) | becker_hat_large | engine 5777f91c | 16,262 st / 11 tr / 1 cc / 2 / 11 | 16,262 st / 11 tr / 1 cc / 2 / 11 | 12,356 st / 10 tr / 4 cc / 1 / 9 | **no change** (byte-identical DST) | - |
| `fill_one_pass_sections` (#1270) | becker_lc_large | engine 5777f91c | 14,830 st / 14 tr / 1 cc / 5 / 14 | 14,830 st / 14 tr / 1 cc / 5 / 14 | 11,274 st / 12 tr / 3 cc / 2 / 11 | **no change** (byte-identical DST) | - |
| `fill_one_pass_sections` (#1270) | becker_hat_small | engine 5777f91c | 10,541 st / 11 tr / 1 cc / 4 / 11 | 10,541 st / 11 tr / 1 cc / 4 / 11 | 8,694 st / 11 tr / 4 cc / 2 / 10 | **no change** (byte-identical DST) | - |
| `fill_one_pass_sections` (#1270) | becker_chest_small | engine 5777f91c | 10,309 st / 11 tr / 1 cc / 4 / 11 | 10,309 st / 11 tr / 1 cc / 4 / 11 | 8,694 st / 12 tr / 3 cc / 2 / 11 | **no change** (byte-identical DST) | - |
| `fill_one_pass_sections` (#1270) | becker_beanie | engine 5777f91c | 13,862 st / 14 tr / 2 cc / 6 / 14 | 13,747 st / 13 tr / 2 cc / 5 / 13 | 11,412 st / 48 tr / 5 cc / 0 / 4 | 377 (107 in crop) | [off](renders/flip-sheet-2026-11-06-fill-one-pass/fill_one_pass_sections__becker_beanie__off.jpg) [on](renders/flip-sheet-2026-11-06-fill-one-pass/fill_one_pass_sections__becker_beanie__on.jpg) pro (local only) [where](renders/flip-sheet-2026-11-06-fill-one-pass/fill_one_pass_sections__becker_beanie__where.jpg) |

## What each number is

- `fill_one_pass_sections`: cuts inside one piece / all cuts. Sets `{"photo_prep_background_removal_timeout_s": 900, "fill_one_pass_sections": true}`. **Seam order's progression re-planned so a free section the needle reaches hidden (over unsewn ground, or under rows still to come) goes before the nearest, and the fill phase sews those hidden routes. Lay read first; kept only where it removes a hop past LINK_MAX_GAP_MM (one stage 7 could never bury), cuts no more and lays no more on finished fill than seam order's own order; a shape not re-planned is byte-identical. Both arms pin the rembg timeout at 900 s.**

Readers: stitches and trims are pystitch records (the pro read as DST, never PES: the PES reader reports a TRIM at every jump). `stitches under 0.5 mm` are needle-to-needle. `fills read BARE` is `tools/pro_fill_underlay.py`. `uncut jumps` are needle-up hops with no TRIM or colour change round them. `white thread` reads the file's own colours (the pro's PES; a DST has none). `hops under later thread` is `tools/trim_classes.py`. `edge-cap rings` are plan run roles, so the pro has none. `run starts that lock`: the first three stitches after a cut, colour change or jump all at most 1.0 mm with a reversal. `short columns bare` is `tools/pro_satin_underlay.py` (PR #1044's branch). `letter height` is the median of `tools/small_text_columns.py`'s 0.8-6 mm pieces.

