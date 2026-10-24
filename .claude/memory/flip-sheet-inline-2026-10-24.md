---
name: flip-sheet-inline-2026-10-24
description: The flip sheet is now ONE self-contained HTML (`flip_sheet_renders report --inline`) because the desktop file pane cannot resolve relative image paths; three wave-1 layout flags added (inside stagger, enclosed-white keyline, wide letters). A flag with a `base` is diffed against its own OFF.
metadata:
  type: project
---

2026-10-24, task I2. `python -m tools.flip_sheet_renders report --inline SHEET.html
--date YYYY-MM-DD` writes the sheet with every crop as a base64 JPEG data URI
(11.7 MB for 13 flags / 130 images; re-encodes smaller down to 360 px if it would
pass `INLINE_MAX_MB` 15). Tests: `tests/test_flip_sheet_renders.py`.

**Why.** A relative `<img src>` shows broken boxes in the app's file viewer.

**New flags on the sheet.** `lettering_columns_inside_stagger` (#1058, number =
same-hole inner ends, read by `tools.inside_stagger` over the whole DST),
`enclosed_white_keyline` (#1059, white stitches / under 1 mm),
`text_cluster_wide_letters` (#1060, shapes tagged in a line, from the new
`tagged` field in stats.json -- a DST cannot carry it, so the pro's cell is n/a).

**Traps.**
- `enclosed_white_keyline` only acts under `sew_enclosed_white`: it has a `base`,
  so its OFF is arm `enclosed_white_keyline__off` (base alone), cached per
  engine like `off`. Diffing against bare OFF would have shown the whole
  white-faces change as the keyline's.
- A flag whose PR is open runs with `--engine <scratch merge of branch + main>`.
  Worktrees have no rembg venv: junction `digitizer/rembg_isolated/venv` to
  main's if you want the product's path -- but MFab OFF stayed 13,721 st (the
  10-23 sheet's number), not #1060's 11,605, so the sheet's MFab baseline is
  not #1060's measurement.
- Rendering is slow: a Fremont digitize cell took 12-23 min at `--jobs 3`, and
  `report` re-renders the whole design per tile (about 25 min for 13 flags).
- Old ten flags were reused from another lane's cache (`debug_out/flip_sheet`);
  the cache is gitignored, copy it, do not re-run.
