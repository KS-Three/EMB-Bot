# Flip sheet 2026-10-29: OFF | ON | pro, one crop per flag and fixture

Kent's ruling 2026-10-22: stitch layout is judged in the preview; only pull and comp need fabric. Every row here is a layout flag built OFF, rendered where it changes stitches, beside the professional's file for the same job. The flips are Kent's; nothing in this PR changes a default.

Open `./index.html` for the pictures side by side. The pro's crops are not committed (Kent 2026-10-27: "Stop new ones, keep old (Recommended)"): they are written to `pro_renders/`, gitignored, and `report --inline` puts them on the local page. Regenerate with `python -m tools.flip_sheet_renders run` then `report` (see the tool's docstring; a flag not on main runs with `--engine <checkout>`).

Each cell: stitches / trims / the number the flag is about. Crops are 18 x 11 mm at 40 px/mm, placed on the window holding the most changed needle points (OFF vs ON, 0.05 mm grid); the pro's crop is the same window as a fraction of his extents, no registration. The hat preset at the pro's width (Fremont at Kent's 92.5).

| flag (PR) | fixture | engine | OFF | ON | pro | changed points | crop |
|---|---|---|---|---|---|---|---|
| `edge_cap_satin` (#1191) | hotel_fremont_hat | engine 44ecf1cb | 15,865 st / 25 tr / 3 cc / 0 | 15,865 st / 25 tr / 3 cc / 0 | 17,067 st / 21 tr / 10 cc / n/a (DST has no roles) | **no change** (byte-identical DST) | - |
| `edge_cap_satin` (#1191) | becker_hat_small | engine 44ecf1cb | 10,270 st / 13 tr / 1 cc / 0 | 10,286 st / 13 tr / 2 cc / 1 | 8,694 st / 11 tr / 4 cc / n/a (DST has no roles) | 16 (16 in crop) | [off](./edge_cap_satin__becker_hat_small__off.jpg) [on](./edge_cap_satin__becker_hat_small__on.jpg) pro (local only) [where](./edge_cap_satin__becker_hat_small__where.jpg) |
| `edge_cap_satin` (#1191) | gaulke_roofing_hat | engine 44ecf1cb | 7,446 st / 30 tr / 1 cc / 0 | 7,446 st / 30 tr / 1 cc / 0 | 6,138 st / 42 tr / 0 cc / n/a (DST has no roles) | **no change** (byte-identical DST) | - |
| `edge_cap_satin` (#1191) | precision_drone | engine 44ecf1cb | 14,491 st / 83 tr / 9 cc / 0 | 14,491 st / 83 tr / 9 cc / 0 | 14,552 st / 59 tr / 22 cc / n/a (DST has no roles) | **no change** (byte-identical DST) | - |
| `edge_cap_bean_legacy` (#1191) | hotel_fremont_hat | engine 44ecf1cb | 15,865 st / 25 tr / 3 cc / 0 | 15,839 st / 25 tr / 3 cc / 0 | 17,067 st / 21 tr / 10 cc / n/a (DST has no roles) | 430 (336 in crop) | [off](./edge_cap_bean_legacy__hotel_fremont_hat__off.jpg) [on](./edge_cap_bean_legacy__hotel_fremont_hat__on.jpg) pro (local only) [where](./edge_cap_bean_legacy__hotel_fremont_hat__where.jpg) |
| `edge_cap_bean_legacy` (#1191) | becker_hat_small | engine 44ecf1cb | 10,270 st / 13 tr / 1 cc / 0 | 10,270 st / 13 tr / 1 cc / 0 | 8,694 st / 11 tr / 4 cc / n/a (DST has no roles) | **no change** (byte-identical DST) | - |
| `edge_cap_bean_legacy` (#1191) | gaulke_roofing_hat | engine 44ecf1cb | 7,446 st / 30 tr / 1 cc / 0 | 7,474 st / 31 tr / 2 cc / 2 | 6,138 st / 42 tr / 0 cc / n/a (DST has no roles) | 28 (14 in crop) | [off](./edge_cap_bean_legacy__gaulke_roofing_hat__off.jpg) [on](./edge_cap_bean_legacy__gaulke_roofing_hat__on.jpg) pro (local only) [where](./edge_cap_bean_legacy__gaulke_roofing_hat__where.jpg) |
| `edge_cap_bean_legacy` (#1191) | precision_drone | engine 44ecf1cb | 14,491 st / 83 tr / 9 cc / 0 | 14,457 st / 83 tr / 10 cc / 1 | 14,552 st / 59 tr / 22 cc / n/a (DST has no roles) | 116 (64 in crop) | [off](./edge_cap_bean_legacy__precision_drone__off.jpg) [on](./edge_cap_bean_legacy__precision_drone__on.jpg) pro (local only) [where](./edge_cap_bean_legacy__precision_drone__where.jpg) |

## What each number is

- `edge_cap_satin`: edge-cap runs. Sets `{"edge_cap": "satin"}`. **OFF is the shipped engine: edge_cap 'bean', which bean_only_lines (ON since 2026-10-27) turns into no cap. ON is the satin style, the one cap style still live. docs/edge-cap-remeasure-2026-10-29.md has the silhouette and size sweep.**
- `edge_cap_bean_legacy`: edge-cap runs. Sets `{"edge_cap": "bean", "bean_only_lines": false}`. **The bean cap as it sewed 2026-09-11 to 10-27, with bean_only_lines OFF so the bean style is not turned off. bean_only_lines OFF also moves bean letters and the run tier, so ON differs from OFF in more than the cap: read the rings.**

Readers: stitches and trims are pystitch records (the pro read as DST, never PES: the PES reader reports a TRIM at every jump). `stitches under 0.5 mm` are needle-to-needle. `fills read BARE` is `tools/pro_fill_underlay.py`. `uncut jumps` are needle-up hops with no TRIM or colour change round them. `white thread` reads the file's own colours (the pro's PES; a DST has none). `hops under later thread` is `tools/trim_classes.py`. `edge-cap rings` are plan run roles, so the pro has none. `run starts that lock`: the first three stitches after a cut, colour change or jump all at most 1.0 mm with a reversal. `short columns bare` is `tools/pro_satin_underlay.py` (PR #1044's branch). `letter height` is the median of `tools/small_text_columns.py`'s 0.8-6 mm pieces.

