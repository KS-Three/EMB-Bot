---
name: pro-renders-local-only-2026-10-27
description: Kent 2026-10-27 "Stop new ones, keep old (Recommended)": no new render of the pro's stitch files under docs/ (public repo); they go to gitignored pro_renders/; a name-based guard test allowlists the 211 kept.
metadata:
  type: project
---

Kent ruled 2026-10-27, verbatim: **"Stop new ones, keep old (Recommended)"**, on
renders of the professional's stitch files in this PUBLIC repo. The 211 images
under docs/ that a name marks as pro-derived stay (none moved or deleted).

- `tools/pro_renders.py`: `ROOT` = repo `pro_renders/` (gitignored), `out_dir`,
  and `marks_pro`: a path is pro-derived when any word of a folder or the stem
  (split on non-alphanumerics) is `pro`, `pro<digits>` or `professional`. Not
  `proseal`, `repro`, `promoted`.
- `tests/test_no_new_pro_renders.py` fails on any committed docs/ image the rule
  flags that is not in `tests/pro_renders_allowlist.txt` (generated once from
  main 8341d1f7). `git ls-files` and names only.
- Defaults moved off docs/: `flip_sheet_renders report` writes the pro's tiles
  to `--pro-renders` (ours still to `--renders`; `--inline` reads both, the md
  names the pro crop without a link); `flip_eight_proof --out`;
  `border_census --crops`; `lane_census sheet`. The last two now put `_pro` in
  their composite names.

**Why:** the repo is world-readable; the pro's files are a third party's work.

**How to apply:** a new pro panel goes to `tools.pro_renders.out_dir(...)`, never
docs/. Name every composite that holds a pro panel with a `pro` word: the guard
reads names, so `pro_pair`'s `sheet_whole.png` or `bay_census`'s `<slug>.png`
passed explicitly into docs/ would slip past it. A file the rule flags that is
not pro-derived: rename it. Adding to the allowlist is Kent's call.
