#!/usr/bin/env python
"""flip_sheet_renders: one page Kent flips layout flags from -- OFF | ON | pro.

WHAT IT IS FOR. Kent ruled 2026-10-22 that stitch LAYOUT is judged in the
preview and only pull weight and compensation need fabric. So every parked
flag that moves where stitches go is decided from pictures beside the
professional's file for the same job, not from a sew-out. This tool makes
that page: for each flag, on each paired fixture, the same crop three ways
at a zoom where single stitches show, with the crop chosen where the flag
actually changes something, and under it the stitch count, the trim count
and one number the flag is about -- for OFF, ON and the pro.

    .venv/Scripts/python -m tools.flip_sheet_renders run [--flags A B] [--fixtures S ...]
        [--engine DIR] [--cache DIR] [--jobs 3]
    .venv/Scripts/python -m tools.flip_sheet_renders report [--out DOCS_MD] [--renders DIR]
        [--pro-renders DIR] [--inline SHEET.html [--date YYYY-MM-DD]]

HOW. `run` digitizes each fixture the Studio's way (`tools.pro_pair.digitize`,
the hat preset at the pro's width) once OFF and once per flag ON, writes
each as a DST (`digitizer_core.export.write_dst`, the file a customer gets)
and caches it with the plan's design and run roles under `--cache`
(resumable: a cell that exists is not re-run). `report` reads every DST --
ours and the pro's -- with ONE reader per number (pystitch), diffs OFF and
ON by needle-down points (0.05 mm grid), slides a 18 x 11 mm window over the
points that differ and crops all three renders there, 40 px/mm. A cell whose
diff is zero prints "no change" with the count that proves it instead of
three identical pictures.

A flag that is not on `main` yet is run from its PR branch: pass `--engine
DIR` (a checkout root) and that checkout's `digitizer_core` is imported in
place of this one; the cache records the engine's commit, and the OFF cell
is cached PER ENGINE so a branch flag is diffed against its own OFF.

NUMBERS. Every metric is read off the DST so OFF, ON and the pro are read
by the same rule; where a number needs the plan's run roles (edge-cap rings)
the pro's cell says so. The readers are the repo's own: `tools.
pro_fill_underlay` (fills BARE), `tools.trim_classes` (hops under later
thread), `tools.small_text_columns` (letter pieces), and -- on the branch
that carries it -- `tools.pro_satin_underlay` (short columns bare).

`report --inline SHEET.html` also writes ONE self-contained page: every image
is a base64 data URI, so a viewer that cannot resolve relative paths (the
desktop app's file pane) shows the pictures. It stays under `INLINE_MAX_MB`
by re-encoding the crops smaller until it fits.

The pro's crops never go under docs/ (Kent 2026-10-27: "Stop new ones, keep
old (Recommended)"): `report` writes them to `--pro-renders`, gitignored
`pro_renders/` by default, and ours to `--renders`. The inlined page reads
both, so it keeps the pro's panels; it stays local. The markdown names the
pro's crop without linking it.

A flag with a `base` (`enclosed_white_keyline` only acts under
`sew_enclosed_white`) is diffed against its OWN OFF -- the base sets alone,
cached as arm `<flag>__off` -- not against the bare engine.

Each flag has a KIND (2026-10-26): LAYOUT, judged from these renders (Kent
2026-10-22), or FABRIC, ROADMAP gate 1 -- it needs a sew-out (underlay, locks,
anything the preview cannot show). The page groups its rows by flag, each
under its kind with stitches, trims and colour changes OFF -> ON -> pro.

A flag the Studio's request cannot carry (`cfg.extra` keys: the service's
parser refuses `extra`) sets it as `sets: {"extra": {...}}`; the cell lays
that onto the parsed config, for that digitize only.

Nothing here changes an engine default; the flips are Kent's.
"""
from __future__ import annotations

import argparse
import base64
import contextlib
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools._console import utf8_console  # noqa: E402
from tools import pro_renders  # noqa: E402

DATE = "2026-10-23"
PPM = 40.0                  # crop renders: 0.4 mm thread = 16 px
PAD_MM = 2.0                # stitchviz.render_design's pad
WINDOW_MM = (18.0, 11.0)    # the crop, mm (w, h)
GRID_MM = 0.05              # needle-point grid for the OFF/ON diff
INLINE_MAX_MB = 15.0        # the inlined page's ceiling
INLINE_LEVELS = [(None, None), (85, 720), (75, 600), (65, 480), (55, 360)]  # (jpeg q, max width)
LOCK_LEG_MM = 1.0           # a lock's legs are at most this
DEFAULT_CACHE = DIGITIZER / "debug_out" / "flip_sheet"
DEFAULT_DOC = DIGITIZER.parent / "docs" / f"flip-sheet-{DATE}.md"
DEFAULT_RENDERS = DIGITIZER.parent / "docs" / "renders" / f"flip-sheet-{DATE}"
#: the pro's tiles (`pro`, `pro_xray`): local only, never docs/ (Kent 2026-10-27,
#: "Stop new ones, keep old (Recommended)"; `tools.pro_renders`). Ours stay in
#: `DEFAULT_RENDERS`; `--inline` reads both, so the local page keeps every panel.
#: `report` names the pro's folder after `--renders`' own.
DEFAULT_PRO_RENDERS = pro_renders.out_dir(DEFAULT_RENDERS.name)

#: (slug in `tools.border_census.PAIRS`, width mm or None for the pro's).
#: Fremont at 92.5: Kent's own job width (`fremont_triage.KENT_WIDTH_MM`),
#: 0.1 mm under the pro's extents.
FIXTURES: list[tuple[str, float | None]] = [
    ("hotel_fremont_hat", 92.5),
    ("becker_hat_small", None),
    ("mfab_hat", None),
]

#: Pairs `tools.border_census.PAIRS` lacks, in its row shape (slug, pro file,
#: art, garment), for a flag's own `fixtures`. A job `tools.pro_intake`
#: registered is found by its slug too (`--fixtures SLUG`).
EXTRA_PAIRS = [
    ("proseal_beanie", "Proseal/PROSEALHAT BEANI.DST", "Proseal/PROSeal Logo.jpg", "beanie"),
]

#: Art for a job whose customer file is only on Google Drive (G:), used when
#: G: is not mounted: the committed corpus crops (#556), cut from the pro's
#: preview at ~400 px. A cell digitized from one may differ from a PR's cell
#: digitized from the customer's file; `fixture_files` says which it used
#: (on 2026-10-24 MFab's counts matched #1064's exactly).
ART_FALLBACK = {
    "mfab_hat": DIGITIZER / "testdata" / "art" / "logo_mfab_hat.png",
    "mfab_lc": DIGITIZER / "testdata" / "art" / "logo_mfab_lc.png",
}

#: The flags. `sets` is laid over the Studio request (`--set` in pro_pair);
#: `metric` names a reader below; `about` is the column heading; `pr` the PR
#: that built it. Add a row here and the next `run`/`report` carries it.
#: Optional: `base` (the flag acts only on top of these; OFF is the base, not
#: the bare engine), `base_name` (flags with the SAME base share one OFF arm
#: under that name instead of digitizing it once each), `fixtures` (the jobs
#: the flag is about; FIXTURES otherwise), `kind` ("LAYOUT", the default:
#: judged from renders; "FABRIC": gate 1, a sew-out).
_SMALL_TEXT_SET = {"small_text_cap_mm": 4.0, "small_text_cap_max_width_scale": 1.05,
                   "small_text_cap_min_stroke_mm": 0.85, "small_text_cap_letter_gap_mm": 0.25,
                   "small_text_cap_bold_scale": 1.45, "lettering_columns_small_bold": True}
_WHITE_SEWN = {"sew_enclosed_white": True, "enclosed_white_keyline": True}
#: the engine before the 2026-10-26 flips (both ON by default since), with rembg's
#: timeout pinned: its 60 s default fails under load and reroutes MFab (photo_scene)
_REMBG_900 = {"photo_prep_background_removal_timeout_s": 900.0}
_WAVE3_OFF = {"small_text_bay_mouth": False, "sew_enclosed_white": False, **_REMBG_900}
#: The jobs that sew enclosed white off MFab (white ON by default since #1112): where
#: the keyline switches can act now that MFab-type art has them through the gate (#1122)
KEYLINE_OFF_MFAB = ("becker_hat_large", "becker_lc_large", "becker_hat_small", "becker_chest_small",
                    "becker_beanie", "gaulke_roofing_hat", "golf_hat", "tires_hat_3d",
                    "proseal_hat", "proseal_beanie")

FLAGS: dict[str, dict] = {
    "fill_turn_slant": {
        "kind": "FABRIC",
        "sets": {"fill_turn_slant": True}, "metric": "sub_half_mm",
        "about": "stitches under 0.5 mm", "pr": 1036,
        "note": "PR #1036 was RED on CI when rendered (tests/test_cut_every_jump.py "
                "test_off_is_byte_identical_to_base[earlier-0], an OFF md5 pin stale after main "
                "moved); rendered from its branch, diffed against that branch's own OFF."},
    "fill_underlay_cross": {
        "kind": "FABRIC",
        "sets": {"fill_underlay_cross": True}, "metric": "fill_underlay", "xray": True,
        "about": "underlay read under each fill (verdict: fills)", "pr": 1033},
    "cut_every_jump": {
        "sets": {"cut_every_jump": True}, "metric": "uncut_jumps",
        "about": "uncut jumps", "pr": 1035,
        "note": "PR #1035 was RED on CI when rendered (the same OFF md5 pin as #1036); rendered "
                "from its branch, diffed against that branch's own OFF."},
    "sew_enclosed_white": {
        "sets": {"sew_enclosed_white": True}, "metric": "white_stitches",
        "about": "stitches in white thread", "pr": 1031},
    "trim_bury_under_later": {
        "sets": {"trim_bury_under_later": True}, "metric": "under_later",
        "about": "trims whose hop later thread covers", "pr": 1030},
    "compact_solids_satin": {
        "sets": {"compact_solids_satin": True}, "metric": "rings",
        "about": "edge-cap rings (plan roles)", "pr": 1040},
    "small_solids_satin": {
        "sets": {"small_solids_satin": True}, "metric": "rings",
        "about": "edge-cap rings (plan roles)", "pr": 1023},
    "tie_in_off": {
        "kind": "FABRIC",
        "sets": {"tie_in_off": True}, "metric": "locks",
        "about": "run starts that lock", "pr": 1042},
    "satin_underlay_short_columns": {
        "kind": "FABRIC",
        "sets": {"satin_underlay_short_columns": True}, "metric": "short_bare", "xray": True,
        "about": "satin columns under 5 mm sewn bare", "pr": 1044},
    "lettering_columns_inside_stagger": {
        "sets": {"lettering_columns_inside_stagger": True}, "metric": "stagger",
        "about": "satin inner ends landing in a hole already used (pivot zones found)", "pr": 1058,
        "note": "Alone against OFF. PR #1058's headline pairs it with lettering_columns_corner_fold "
                "(OFF on main); its fold -> fold+stagger same-hole counts are Fremont 16 -> 13, "
                "MFab 27 -> 8 (pro 5 and 4)."},
    "enclosed_white_keyline": {
        "base": {"sew_enclosed_white": True},
        "sets": {"sew_enclosed_white": True, "enclosed_white_keyline": True},
        "metric": "white_under_1mm",
        "about": "white-thread stitches (of them under 1 mm)", "pr": 1059,
        "note": "Only acts with sew_enclosed_white ON, so OFF here is sew_enclosed_white ON with the "
                "keyline OFF and ON adds the keyline; the bare engine is not the comparison. "
                "PR #1059 was still open when rendered: run from a local merge of its branch "
                "with main (not committed anywhere)."},
    "text_cluster_wide_letters": {
        "sets": {"text_cluster_wide_letters": True}, "metric": "tagged",
        "about": "shapes the text tagger put in a line (the Column lane's input)", "pr": 1060,
        "note": "The pro has no tags to count; its row is the DST's own stitches and trims."},
    "small_text_set": {
        "sets": {"small_text_cap_mm": 4.0, "small_text_cap_max_width_scale": 1.05,
                 "small_text_cap_min_stroke_mm": 0.85, "small_text_cap_letter_gap_mm": 0.25,
                 "small_text_cap_bold_scale": 1.45, "lettering_columns_small_bold": True},
        "metric": "letter_height", "about": "median small-letter height, mm", "pr": 1029},
    # ---- wave 2 (2026-10-24)
    "small_text_cap_reach_edges": {
        "base": dict(_SMALL_TEXT_SET), "base_name": "small_text_set",
        "sets": {**_SMALL_TEXT_SET, "small_text_cap_reach_edges": True},
        "fixtures": ["proseal_hat", "proseal_beanie", "hotel_fremont_hat"],
        "metric": "small_lines", "about": "small lines: built, sewn height mm (census reader)",
        "pr": 1066,
        "note": "Acts only under #1029's re-set, so OFF is the re-set set (small_text_set) and ON "
                "adds this flag. PR #1066: ProSeal hat tagline 3.15 mm bean -> 4.35/4.45 satin "
                "(pro 4.55), beanie 2.8 -> 3.65/3.7 (pro 4.0); Fremont and Drone byte-identical."},
    "monoline_script_satin": {
        "sets": {"monoline_script_satin": True}, "fixtures": ["tires_hat_3d"],
        "metric": "sub_1mm", "about": "stitches under 1 mm (whole design)", "pr": 1063,
        "note": "The catch is TRIMS (the st / tr figures): PR #1063 whole design 8,001 st / 10 tr "
                "OFF -> 6,101 / 24 ON, pro 5,555 / 10. In the word: under-1 mm stitches 2,515 -> "
                "548 (pro 43), fill -> satin square to the stroke 0.00 -> 0.88 (pro 0.85). PR #1063 "
                "was open when rendered: run from a local merge with main (not committed)."},
    "border_from_outline": {
        "base": dict(_WHITE_SEWN), "base_name": "white_sewn",
        "sets": {**_WHITE_SEWN, "border_from_outline": True},
        "fixtures": ["becker_hat_small", "mfab_hat", "gaulke_roofing_hat"],
        "metric": "satin_loops", "about": "closed satin loops (borders)", "pr": 1065,
        "note": "Rendered with sew_enclosed_white and enclosed_white_keyline ON (Kent flipped both "
                "2026-10-24); it does nothing on MFab without white sewn. PR #1065 with white sewn: "
                "Becker small 8,512 / 21 -> 11,100 / 25 (faces fill, loops on top; pro 8,694 / 40), "
                "MFab hat 25,512 / 108 -> 20,219 / 89 (pro 17,568 / 46); Gaulke no outline, same "
                "bytes. Bridge NOT rendered: its pro files are only on G:, unmounted. PR #1065 was "
                "open when rendered: run from a local merge with main (not committed)."},
    "silhouette_underfill": {
        "base": dict(_WHITE_SEWN), "base_name": "white_sewn",
        "sets": {**_WHITE_SEWN, "silhouette_underfill": True},
        "fixtures": ["mfab_hat", "mfab_lc", "becker_beanie"],
        "metric": "travel_runs", "about": "travel runs in the plan (pro: n/a)", "pr": 1064,
        "note": "Rendered with sew_enclosed_white and enclosed_white_keyline ON (Kent flipped both "
                "2026-10-24), as PR #1064 measured it: MFab hat 18,916 / 81 -> 17,540 / 37 (pro "
                "17,568 / 19), MFab LC 16,542 / 72 -> 16,658 / 44 (pro 15,786 / 20), Becker beanie "
                "11,501 / 21 -> 13,726 / 20 (pro 11,411 / 11). White sews ON TOP of black on MFab "
                "(the reverse of #1059's order): that order is Kent's call."},
    # ---- MFab under-fill panels (2026-10-25, Kent: "the satin infill in between and around
    # letters ... use the M-Fab logo"): defaults | b-fixed | pro, then d2 | d2 + panels | pro
    "silhouette_underfill_alone": {
        "sets": {"silhouette_underfill": True},
        "fixtures": ["mfab_hat", "mfab_lc"],
        "metric": "sub_1mm", "about": "stitches under 1 mm", "pr": 1094,
        "note": "The under-fill ALONE, the white keyline unsewn (arm b). Before this PR the "
                "keyline cut split the outline and stage 5 dropped every body it held, uncounted "
                "(MFab LC: 26 merged shapes sewn by nobody); now every body sews as the host's "
                "fill at one angle. Cells digitized with rembg from the main checkout's venv and "
                "its timeout pinned at 900 s (the hat is photo_scene: route checked per arm)."},
    "silhouette_underfill_panels": {
        "base": {"silhouette_underfill": True, **_WHITE_SEWN}, "base_name": "d2",
        "sets": {"silhouette_underfill": True, **_WHITE_SEWN, "silhouette_underfill_panels": True},
        "fixtures": ["mfab_hat", "mfab_lc"],
        "metric": "white_under_1mm", "about": "white stitches (under 1 mm)", "pr": 1094,
        "also": {"name": "mitre", "label": "ON + MITRE",
                 "sets": {"silhouette_underfill": True, **_WHITE_SEWN,
                          "silhouette_underfill_panels": True, "outline_loop_mitre": True}},
        "note": "OFF is arm d2 (under-fill + white sewn + keyline). ON: AND WELDING and LLC ride "
                "a closed white panel -- not merged into the black, sewn after the white (black, "
                "white, black), white loops only round the M-FAB bodies. ON + MITRE adds "
                "`outline_loop_mitre` (#1093): the whole recipe. Same rembg pin as above."},
    # ---- wave 3 (2026-10-25)
    "border_from_outline_line_art_guard": {
        "base": {"border_from_outline": True},
        "sets": {"border_from_outline": True, "border_from_outline_line_art_guard": True},
        "fixtures": ["bridge_hat", "bridge_lc", "becker_hat_small"],
        "metric": "satin_loops", "about": "closed satin loops (borders)", "pr": 1078,
        "note": "Acts only with border_from_outline (ON since #1070), so OFF is today's engine. "
                "PR #1078: Bridge's bowl drawing stops reading as an outline -- hat and LC sew "
                "byte-identical to border_from_outline OFF; bowl window spike rays 22 -> 1 (hat), "
                "21 -> 1 (LC), garment pinholes at the anchor 2 -> 0 (hat). Becker, MFab, Fremont "
                "byte-identical. The pro's Bridge art carried no drawing: nothing of his to "
                "compare in the bowl. Bridge's pro files are on G:; set PRO_PARITY_ROOT when it "
                "is unmounted."},
    "silhouette_underfill_rim": {
        "base": {"silhouette_underfill": True, **_WHITE_SEWN}, "base_name": "d2",
        "sets": {"silhouette_underfill": True, **_WHITE_SEWN, "silhouette_underfill_rim": True},
        "fixtures": ["mfab_hat", "mfab_lc", "hotel_fremont_hat", "bridge_hat", "bridge_lc"],
        "metric": "satin_loops", "about": "closed satin loops (borders)", "pr": 1096,
        "note": "Acts only under silhouette_underfill, so OFF is arm d2 (under-fill + white sewn "
                "+ keyline) and ON adds the rim: the ring host's outer edge as one closed satin "
                "loop at 1.75 mm after its fill, in its colour. The pro: MFab one closed column "
                "1.94 (hat) / 1.86 (LC), Fremont the white ground's edge in two passes at "
                "1.39-1.73. Becker's letter host gets none (its ring is the satin)."},
    "fine_bars_satin": {
        "sets": {"fine_bars_satin": True},
        "fixtures": ["machine_hat", "hotel_fremont_hat", "precision_drone", "mfab_lc", "mfab_hat",
                     "bridge_hat", "bridge_lc"],
        "metric": "run_shapes", "about": "shapes sewn as a plain run ring (plan roles)", "pr": 1101,
        "note": "Free-standing thin ink bars under the area floor: To a T's speed rules, Fremont's "
                "separators, the drone's AND DRONE rule, MFab's LLC hairline. The pro satins each; "
                "ours rings them OFF. Gate-1 caveat (config.py): no width, pull or density moves, "
                "but whether a ~1 mm bar holds on a cap is the sew-out question small_solids_satin "
                "already carries -- Kent flipped that one from renders on 10-23 with the same caveat."},
    # ---- wave-3 flips (2026-10-26, Kent: bay mouth "Flip ON", white "A ... alone", "Flip,
    # but prove it first"). Both are ON by default from this PR, so OFF pins both False.
    "wave3_flips": {
        "base": dict(_WAVE3_OFF), "base_name": "wave3_off",
        "sets": {"small_text_bay_mouth": True, "sew_enclosed_white": True, **_REMBG_900},
        "fixtures": ["becker_hat_large", "mfab_hat", "hotel_fremont_hat"],
        "metric": "white_stitches", "about": "stitches in white thread", "pr": 1112,
        "note": "OFF pins both flips False (the engine before 2026-10-26); ON is the shipped "
                "defaults, the Studio's request as it now goes (white ticked, sewn white). "
                "fields_fill and the keyline stay OFF in both; rembg's timeout pinned at 900 s in "
                "both (route checked per cell)."},
    # ---- wave 3 sheet (2026-10-26): every flag built OFF since 10-24 not already above
    "lettering_columns_apex_cut": {
        "sets": {"lettering_columns_apex_cut": True},
        "fixtures": ["becker_hat_large", "mfab_hat", "proseal_hat"],
        "metric": "sub_1mm", "about": "stitches under 1 mm (whole design)", "pr": 1088,
        "note": "An acute tip -- the M's V, a W's apexes, a pointed A or N -- sews as ONE column "
                "cut off its strokes along the cross, as the pro's does (#1088; #1090 skips the slot "
                "rule for a letter with such a tip: MARINE's M at 95.7 mm). Corner fold is ON on main."},
    "text_cluster_part_touching": {
        "sets": {"text_cluster_part_touching": True},
        "fixtures": ["mfab_hat", "mfab_lc"],
        "metric": "tagged", "about": "shapes the text tagger put in a line (the Column lane's input)",
        "pr": 1080,
        "also": {"name": "bean_ink", "label": "ON + BEAN INK", "fixtures": ["mfab_lc"],
                 "sets": {"text_cluster_part_touching": True, "bean_ink_outlined_letters": True}},
        "note": "Two letters the tagger misses on MFab's AND WELDING: the hat's I and N touching at "
                "a 0.08 mm neck (traced as one region), and the LC's AND N overshooting the cap "
                "height. Alone, the LC's newly tagged N goes bean on its white keyline and sews "
                "hollow; ON + BEAN INK adds `bean_ink_outlined_letters` (#1128), which sews it "
                "satin. The hat's plan does not move under bean ink (#1128), so its third cell is "
                "left out."},
    "outline_loop_mitre": {
        "sets": {"outline_loop_mitre": True},
        "fixtures": ["becker_hat_large", "becker_hat_small", "bridge_hat", "bridge_lc"],
        "metric": "satin_loops", "about": "closed satin loops (borders)", "pr": 1093,
        "note": "The border_from_outline loops (ON on main) keep their far rail at the satin pitch "
                "through a letter's convex corners: the pro's corner is a round pivot, not a mitre "
                "(far ends 1.00 W out; ours OFF 1.1 mm apart at the corner, his 0.4). Bridge's art "
                "outline is guarded out (#1078), so Bridge should read no change."},
    "keyline_fold_slivers": {
        # wave 5: no base. White sews by default since #1112. On MFab-type art the gate sews
        # this switch ON by itself since #1122 (with skip and absorb), so an MFab cell is OFF
        # byte for byte: the row reads the jobs off MFab, where the trio moved them
        "sets": {"keyline_fold_slivers": True},
        "fixtures": list(KEYLINE_OFF_MFAB),
        "metric": "white_under_1mm", "about": "white stitches (under 1 mm)", "pr": 1102,
        "note": "Read only where white sews -- since #1112 that is every job with an enclosed "
                "white field. ON folds a white field's hairline slivers back into it. ON on "
                "MFab-type art through the gate since #1122 (Kent 2026-10-26, \"MFab extras into "
                "the gate\"; docs/gate-mfab-extras-2026-10-26.md), so this row is the jobs off "
                "MFab. Older bases' numbers (#1102's 41 -> 27) are not quoted: read the cells."},
    "skip_covered_shapes": {
        "sets": {"skip_covered_shapes": True},
        "fixtures": list(KEYLINE_OFF_MFAB),
        "metric": "white_under_1mm", "about": "white stitches (under 1 mm)", "pr": 1102,
        "note": "A shape whose whole thread lies on thread of its own colour block is not sewn. "
                "Same colour, so nothing that shows changes; it removes a second layer and its "
                "cuts. ON on MFab-type art through the gate since #1122, so this row is the jobs "
                "off MFab (white sewn by default since #1112)."},
    "keyline_trio": {
        # the detection pass: one combined arm per non-MFab white job; a flag gets its own
        # cell on a job only where this arm's DST differs from OFF
        "sets": {"keyline_fold_slivers": True, "skip_covered_shapes": True,
                 "extra": {"absorb_fragments": True}},
        "fixtures": list(KEYLINE_OFF_MFAB),
        "metric": "white_under_1mm", "about": "white stitches (under 1 mm)", "pr": 1102,
        "note": "Not a flag: the detection pass. keyline_fold_slivers, skip_covered_shapes and "
                "absorb_fragments all ON at once on every non-MFab job that sews white (since "
                "#1112; MFab has all three through the gate, #1122). Where its DST equals OFF "
                "none of the three acts on that job; where it differs, each flag gets its own cell."},
    "lettering_columns_italic_lean": {
        "sets": {"lettering_columns_italic_lean": True},
        "fixtures": ["proseal_hat", "proseal_beanie"],
        "metric": "sub_1mm", "about": "stitches under 1 mm (whole design)", "pr": 1079,
        "note": "Under lettering_columns_text_lean (ON on main): the bars of an italic word cross "
                "along its stems, 71-78 deg off the line of text as the pro's do on PROSEAL, where "
                "the lane crosses them square to themselves."},
    "fill_section_travel": {
        "sets": {"extra": {"fill_section_travel": True}},
        # wave 3's three, plus (wave 5) the rest of PR #1091's five hats; Fremont first, the
        # one it moved
        "fixtures": ["hotel_fremont_hat", "bridge_hat", "bridge_lc", "becker_hat_large", "mfab_hat",
                     "precision_drone", "gaulke_roofing_hat"],
        "metric": "travel_runs", "about": "travel runs in the plan (pro: n/a)", "pr": 1091,
        "note": "A cfg.extra key (the Studio's request cannot set it; the cell lays it on). Fill "
                "sections join by a route hidden inside the field instead of a cut. PR #1091 read "
                "Fremont's in-piece cuts 51 -> 41 on its own base and its other hats unmoved; on "
                "this sheet it changes six of these seven jobs (Gaulke byte-identical), but the DST's "
                "trims by one at most (Becker large +1, MFab hat and the drone -1)."},
    "absorb_fragments": {
        # wave 5: no base, as keyline_fold_slivers; the gate's on MFab since #1122
        "sets": {"extra": {"absorb_fragments": True}},
        "fixtures": list(KEYLINE_OFF_MFAB),
        "metric": "white_under_1mm", "about": "white stitches (under 1 mm)", "pr": 1100,
        "note": "A cfg.extra key, read only where white sews (every enclosed white field since "
                "#1112): a white keyline fragment narrower than the pro's narrowest satin, within "
                "one thread of its field, is sewn as part of the field after stage 5. ON on "
                "MFab-type art through the gate since #1122, with its panel fix (the join keeps "
                "the riders' panel), so this row is the jobs off MFab. Older bases' numbers "
                "(#1100's 77 -> 60) are not quoted: read the cells."},
    "small_text_bay_mouth": {
        # a field since #1112 and ON by default (Kent 2026-10-26), so OFF pins it False
        "base": dict(_WAVE3_OFF), "base_name": "wave3_off",
        "sets": {"small_text_bay_mouth": True, "sew_enclosed_white": False, **_REMBG_900},
        "fixtures": ["hotel_fremont_hat", "proseal_hat"],
        "metric": "small_lines", "about": "small lines: built, sewn height mm (census reader)",
        "pr": 1085,
        "note": "On the re-set: the widening shuts a bay where a terminal curls back to its own "
                "letter, so Fremont's EST 1895 sews as BST 1893. ON cuts the terminal back along "
                "its stroke until the mouth holds the pro's 0.51 mm (n 18). No letter's height "
                "moves, so read the picture, not the column; ProSeal is the byte-identical control. "
                "Flipped ON by #1112, so OFF here pins it (and white) False."},
    # ---- script words (2026-10-26, Kent: "Measure, then build OFF")
    "script_strokes": {
        "base": {"photo_prep_background_removal_timeout_s": 900}, "base_name": "rembg900",
        "sets": {"photo_prep_background_removal_timeout_s": 900, "script_strokes": True},
        "fixtures": ["bridge_hat", "bridge_lc", "tires_hat_3d", "machine_hat"],
        "metric": "script_square", "about": "word's crosses square to the stroke (script_census)",
        "pr": 1119,
        "note": "A script word sewn one satin column per pen stroke, crosses square to the stroke, "
                "the path read on the art's ink. Both arms pin the rembg timeout at 900 s (Tires is "
                "photo_scene). The pro RE-SET Bridge in a taller font of his own (not reproducible "
                "from a trace) and sews it thinner: his crosses 1.56 mm at hat against the drawn "
                "1.76 + our 0.4 mm pull a side -- a smaller script pull is gate 1, not built."},
    # ---- wave 5 (2026-10-27)
    "bean_ink_outlined_letters": {
        "sets": {"bean_ink_outlined_letters": True},
        "fixtures": ["mfab_lc", "mfab_hat"],
        "metric": "run_shapes", "about": "shapes sewn as a plain run (bean letters)", "pr": 1128,
        "note": "MFab's small line is black letters on a black body, each ringed by a white "
                "keyline, so the ink reader takes the keyline for the letter's ink (0.4-1.7% of "
                "the spine inside the letter). OFF, the LC's AND A goes bean and sews as a white "
                "letter with a thin black line round it. ON leaves out a read whose spines lie "
                "less than half inside the letter: the A sews black satin (crosses 44 -> 116, "
                "pro 114). The hat is the control: its reads are the letters' own ink and fail "
                "the shape gate, so it should not move."},
    # ---- defect 19 (2026-10-29): the design-edge cap on today's main
    "edge_cap_satin": {
        "sets": {"edge_cap": "satin"},
        "fixtures": ["hotel_fremont_hat", "becker_hat_small", "gaulke_roofing_hat",
                     "precision_drone"],
        "metric": "rings", "about": "edge-cap runs", "pr": None,
        "note": "OFF is the shipped engine: edge_cap 'bean', which bean_only_lines (ON since "
                "2026-10-27) turns into no cap. ON is the satin style, the one cap style still "
                "live. docs/edge-cap-remeasure-2026-10-29.md has the silhouette and size sweep."},
    "edge_cap_bean_legacy": {
        "sets": {"edge_cap": "bean", "bean_only_lines": False},
        "fixtures": ["hotel_fremont_hat", "becker_hat_small", "gaulke_roofing_hat",
                     "precision_drone"],
        "metric": "rings", "about": "edge-cap runs", "pr": None,
        "note": "The bean cap as it sewed 2026-09-11 to 10-27, with bean_only_lines OFF so the "
                "bean style is not turned off. bean_only_lines OFF also moves bean letters and "
                "the run tier, so ON differs from OFF in more than the cap: read the rings."},
}

#: The wave-3 sheet (2026-10-26): the flags its run and report carry. The bay mouth left
#: it when #1112 flipped it ON; its row stays, for the OFF | ON | pro of that PR.
# `outline_loop_mitre` and `fine_bars_satin` left it when Kent flipped them ON,
# 2026-10-26 ("Outline corners pivot", "Fine bars as satin"); their rows stay.
# `text_cluster_part_touching` and `lettering_columns_italic_lean` left it when Kent
# flipped them ON from the wave-5 sheet, 2026-10-27; their rows stay.
#: (`silhouette_underfill_rim`, `keyline_fold_slivers`, `skip_covered_shapes` and
#: `absorb_fragments` left it 2026-10-27: ON with the white-keyline recipe on every
#: job, Kent "Every job (Recommended)"; their rows are kept)
WAVE3 = ["lettering_columns_apex_cut", "monoline_script_satin", "fill_section_travel"]

#: The wave-5 sheet (2026-10-27): every layout flag still waiting on Kent, on main
#: after #1112 (white and the bay mouth ON), #1121 (fine bars and the outline pivot
#: ON), #1122 and #1134 (the keyline switches and the loop chain ride MFab's gate,
#: #1115) and #1127 (the re-set grows away). `ask`: Kent rules it
#: from this sheet. A row shown and not
#: asked says why in `label`, and is drawn from cells already rendered (their
#: engine on the row): it gets no new digitize.
W5_DATE = "2026-10-27"
W5: dict[str, dict] = {
    "lettering_columns_italic_lean": {"ask": True},
    # the detection pass on fa3150de (Tires again on 4a087210, after #1136 moved its OFF): the
    # trio's DST is OFF's byte for byte on all ten white
    # jobs off MFab, so keyline_fold_slivers, skip_covered_shapes and absorb_fragments get no
    # row of their own (nothing a render could judge) and are not asked
    "keyline_trio": {"ask": False, "label": "detection pass, not a flag: ON is OFF byte for byte "
                                            "on all ten white jobs off MFab, so keyline_fold_slivers, "
                                            "skip_covered_shapes and absorb_fragments act nowhere "
                                            "off MFab; on MFab they are ON through the gate (#1122)"},
    "fill_section_travel": {"ask": True},
    "bean_ink_outlined_letters": {"ask": True},
    "text_cluster_part_touching": {"ask": True},
    "outline_loop_mitre": {"ask": False, "label": "Kent ruled ON 2026-10-26 (\"Outline corners "
                           "pivot\"); flipped ON by #1121. Wave 3's cells only"},
    "fine_bars_satin": {"ask": False, "label": "Kent ruled ON 2026-10-26 (\"Fine bars as satin\"); "
                        "flipped ON by #1121. Wave 3's cells only"},
    "lettering_columns_apex_cut": {"ask": False, "label": "existing cells only: claude/apex-walk-w5 "
                                   "renders this letter set, and Kent rules from its sheet"},
    "monoline_script_satin": {"ask": False, "label": "HELD by Kent 2026-10-24 (#1070); with "
                              "script_strokes ON (#1136) Tires' script word never reaches it"},
    "silhouette_underfill_rim": {"ask": False, "label": "ON on MFab via #1115; elsewhere waits on "
                                 "silhouette_underfill (held 10-24), and alone it fails gate 3 "
                                 "on MFab"},
}


def flag_kind(flag: str) -> str:
    """LAYOUT (judged from renders, Kent 2026-10-22) or FABRIC (gate 1)."""
    return FLAGS[flag].get("kind", "LAYOUT")


# ------------------------------------------------------------------ engine
def engine_root() -> Path:
    """The checkout whose `digitizer_core` is imported: `--engine`'s, else ours."""
    return Path(os.environ.get("FLIP_SHEET_ENGINE") or DIGITIZER.parent)


def use_engine(root: Path | None) -> None:
    if root is None:
        return
    d = Path(root).resolve() / "digitizer"
    if not (d / "digitizer_core").is_dir():
        raise SystemExit(f"--engine {root}: no digitizer/digitizer_core there")
    os.environ["FLIP_SHEET_ENGINE"] = str(d.parent)
    sys.path.insert(0, str(d))
    for name in list(sys.modules):
        if name.split(".")[0] in ("digitizer_core", "digitizer_service", "tools"):
            del sys.modules[name]


def engine_sha(root: Path | None = None) -> str:
    root = Path(root or engine_root())
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root,
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


# ---------------------------------------------------------------- fixtures
def fixture_files(slug: str) -> dict:
    """pro DST (preferred over PES: the PES reader reports a TRIM at every
    jump), pro PES if any (thread colours), art, garment, width."""
    from tools import border_census as bc
    from tools import pro_pair as pp
    from tools.pro_intake import registered_pairs
    row = next(r for r in [*bc.PAIRS, *EXTRA_PAIRS, *registered_pairs()] if r[0] == slug)
    pro, art = bc.find_pair(*row[:3])
    fallback = art is None and slug in ART_FALLBACK and ART_FALLBACK[slug].exists()
    if fallback:
        art = ART_FALLBACK[slug]
    if pro is None or art is None:
        raise SystemExit(f"{slug}: missing {'pro' if pro is None else 'art'} file")
    pes = pro if pro.suffix.lower() == ".pes" else None
    dst = bc.find(row[1][:-4] + ".DST") if row[1].upper().endswith(".PES") else pro
    width = dict(FIXTURES).get(slug)
    if width is None:
        width = pp.pro_counts(dst or pro)["width_mm"]
    return {"slug": slug, "garment": row[3], "art": Path(art), "pro_dst": Path(dst or pro),
            "pro_pes": Path(pes) if pes else None, "width_mm": float(width),
            "art_fallback": fallback}


# --------------------------------------------------------------------- run
def is_off(arm: str) -> bool:
    return arm == "off" or arm.endswith("__off")


def off_arm(flag: str) -> str:
    """The arm a flag is diffed against: bare `off`, or `<base_name>__off` when
    it has a `base` (`base_name` defaults to the flag: one OFF arm per flag)."""
    spec = FLAGS[flag]
    return f"{spec.get('base_name', flag)}__off" if spec.get("base") else "off"


def also_arm(flag: str, slug: str | None = None) -> str | None:
    """The row's optional THIRD cell (`also`: {name, label, sets[, fixtures]}), sewn
    beside ON and cropped on ON's window -- e.g. d2 | d2 + panels | d2 + panels +
    mitre | pro. With `slug`, None where the third cell's own `fixtures` leave it out."""
    also = FLAGS[flag].get("also")
    if not also or (slug is not None and "fixtures" in also and slug not in also["fixtures"]):
        return None
    return f"{flag}__{also['name']}"


def arm_sets(arm: str) -> dict:
    if arm == "off":
        return {}
    if arm.endswith("__off"):
        name = arm[: -len("__off")]
        owner = next(f for f, s in FLAGS.items() if s.get("base") and s.get("base_name", f) == name)
        return dict(FLAGS[owner]["base"])
    if "__" in arm:
        flag, _name = arm.split("__", 1)
        return dict(FLAGS[flag]["also"]["sets"])
    return dict(FLAGS[arm]["sets"])


def flag_fixtures(flag: str, asked: list[str] | None) -> list[str]:
    """The jobs a flag is rendered on: its own `fixtures` (narrowed to `asked`
    when given), else `asked`, else FIXTURES."""
    own = FLAGS[flag].get("fixtures")
    if own:
        return [s for s in own if not asked or s in asked]
    return list(asked) if asked else [s for s, _ in FIXTURES]


def cell_dir(cache: Path, slug: str, arm: str, sha: str) -> Path:
    return cache / slug / (f"{arm}__{sha}" if is_off(arm) else arm)


@contextlib.contextmanager
def config_extra(extra: dict | None):
    """`cfg.extra` keys laid onto the config the service's parser builds, for
    one digitize: the parser refuses `extra`, so a flag that lives there
    (`fill_section_travel`) cannot ride the Studio's request. None: nothing."""
    if not extra:
        yield
        return
    import importlib
    svc = importlib.import_module("digitizer_service.app")   # the package's `app` is the FastAPI object
    parse = svc._parse_config

    def with_extra(raw):
        kw = parse(raw)
        kw["extra"] = {**(kw.get("extra") or {}), **extra}
        return kw
    svc._parse_config = with_extra
    try:
        yield
    finally:
        svc._parse_config = parse


def digitize_cell(slug: str, arm: str, cache: Path, engine: str | None) -> dict:
    """One (fixture, arm): ours.dst + design.json + runs.json + stats.json."""
    use_engine(Path(engine) if engine else None)
    from tools import pro_pair as pp
    from digitizer_core.export import write_dst
    sha = engine_sha()
    out = cell_dir(cache, slug, arm, sha)
    if (out / "stats.json").exists():
        return json.loads((out / "stats.json").read_text(encoding="utf-8"))
    fx = fixture_files(slug)
    sets = arm_sets(arm)
    # a lane has no rembg venv of its own: point stage 1 at the primary checkout's, or a
    # photo_scene job (MFab) silently takes the no-background-removal route (2026-10-26)
    from tools.enclosed_pro_census import _rembg
    rembg = _rembg()
    request_sets = {k: v for k, v in sets.items() if k != "extra"}
    cpu0 = time.process_time()
    with config_extra(sets.get("extra")):
        d = pp.digitize(fx["art"], fx["width_mm"], fx["garment"], request_sets)
    cpu = time.process_time() - cpu0
    out.mkdir(parents=True, exist_ok=True)
    write_dst(d.plan, out / "ours.dst")
    travel = travel_instruments(d.plan, out / "ours.dst")
    (out / "design.json").write_text(json.dumps(d.design), encoding="utf-8")
    runs = []
    for bi, (blk, run) in enumerate(d.plan.iter_runs()):
        pts = run.points or []
        runs.append({"shape": str(run.shape_id), "kind": str(run.kind),
                     "role": str(getattr(run, "role", "") or ""), "n": len(pts),
                     "jump": bool(getattr(run, "jump", False)), "trim": bool(getattr(run, "trim", False)),
                     "rgb": list(blk.rgb)})
    (out / "runs.json").write_text(json.dumps(runs), encoding="utf-8")
    tagged = sum(1 for r in d.result.regions
                 if (getattr(r, "meta", None) or {}).get("text_cluster_id") is not None)
    stats = {"slug": slug, "arm": arm, "sets": sets, "engine": sha, "tagged": tagged,
             "engine_root": str(engine_root()), "width_mm": fx["width_mm"],
             "garment": fx["garment"], "secs": round(d.secs, 1), "cpu_s": round(cpu, 1),
             "plan_stitches": d.plan.stats.stitch_count, "plan_trims": d.plan.stats.trims,
             "rembg": rembg,
             "background_removed": any((w.get("code") == "PHOTO_BACKGROUND_REMOVED")
                                       for w in (getattr(d.plan, "warnings", None) or [])),
             "md5": hashlib.md5((out / "ours.dst").read_bytes()).hexdigest(), **travel}
    (out / "stats.json").write_text(json.dumps(stats, indent=1), encoding="utf-8")
    return stats


#: hairline_travel's half-thread clearance and the two wider bands #1112 read beside it:
#: a rise only at 0.20 is travel overlapping a laid stitch by under half a thread
BARE_BANDS_MM = (0.20, 0.25, 0.30)
OFFBODY_PPM = 10.0          # travel off DST bodies: raster of the cell's own DST
OFFBODY_TOL_PX = 2          # +0.2 mm round the opened bodies


def bare_by_band(plan, bands=BARE_BANDS_MM) -> dict[str, float]:
    """`tools.hairline_travel`'s bare thread (needle-down travel legs, flights left
    out) at each clearance in `bands`: mm of leg further than that from every laid
    stitch's centreline. The 0.20 band is the instrument's own `scan` number."""
    import numpy as np
    import shapely
    from shapely.geometry import LineString
    from tools import hairline_travel as ht
    zone = ht._thread_zone(plan)
    tot = {d: 0.0 for d in bands}
    for lg in ht.legs(plan):
        if lg["flight"] or zone is None or len(lg["pts"]) < 2:
            continue
        path = LineString(lg["pts"])
        if path.length <= 0:
            continue
        n = max(2, int(path.length / ht.STEP_MM))
        pts = shapely.line_interpolate_point(path, (np.arange(n) + 0.5) / n, normalized=True)
        for d in bands:
            hit = zone.query(pts, predicate="dwithin", distance=d)
            cov = np.zeros(len(pts), bool)
            cov[hit[0]] = True
            tot[d] += float((~cov).sum()) * path.length / n
    return {f"{d:.2f}": round(v, 2) for d, v in tot.items()}


def _dst_bodies(path: Path):
    """The DST's sewn bodies as a raster: each block's needle-down lines at a
    thread's width, opened by `sequence_pro.OPEN_MM` (a lone walk line is not a
    body), dilated `OFFBODY_TOL_PX`. -> (mask, mm -> px, (w, h), first stitch mm)."""
    import cv2
    import numpy as np
    from tools import sequence_pro as sp
    f = sp.read(path)
    x0, y0, x1, y1 = f["extents"]
    ox, oy = x0 - 2, y0 - 2
    w, h = int((x1 - x0 + 4) * OFFBODY_PPM) + 2, int((y1 - y0 + 4) * OFFBODY_PPM) + 2
    lw = max(1, int(round(sp.THREAD_MM * OFFBODY_PPM)))

    def px(p):
        return int(round((p[0] - ox) * OFFBODY_PPM)), int(round((p[1] - oy) * OFFBODY_PPM))
    bodies = np.zeros((h, w), np.uint8)
    k = int(round(sp.OPEN_MM * OFFBODY_PPM))
    for block in f["blocks"]:
        mv = sp.moves(block)
        im = np.zeros((h, w), np.uint8)
        for a, b in zip(mv, mv[1:]):
            if not b["up"]:
                cv2.line(im, px(a["p"]), px(b["p"]), 1, lw)
        bodies |= cv2.morphologyEx(im, cv2.MORPH_OPEN, np.ones((k, k), np.uint8))
    t = 2 * OFFBODY_TOL_PX + 1
    near = cv2.dilate(bodies, np.ones((t, t), np.uint8))
    first = next((x, y) for b in f["blocks"] for x, y, c in b if c == 0)   # pystitch.STITCH
    return near, px, (w, h), first


def travel_offbody(plan, dst: Path) -> float:
    """mm of TRAVEL thread -- each run and its needle-down legs in and out -- off
    every body of the cell's own DST: the bare-fabric question read against the
    machine file, not the plan (#1112's second reading)."""
    from digitizer_core import stitches
    near, px, (w, h), first_dst = _dst_bodies(dst)
    fp = next(pt for cmd, pt in stitches.iter_machine_commands(plan) if cmd == stitches.CMD_STITCH)
    dx, dy = first_dst[0] - fp[0], first_dst[1] - fp[1]
    runs = [r for _b, r in plan.iter_runs() if r.points]
    tot = 0.0
    for i, r in enumerate(runs):
        if r.kind != stitches.TRAVEL:
            continue
        pts = list(r.points)
        if i and not r.jump:
            pts = [runs[i - 1].points[-1]] + pts
        if i + 1 < len(runs) and not runs[i + 1].jump:
            pts = pts + [runs[i + 1].points[0]]
        for a, b in zip(pts, pts[1:]):
            L = math.dist(a, b)
            n = max(1, int(math.ceil(L / 0.25)))
            for k in range(n):
                t = (k + 0.5) / n
                qx, qy = px((a[0] + (b[0] - a[0]) * t + dx, a[1] + (b[1] - a[1]) * t + dy))
                if 0 <= qx < w and 0 <= qy < h and not near[qy, qx]:
                    tot += L / n
    return round(tot, 2)


def travel_instruments(plan, dst: Path) -> dict:
    """The travel numbers a row carries beside its counts. `bare_mm` (by clearance
    band) is gate 3's instrument; `exposed_mm` (`tools.travel_cover`, which also
    counts travel lying on EARLIER thread) and `offbody_mm` are information."""
    from tools.travel_cover import travel_exposure
    out = {"exposed_mm": round(travel_exposure(plan)["exposed_mm"], 1), "bare_mm": bare_by_band(plan)}
    try:
        out["offbody_mm"] = travel_offbody(plan, dst)
    except Exception as e:  # noqa: BLE001 -- an unreadable file is a cell note, not a lost cell
        out["offbody_mm"] = f"reader failed: {type(e).__name__}"
    return out


def _job(args):
    slug, arm, cache, engine = args
    try:
        s = digitize_cell(slug, arm, Path(cache), engine)
        return f"{slug}/{arm}: {s['plan_stitches']} st, {s['plan_trims']} trims, {s['secs']} s [{s['engine']}]"
    except Exception as e:  # noqa: BLE001 -- one cell failing must not sink the pass
        return f"{slug}/{arm}: FAILED {type(e).__name__}: {e}"


def run_cmd(a) -> int:
    flags = a.flags or list(FLAGS)
    bad = [f for f in flags if f not in FLAGS]
    if bad:
        raise SystemExit(f"unknown flags: {bad}; known: {list(FLAGS)}")
    pairs = [(s, arm) for f in flags for s in flag_fixtures(f, a.fixtures)
             for arm in (off_arm(f), f, also_arm(f, s)) if arm]
    if getattr(a, "off_only", False):     # OFF first: `adopt` then keeps ON cells whose OFF held
        pairs = [(s, arm) for s, arm in pairs if is_off(arm)]
    jobs = [(s, arm, str(a.cache), a.engine) for s, arm in dict.fromkeys(pairs)]
    if a.jobs <= 1:
        for j in jobs:
            print(_job(j), flush=True)
    else:
        with ProcessPoolExecutor(max_workers=a.jobs) as ex:
            for line in ex.map(_job, jobs):
                print(line, flush=True)
    return 0


def _md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def adopt(src: Path, dst: Path, flag: str, slug: str, base_sha: str | None) -> str:
    """Copy an ON cell (and the OFF it was diffed against) from an older cache.

    `base_sha` None: a row shown and not asked -- copied as it is, its engine on
    the row. Otherwise only when the cell's `sets` are the row's today AND the OFF
    it was diffed against is byte-identical to this cache's OFF at `base_sha`:
    the base moved nowhere this job sews, so the old ON stands for the new one.
    -> what happened, one line."""
    import shutil
    on = src / slug / flag
    if not (on / "stats.json").exists():
        return f"{slug}/{flag}: no cell in {src}"
    st = json.loads((on / "stats.json").read_text(encoding="utf-8"))
    off_old = cell_dir(src, slug, off_arm(flag), st["engine"])
    if not (off_old / "ours.dst").exists():
        return f"{slug}/{flag}: its OFF ({off_old.name}) is not in {src}"
    if base_sha is not None:
        if st.get("sets") != arm_sets(flag):
            return f"{slug}/{flag}: not adopted, its sets {st.get('sets')} are not the row's"
        off_new = cell_dir(dst, slug, off_arm(flag), base_sha)
        if not (off_new / "ours.dst").exists():
            return f"{slug}/{flag}: not adopted, no OFF at {base_sha} to compare"
        if _md5(off_new / "ours.dst") != _md5(off_old / "ours.dst"):
            return f"{slug}/{flag}: not adopted, OFF moved {st['engine']} -> {base_sha}"
    for d in (on, off_old):
        target = dst / slug / d.name
        if not target.exists():
            shutil.copytree(d, target)
    return f"{slug}/{flag}: adopted from {st['engine']}"


def adopt_cmd(a) -> int:
    for f in a.flags:
        for s in flag_fixtures(f, a.fixtures):
            print(adopt(Path(a.source), Path(a.cache), f, s, a.base), flush=True)
    return 0


# ----------------------------------------------------------------- readers
def read_stream(path: Path) -> list[tuple[float, float, int]]:
    """(x mm, y mm, command) per record, as pystitch reads the file."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    m = pystitch.COMMAND_MASK
    return [(x / 10.0, y / 10.0, c & m) for x, y, c in pat.stitches]


def counts(stream) -> dict:
    import pystitch
    cmds = [c for *_, c in stream]
    return {"stitches": sum(1 for c in cmds if c == pystitch.STITCH),
            "trims": sum(1 for c in cmds if c == pystitch.TRIM),
            "colours": sum(1 for c in cmds if c == pystitch.COLOR_CHANGE)}


def needle_points(stream) -> list[tuple[float, float]]:
    import pystitch
    return [(x, y) for x, y, c in stream if c == pystitch.STITCH]


def sub_half_mm(stream, _fx, _cell) -> int:
    """Needle-to-needle stitches under 0.5 mm (a fill's straight row turns)."""
    import pystitch
    n, prev = 0, None
    for x, y, c in stream:
        if c == pystitch.STITCH:
            if prev is not None and math.dist(prev, (x, y)) < 0.5:
                n += 1
            prev = (x, y)
        else:
            prev = None if c in (pystitch.TRIM, pystitch.COLOR_CHANGE) else prev
    return n


def sub_1mm(stream, _fx, _cell) -> int:
    """Needle-to-needle stitches under 1 mm (a fill's turns, a column's crowding)."""
    import pystitch
    n, prev = 0, None
    for x, y, c in stream:
        if c == pystitch.STITCH:
            if prev is not None and math.dist(prev, (x, y)) < 1.0:
                n += 1
            prev = (x, y)
        else:
            prev = None if c in (pystitch.TRIM, pystitch.COLOR_CHANGE) else prev
    return n


def satin_loops(_stream, _fx, cell) -> int:
    """Satin columns whose spine closes on itself -- a border laid along an
    outline (`border_census.closed_satin_loops`, the census's own reader)."""
    from tools.border_census import closed_satin_loops
    from tools.study_pro import load_runs
    return len(closed_satin_loops(load_runs(Path(cell["dst"]))[0]))


def travel_runs(_stream, _fx, cell) -> str:
    runs = cell.get("runs")
    if runs is None:
        return "n/a (DST has no roles)"
    return str(sum(1 for r in runs if r["kind"] == "travel"))


def small_lines(_stream, fx, cell) -> str:
    """Each small line the census lists for this job (`small_text_floor_census.
    ELEMENTS`, not its references): construction and sewn height, read by the
    census's own reader. The art height is the listed box's; the pro is read
    through `register` against our OFF file."""
    from tools import small_text_floor_census as st
    from tools.study_pro import load_runs
    els = [e for e in st.ELEMENTS if e[0] == fx["slug"] and "(ref)" not in e[1]]
    if not els:
        return "no small lines listed"
    runs = load_runs(Path(cell["dst"]))[0]
    reg = st.register(fx["pro_dst"], fx["ours_ref"]) if cell.get("stats") is None else None
    out = []
    for _slug, label, box, *_ in els:
        art_h = box[3] - box[1]
        m_y, m_x, cy = max(2.5, 1.5 * art_h), 2.0 + 0.5 * art_h, 0.5 * (box[1] + box[3])
        if reg is None:
            e = st.read_element(runs, (box[0] - m_x, box[1] - m_y, box[2] + m_x, box[3] + m_y), art_h, cy)
        else:
            e = st.read_element(runs, st._map_box(box, reg, m_x * reg.scale, m_y * reg.scale),
                                art_h * reg.scale, reg.scale * cy + reg.dy)
        out.append(f"{label} {e['verdict'].lower()} {e.get('h_mm', '-')}")
    return "; ".join(out)


def fill_underlay(_stream, _fx, cell) -> str:
    """What `tools.pro_fill_underlay` reads under each fill: verdict counts
    (CROSS / DIAG / PARALLEL / MIXEDANG / RUNONLY / BARE)."""
    from collections import Counter
    from tools import pro_fill_underlay as pfu
    c = Counter(v for v, _ in pfu.classify_file(cell["dst"]))
    return " ".join(f"{k} {n}" for k, n in sorted(c.items())) or "no fills read"


def uncut_jumps(stream, _fx, _cell) -> int:
    """Needle-up hops (one or more JUMP records) between two penetrations
    with no TRIM or colour change around them."""
    import pystitch
    n, in_jump, cut = 0, False, False
    for _x, _y, c in stream:
        if c == pystitch.JUMP:
            in_jump = True
        elif c in (pystitch.TRIM, pystitch.COLOR_CHANGE):
            cut = True
        elif c == pystitch.STITCH:
            if in_jump and not cut:
                n += 1
            in_jump, cut = False, False
    return n


def white_stitches(_stream, fx, cell) -> str:
    """Stitches sewn in a near-white thread, from the file's own colours;
    a DST carries none."""
    design = cell.get("design")
    if design is None:
        return "n/a (no thread colours)"
    colors = design.get("colors") or []
    n, ci = 0, 0
    for s in design.get("stitches") or []:
        t = s.get("type")
        if t == "color":
            ci += 1
        elif t == "stitch" and ci < len(colors):
            c = colors[ci]
            if min(c.get("r", 0), c.get("g", 0), c.get("b", 0)) >= 230:
                n += 1
    return str(n)


def under_later(_stream, _fx, cell) -> int:
    from tools import trim_classes as tc
    return sum(1 for r in tc.classify(cell["dst"]) if r.get("cls") == "under_later")


def rings(_stream, _fx, cell) -> str:
    runs = cell.get("runs")
    if runs is None:
        return "n/a (DST has no roles)"
    return str(sum(1 for r in runs if r["role"] == "edge_cap"))


def run_shapes(_stream, _fx, cell) -> str:
    """Shapes sewn as a plain run -- the rescue's ring, not an edge cap."""
    runs = cell.get("runs")
    if runs is None:
        return "n/a (DST has no roles)"
    return str(len({r["shape"] for r in runs if r["kind"] == "run" and not r["role"]}))


def locks(stream, _fx, _cell) -> int:
    """Run starts (after a trim, colour change or jump) whose first three
    stitches are all under LOCK_LEG_MM with a reversal among them."""
    import pystitch
    n, head, fresh = 0, [], True
    for x, y, c in stream:
        if c == pystitch.STITCH:
            head.append((x, y))
            if fresh and len(head) == 4:
                legs = [math.dist(a, b) for a, b in zip(head, head[1:])]
                vecs = [(b[0] - a[0], b[1] - a[1]) for a, b in zip(head, head[1:])]
                rev = any(_dot(u, v) < 0 for u, v in zip(vecs, vecs[1:]))
                if all(l <= LOCK_LEG_MM for l in legs) and rev:
                    n += 1
                fresh = False
        elif c in (pystitch.TRIM, pystitch.COLOR_CHANGE, pystitch.JUMP):
            head, fresh = [], True
    return n


def _dot(u, v) -> float:
    return u[0] * v[0] + u[1] * v[1]


def _engine_module(name: str, cell: dict):
    """`tools.<name>` from this checkout, else from the engine the cell was
    run on (a branch reader the report's checkout lacks yet)."""
    import importlib
    import importlib.util
    try:
        return importlib.import_module(f"tools.{name}")
    except ImportError:
        pass
    root = cell.get("engine_root")
    path = Path(root) / "digitizer" / "tools" / f"{name}.py" if root else None
    if path is None or not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"_engine_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def short_bare(_stream, _fx, cell) -> str:
    psu = _engine_module("pro_satin_underlay", cell)
    if psu is None:
        return "n/a (reader not on this engine)"
    rows = psu.read_columns(psu.blocks_from_file(Path(cell["dst"])), 6)
    short = [r for r in rows if r["length"] < 5.0]
    if not short:
        return "0 short columns"
    sb = sum(1 for r in short if r["bare"])
    return f"{100.0 * sb / len(short):.1f}% ({sb} of {len(short)})"


def letter_height(_stream, _fx, cell) -> str:
    """Median height of letter-sized pieces (0.8-6 mm tall), the way
    `small_text_columns` cuts a file into letters."""
    from tools import small_text_columns as stc
    pcs = stc.pieces(stc.read_blocks(cell["dst"]))
    hs = sorted(p["y1"] - p["y0"] for p in pcs if 0.8 <= p["y1"] - p["y0"] <= 6.0)
    if not hs:
        return "no small pieces"
    return f"{hs[len(hs) // 2]:.2f} ({len(hs)} pieces)"


def _needle_runs(stream) -> list[list[tuple[float, float]]]:
    """Needle-down runs: stitches between cuts, colour changes and jumps."""
    import pystitch
    runs, cur = [], []
    for x, y, c in stream:
        if c == pystitch.STITCH:
            cur.append((x, y))
        elif cur:
            runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    return runs


def stagger(stream, _fx, _cell) -> str:
    """PR #1058's own number, by its own reader (`tools.inside_stagger`): inner ends
    of a satin pivot that land within 0.1 mm of an earlier one, with the zones found."""
    from tools import inside_stagger as ist
    s = ist.summary(ist.read(_needle_runs(stream)))
    return f"{s['same_hole']} same-hole ({s['zones']} zones)"


def white_under_1mm(_stream, _fx, cell) -> str:
    """Stitches in near-white thread (the file's own colours) and how many step under
    1 mm from the one before inside the same block. Design x/y are tenths of a mm."""
    design = cell.get("design")
    if design is None:
        return "n/a (no thread colours)"
    colors = design.get("colors") or []
    white = short = ci = 0
    prev = None
    for s in design.get("stitches") or []:
        t = s.get("type")
        if t == "color":
            ci, prev = ci + 1, None
        elif t == "stitch":
            if ci < len(colors) and min(colors[ci].get(k, 0) for k in "rgb") >= 230:
                white += 1
                if prev is not None and math.dist(prev, (s["x"], s["y"])) < 10.0:
                    short += 1
            prev = (s["x"], s["y"])
        else:
            prev = None
    return f"{white:,} ({short:,} under 1 mm)"


#: the colour block holding the script word, (ours, the pro's), for
#: `script_square` (To a T's moved to our second block when the white faces
#: began to sew first, #1112)
SCRIPT_BLOCKS = {"bridge_hat": (3, 4), "bridge_lc": (2, 4), "tires_hat_3d": (0, 1),
                 "machine_hat": (1, 1)}


def script_square(_stream, fx, cell) -> str:
    """`tools.script_census` over the word's colour block (`SCRIPT_BLOCKS`):
    the share of its satin crosses square to the stroke (within 20 deg, the
    stroke read off the file's own coverage), over all the block's groups,
    weighted by crosses read, and its satin columns."""
    from tools import script_census as sc
    blocks = SCRIPT_BLOCKS.get(fx["slug"])
    if blocks is None:
        return "n/a (no block named)"
    res = sc.census(Path(cell["dst"]), blocks[1] if cell.get("runs") is None else blocks[0])
    gs = [g for g in res["groups"] if g["read"] and g["square_share"] is not None]
    read = sum(g["read"] for g in gs)
    if not read:
        return "no crosses read"
    share = sum(g["square_share"] * g["read"] for g in gs) / read
    return f"square {share:.2f} of {read} read, {sum(g['columns'] for g in res['groups'])} columns"


def tagged(_stream, _fx, cell) -> str:
    stats = cell.get("stats") or {}
    return str(stats["tagged"]) if "tagged" in stats else "n/a (not in the DST)"


METRICS = {"sub_half_mm": sub_half_mm, "fill_underlay": fill_underlay, "uncut_jumps": uncut_jumps,
           "white_stitches": white_stitches, "under_later": under_later, "rings": rings,
           "locks": locks, "short_bare": short_bare, "letter_height": letter_height,
           "stagger": stagger, "white_under_1mm": white_under_1mm, "tagged": tagged,
           "sub_1mm": sub_1mm, "satin_loops": satin_loops, "travel_runs": travel_runs,
           "small_lines": small_lines, "run_shapes": run_shapes, "script_square": script_square}


# ------------------------------------------------------------------- diff
def _grid(points):
    from collections import Counter
    return Counter((round(x / GRID_MM), round(y / GRID_MM)) for x, y in points)


def diff_points(off_pts, on_pts) -> list[tuple[float, float]]:
    """Grid cells whose needle COUNT differs, one entry per stitch of
    difference. A multiset, not a set: a lock walks over the run's own
    stations, so dropping it removes stitches without moving a point."""
    a, b = _grid(off_pts), _grid(on_pts)
    out = []
    for key in set(a) | set(b):
        n = abs(a.get(key, 0) - b.get(key, 0))
        out += [(key[0] * GRID_MM, key[1] * GRID_MM)] * n
    return out


def best_window(pts, w=WINDOW_MM[0], h=WINDOW_MM[1]) -> tuple[float, float, float, float] | None:
    """The w x h mm window holding the most changed points (1 mm steps)."""
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    best, bx, by = -1, x0, y0
    sx = [x0 + i for i in range(int(max(1, x1 - x0 - w + 2)))]
    sy = [y0 + j for j in range(int(max(1, y1 - y0 - h + 2)))]
    for cx in sx:
        for cy in sy:
            n = sum(1 for p in pts if cx <= p[0] <= cx + w and cy <= p[1] <= cy + h)
            if n > best:
                best, bx, by = n, cx, cy
    return (bx, by, bx + w, by + h)


# ---------------------------------------------------------------- renders
def _extents(stream):
    pts = needle_points(stream)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _design_frame(design: dict):
    """(x0 mm, y_top mm, w, h) of the render's drawn box in PLAN mm (y-down)."""
    from digitizer_core import stitchviz
    x0, x1, y0, y1 = stitchviz._bounds(design.get("stitches") or [])
    return x0 / 10.0, -y1 / 10.0, (x1 - x0) / 10.0, (y1 - y0) / 10.0


def render_crop(design: dict, box_mm, ppm=PPM):
    """`box_mm` in plan mm (y-down, absolute) -> BGR crop of the render."""
    from digitizer_core import stitchviz
    img = stitchviz.render_design(design, px_per_mm=ppm)
    fx, fy, _w, _h = _design_frame(design)
    x0, y0, x1, y1 = box_mm
    px = (int(round((x0 - fx + PAD_MM) * ppm)), int(round((y0 - fy + PAD_MM) * ppm)),
          int(round((x1 - fx + PAD_MM) * ppm)), int(round((y1 - fy + PAD_MM) * ppm)))
    h, w = img.shape[:2]
    return img[max(0, px[1]):max(1, min(h, px[3])), max(0, px[0]):max(1, min(w, px[2]))]


JPEG = [1, 90]   # cv2.IMWRITE_JPEG_QUALITY: 112 tiles at 40 px/mm are 18 MB as PNG, 3 as JPEG


def _write(path, img):
    import cv2
    cv2.imwrite(str(path), img, JPEG)


def is_pro_image(name: str) -> bool:
    """A tile drawn from the pro's file: `<flag>__<slug>__pro.jpg` or `__pro_xray.jpg`."""
    return Path(name).stem.endswith(("__pro", "__pro_xray"))


def image_file(name: str, renders: Path, pro_dir: Path | None = None) -> Path:
    """Where tile `name` lives: the pro's under `pro_dir` when given, every
    other under `renders`."""
    return Path(pro_dir if pro_dir is not None and is_pro_image(name) else renders) / name


def _label(img, text):
    import cv2
    im = img.copy()
    cv2.rectangle(im, (0, 0), (im.shape[1], 30), (255, 255, 255), -1)
    cv2.putText(im, text, (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 0), 2, cv2.LINE_AA)
    return im


def reversed_design(design: dict) -> dict:
    """The design with its sewing order reversed, block by block, so what was
    sewn FIRST (underlay) draws last, on top. A picture of what lies under
    the top thread; the renderer itself is untouched."""
    blocks, cur = [], []
    for s in design.get("stitches") or []:
        if s.get("type") == "color":
            blocks.append(cur)
            cur = []
        else:
            cur.append(s)
    blocks.append(cur)
    colors = list(design.get("colors") or [])
    out = []
    for i, blk in reversed(list(enumerate(blocks))):
        if out:
            out.append({**(out[-1]), "type": "color"})
        out += list(reversed(blk))
    return {**design, "stitches": out, "colors": list(reversed(colors[:len(blocks)])) or colors}


def where_image(design: dict, box_mm, ppm: float = 8.0):
    """The whole OFF design small, with the crop window drawn in red."""
    import cv2
    from digitizer_core import stitchviz
    img = stitchviz.render_design(design, px_per_mm=ppm).copy()
    fx, fy, _w, _h = _design_frame(design)
    x0, y0, x1, y1 = box_mm
    p0 = (int(round((x0 - fx + PAD_MM) * ppm)), int(round((y0 - fy + PAD_MM) * ppm)))
    p1 = (int(round((x1 - fx + PAD_MM) * ppm)), int(round((y1 - fy + PAD_MM) * ppm)))
    cv2.rectangle(img, p0, p1, (0, 0, 255), 2)
    return img


def pro_box(design_pro: dict, ours_frame, box_mm):
    """The same window on the pro's render: ours' box as fractions of our
    drawn extents, applied to the pro's (no registration, as pro_pair)."""
    fx, fy, fw, fh = ours_frame
    px, py, pw, ph = _design_frame(design_pro)
    x0, y0, x1, y1 = box_mm
    sx, sy = pw / fw, ph / fh
    return (px + (x0 - fx) * sx, py + (y0 - fy) * sy, px + (x1 - fx) * sx, py + (y1 - fy) * sy)


# ------------------------------------------------------------------ report
def load_cell(path: Path) -> dict:
    cell = {"dst": path / "ours.dst",
            "stats": json.loads((path / "stats.json").read_text(encoding="utf-8")),
            "design": json.loads((path / "design.json").read_text(encoding="utf-8")),
            "runs": json.loads((path / "runs.json").read_text(encoding="utf-8"))}
    cell["stream"] = read_stream(cell["dst"])
    return cell


def pro_cell(fx: dict) -> dict:
    from tools.pro_parity import pairframe
    cell = {"dst": fx["pro_dst"], "stream": read_stream(fx["pro_dst"]), "runs": None}
    # counts from the DST; the picture from the PES when there is one, so the
    # pro's crop draws in his thread colours rather than the grey fallback
    cell["design"] = (pairframe.design_for(fx["pro_pes"], None, None, fx["slug"])
                      if fx["pro_pes"] else None)
    cell["design_render"] = cell["design"] or pairframe.design_for(fx["pro_dst"], None, None, fx["slug"])
    return cell


TRAVEL_KEYS = ("exposed_mm", "bare_mm", "offbody_mm", "cpu_s", "md5")


def measure(flag: str, cell: dict, fx: dict) -> dict:
    out = counts(cell["stream"])
    fn = METRICS[FLAGS[flag]["metric"]]
    try:
        out["about"] = fn(cell["stream"], fx, cell)
    except Exception as e:  # noqa: BLE001 -- a reader that cannot read a file is a cell, not a crash
        out["about"] = f"reader failed: {type(e).__name__}"
    stats = cell.get("stats") or {}
    out.update({k: stats[k] for k in TRAVEL_KEYS if k in stats})   # ours only: plan instruments
    return out


def bare_rise(off: dict, on: dict) -> dict | None:
    """Gate 3's read for one cell pair: bare thread (`hairline_travel`, needle-down
    legs) OFF -> ON at each clearance band. None when either cell predates the
    instrument. `rises`: the bands where ON lays more bare thread than OFF."""
    a, b = off.get("bare_mm"), on.get("bare_mm")
    if not isinstance(a, dict) or not isinstance(b, dict):
        return None
    rises = [k for k in sorted(a) if b.get(k, 0.0) > a[k] + 0.005]
    return {"off": a, "on": b, "rises": rises}


def gate3_verdict(rows: list[dict]) -> str:
    """A flag's gate-3 word over its rendered cells: 'gate 3' when ON raises bare
    thread at the instrument's own band (0.20 mm) on any fixture -- and then it is
    not asked -- 'clear' when no cell rises, 'n/a' when no cell carries it."""
    reads = [r["bare"] for r in rows if r.get("bare")]
    for r in rows:
        reads += [x for x in (r.get("bare_also"),) if x]
    if not reads:
        return "n/a"
    inst = f"{BARE_BANDS_MM[0]:.2f}"
    hit = [x for x in reads if inst in x["rises"]]
    if not hit:
        return "clear"
    wider = any(len(x["rises"]) > 1 for x in hit)
    return "gate 3" if wider else f"gate 3 (at {inst} mm only: overlap under half a thread)"


def build_rows(cache: Path, renders: Path, flags: list[str], slugs: list[str],
               base_sha: str | None = None, pro_dir: Path | None = None) -> list[dict]:
    """One row per (flag, fixture). With `base_sha` (the sheet's OFF engine), a row
    whose cells ran on another engine says so: `stale` when its OFF is not the
    base's OFF byte for byte, `base_bytes` when it is (the base moved nowhere
    this job sews). The pro's tiles go to `pro_dir` when given (`image_file`)."""
    renders.mkdir(parents=True, exist_ok=True)
    if pro_dir is not None:
        Path(pro_dir).mkdir(parents=True, exist_ok=True)
    rows = []
    pros: dict[str, tuple[dict, dict]] = {}
    for slug in dict.fromkeys(s for f in flags for s in flag_fixtures(f, slugs)):
        fx = fixture_files(slug)
        pros[slug] = (fx, pro_cell(fx))
    for flag in flags:
        for slug in flag_fixtures(flag, slugs):
            fx, pro = pros[slug]
            on_dir = cache / slug / flag
            row = {"flag": flag, "fixture": slug, "width_mm": fx["width_mm"], "pr": FLAGS[flag]["pr"],
                   "about": FLAGS[flag]["about"], "sets": FLAGS[flag]["sets"],
                   "note": FLAGS[flag].get("note", "")}
            if fx.get("art_fallback"):
                row["note"] = (row["note"] + " " if row["note"] else "") + (
                    f"{slug}: digitized from the corpus crop {fx['art'].name} (the customer file "
                    "is on G:, unmounted).")
            if not (on_dir / "stats.json").exists():
                row["status"] = "not run"
                rows.append(row)
                continue
            on = load_cell(on_dir)
            sha = on["stats"]["engine"]
            off_dir = cell_dir(cache, slug, off_arm(flag), sha)
            if not (off_dir / "stats.json").exists():
                row["status"] = f"OFF cell missing for engine {sha}"
                rows.append(row)
                continue
            off = load_cell(off_dir)
            fx["ours_ref"] = off["dst"]      # a reader that registers the pro needs one of ours
            row["engine"] = sha
            row["engine_root"] = on["stats"]["engine_root"]
            for c in (off, on, pro):
                c["engine_root"] = row["engine_root"]
            row["off"] = measure(flag, off, fx)
            row["on"] = measure(flag, on, fx)
            row["pro"] = measure(flag, pro, fx)
            row["bare"] = bare_rise(row["off"], row["on"])
            if base_sha and sha != base_sha:
                base_off = cell_dir(cache, slug, off_arm(flag), base_sha) / "ours.dst"
                same = base_off.exists() and _md5(base_off) == _md5(off["dst"])
                row["base_bytes" if same else "stale"] = sha
            also = None
            also_dir = cache / slug / (also_arm(flag, slug) or "-")
            if also_arm(flag, slug) and (also_dir / "stats.json").exists():
                also = load_cell(also_dir)
                also["engine_root"] = row["engine_root"]
                row["also"] = measure(flag, also, fx)
                row["also_label"] = FLAGS[flag]["also"]["label"]
                row["bare_also"] = bare_rise(row["off"], row["also"])
            row["pro_file"] = fx["pro_dst"].name
            d = diff_points(needle_points(off["stream"]), needle_points(on["stream"]))
            row["diff"] = len(d)
            same_file = off["dst"].read_bytes() == on["dst"].read_bytes()
            row["byte_identical"] = same_file
            d_win = d
            if also is not None:
                d_also = diff_points(needle_points(off["stream"]), needle_points(also["stream"]))
                row["diff_also"] = len(d_also)
                d_win = d or d_also        # ON inert and the third cell not: crop on the third
            if not d_win:
                row["status"] = "no change"
                rows.append(row)
                continue
            box = best_window(d_win)
            row["box_mm"] = [round(v, 1) for v in box]
            row["in_window"] = sum(1 for p in d_win if box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3])
            frame = _design_frame(off["design"])
            pbox = pro_box(pro["design_render"], frame, box)
            tiles = {"off": render_crop(off["design"], box), "on": render_crop(on["design"], box)}
            if also is not None:
                tiles["also"] = render_crop(also["design"], box)
            tiles["pro"] = render_crop(pro["design_render"], pbox)
            row["images"] = {}
            for side, img in tiles.items():
                m = row[side]
                name = f"{flag}__{slug}__{side}.jpg"
                _write(image_file(name, renders, pro_dir), _label(img, f"{_side_label(row, side)}: {m['stitches']} st, "
                                                   f"{m['trims']} tr"))
                row["images"][side] = name
            if FLAGS[flag].get("xray"):
                xr = {"off": render_crop(reversed_design(off["design"]), box),
                      "on": render_crop(reversed_design(on["design"]), box),
                      "pro": render_crop(reversed_design(pro["design_render"]), pbox)}
                for side, img in xr.items():
                    name = f"{flag}__{slug}__{side}_xray.jpg"
                    _write(image_file(name, renders, pro_dir), _label(img, f"{side.upper()} x-ray: first-sewn on top"))
                    row["images"][side + "_xray"] = name
            name = f"{flag}__{slug}__where.jpg"
            _write(renders / name, where_image(off["design"], box))
            row["images"]["where"] = name
            row["status"] = "rendered"
            rows.append(row)
            print(f"{flag}/{slug}: {len(d_win)} points differ, window {row['box_mm']}", flush=True)
    return rows


def _fmt(m: dict | None) -> str:
    if m is None:
        return "-"
    cc = f" / {m['colours']} cc" if "colours" in m else ""
    return f"{m['stitches']:,} st / {m['trims']} tr{cc} / {m['about']}"


def _sides(r: dict) -> tuple[str, ...]:
    """The row's cells in order: OFF, ON, the optional third cell, the pro."""
    return ("off", "on", *(("also",) if "also" in r else ()), "pro")


def _side_label(r: dict, side: str) -> str:
    return r.get("also_label", "ALSO") if side == "also" else side.upper()


def _fmt_on(r: dict) -> str:
    """ON, and the third cell beside it when the row has one."""
    on = _fmt(r["on"])
    return on if "also" not in r else f"{on}; {_side_label(r, 'also')}: {_fmt(r['also'])}"


def _md_text(s: str) -> str:
    """An HTML intro line as markdown: <code> to backticks, entities to text."""
    import re
    s = s.replace("<code>", "`").replace("</code>", "`").replace("&mdash;", "--")
    return re.sub(r"<[^>]+>", "", s).replace("&amp;", "&")


def _md_travel(m: dict | None) -> str:
    return _travel(m).replace("&middot;", "/")


def markdown(rows: list[dict], renders: Path, doc: Path, date: str = DATE,
             sheet: dict | None = None, intro: list[str] | None = None) -> str:
    rel = os.path.relpath(renders, doc.parent).replace("\\", "/")
    lines = [f"# Flip sheet {date}: OFF | ON | pro, one crop per flag and fixture", ""]
    for p in intro or []:
        lines += [_md_text(p), ""]
    if sheet:
        lines += ["## What Kent is asked", "",
                  "| flag (PR) | kind | on this sheet | gate 3 | fixtures |", "|---|---|---|---|---|"]
        for flag in sheet:
            fr = [r for r in rows if r["flag"] == flag]
            if fr:
                lines.append(f"| `{flag}` (#{FLAGS[flag]['pr']}) | {flag_kind(flag)} | "
                             f"{ask_status(flag, fr, sheet)[1]} | {gate3_verdict(fr)} | "
                             f"{', '.join(r['fixture'] for r in fr)} |")
        lines += ["", "## Travel per cell (mm)", "",
                  "exposed (`travel_cover`) / bare thread at 0.20/0.25/0.30 mm clearance "
                  "(`hairline_travel`, gate 3) / travel off the DST's own bodies. The pro has no "
                  "plan, so no cell.", "",
                  "| flag | fixture | OFF | ON | third cell |", "|---|---|---|---|---|"]
        for r in rows:
            if r.get("status") in ("rendered", "no change"):
                lines.append(f"| `{r['flag']}` | {r['fixture']} | {_md_travel(r.get('off'))} | "
                             f"{_md_travel(r.get('on'))} | {_md_travel(r.get('also'))} |")
        lines.append("")
    lines += [
             "Kent's ruling 2026-10-22: stitch layout is judged in the preview; only pull and "
             "comp need fabric. Every row here is a layout flag built OFF, rendered where it "
             "changes stitches, beside the professional's file for the same job. The flips are "
             "Kent's; nothing in this PR changes a default.", "",
             f"Open `{rel}/index.html` for the pictures side by side. The pro's crops are not "
             "committed (Kent 2026-10-27: \"Stop new ones, keep old (Recommended)\"): they are "
             "written to `pro_renders/`, gitignored, and `report --inline` puts them on the local "
             "page. Regenerate with "
             "`python -m tools.flip_sheet_renders run` then `report` (see the tool's docstring; "
             "a flag not on main runs with `--engine <checkout>`).", "",
             "Each cell: stitches / trims / the number the flag is about. Crops are 18 x 11 mm at "
             "40 px/mm, placed on the window holding the most changed needle points (OFF vs ON, "
             "0.05 mm grid); the pro's crop is the same window as a fraction of his extents, no "
             "registration. The hat preset at the pro's width (Fremont at Kent's 92.5).", "",
             "| flag (PR) | fixture | engine | OFF | ON | pro | changed points | crop |",
             "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        tag = f"`{r['flag']}` (#{r['pr']})"
        if r.get("status") in ("not run", None) or r.get("status", "").startswith("OFF cell"):
            lines.append(f"| {tag} | {r['fixture']} | - | - | - | - | {r.get('status')} | - |")
            continue
        if r["status"] == "no change":
            why = "byte-identical DST" if r["byte_identical"] else "0 needle points differ"
            lines.append(f"| {tag} | {r['fixture']} | {_engine_note(r)} | {_fmt(r['off'])} | {_fmt_on(r)} | "
                         f"{_fmt(r['pro'])} | **no change** ({why}) | - |")
            continue
        im = r["images"]
        crop = " ".join(f"{s} (local only)" if is_pro_image(im[s]) else f"[{s}]({rel}/{im[s]})" for s in im)
        lines.append(f"| {tag} | {r['fixture']} | {_engine_note(r)} | {_fmt(r['off'])} | {_fmt_on(r)} | "
                     f"{_fmt(r['pro'])} | {r['diff']:,} ({r['in_window']:,} in crop) | {crop} |")
    lines += ["", "## What each number is", ""]
    for flag, spec in FLAGS.items():
        if any(r["flag"] == flag for r in rows):
            note = f" **{spec['note']}**" if spec.get("note") else ""
            lines.append(f"- `{flag}`: {spec['about']}. Sets `{json.dumps(spec['sets'])}`.{note}")
    lines += ["", "Readers: stitches and trims are pystitch records (the pro read as DST, never PES: "
              "the PES reader reports a TRIM at every jump). `stitches under 0.5 mm` are "
              "needle-to-needle. `fills read BARE` is `tools/pro_fill_underlay.py`. `uncut jumps` "
              "are needle-up hops with no TRIM or colour change round them. `white thread` reads "
              "the file's own colours (the pro's PES; a DST has none). `hops under later thread` "
              "is `tools/trim_classes.py`. `edge-cap rings` are plan run roles, so the pro has "
              "none. `run starts that lock`: the first three stitches after a cut, colour change "
              "or jump all at most 1.0 mm with a reversal. `short columns bare` is "
              "`tools/pro_satin_underlay.py` (PR #1044's branch). `letter height` is the median "
              "of `tools/small_text_columns.py`'s 0.8-6 mm pieces.", ""]
    return "\n".join(lines) + "\n"


def summary_table(rows: list[dict]) -> str:
    """One line per (flag, fixture): the flag's own number OFF | ON | pro, at a glance."""
    out = ["<table class='sum'><tr><th>flag (PR)</th><th>fixture</th><th>OFF</th><th>ON</th>"
           "<th>pro</th><th>needle points changed</th></tr>"]
    for r in rows:
        tag = f"<code>{r['flag']}</code> (#{r['pr']}, {flag_kind(r['flag'])})"
        if r.get("status") not in ("rendered", "no change"):
            out.append(f"<tr><td>{tag}</td><td>{r['fixture']}</td><td colspan='4'>{r.get('status')}</td></tr>")
            continue
        change = "none (no change)" if r["status"] == "no change" else f"{r['diff']:,}"
        out.append(f"<tr><td>{tag}</td><td>{r['fixture']}</td>"
                   + f"<td>{_fmt(r['off'])}</td><td>{_fmt_on(r)}</td><td>{_fmt(r['pro'])}</td>"
                   + f"<td>{change}</td></tr>")
    out.append("</table>")
    return "".join(out)


def _counts(m: dict | None) -> str:
    if m is None:
        return "-"
    return f"{m['stitches']:,} st &middot; {m['trims']} tr &middot; {m.get('colours', '-')} cc"


def _travel(m: dict | None) -> str:
    """exposed travel / bare thread at each band / travel off DST bodies, mm."""
    if not m or not isinstance(m.get("bare_mm"), dict):
        return "-"
    bare = "/".join(f"{m['bare_mm'][k]:.2f}" for k in sorted(m["bare_mm"]))
    off = m.get("offbody_mm")
    off = f"{off:.1f}" if isinstance(off, (int, float)) else str(off)
    return f"exp {m['exposed_mm']:.1f} &middot; bare {bare} &middot; off-body {off}"


def ask_status(flag: str, rows: list[dict], sheet: dict | None) -> tuple[str, str]:
    """(badge class, text) for a flag on a sheet with an ask list: 'ask' when Kent
    rules it here, 'gate3' when it was to be asked but ON raises bare thread (gate 3:
    not asked), 'shown' with the sheet's reason otherwise. ('', '') off a sheet."""
    if not sheet or flag not in sheet:
        return "", ""
    s = sheet[flag]
    if not s.get("ask"):
        return "shown", f"SHOWN, NOT ASKED: {s.get('label', '')}"
    g = gate3_verdict(rows)
    if g.startswith("gate 3"):
        return "gate3", f"NOT ASKED: {g} -- ON raises bare thread"
    return "ask", "ASKED: Kent rules it from this sheet" + (" (gate 3 clear)" if g == "clear" else "")


def _engine_note(r: dict) -> str:
    if r.get("stale"):
        return f"engine {r['stale']}: not current base"
    if r.get("base_bytes"):
        return f"engine {r['base_bytes']} (its OFF is the current base's, byte for byte)"
    return f"engine {r.get('engine', '-')}"


def flag_header(flag: str, rows: list[dict], sheet: dict | None = None) -> str:
    """A flag's section head: its kind, whether it is asked, what it sets, and per
    fixture the stitches, trims and colour changes OFF -> ON -> pro beside the
    travel instruments, so it is decided on its own."""
    kind = flag_kind(flag)
    why = ("judged from these renders (Kent 2026-10-22)" if kind == "LAYOUT"
           else "ROADMAP gate 1: needs a sew-out, the renders cannot decide it")
    cls, ask = ask_status(flag, rows, sheet)
    has_also = any("also" in r for r in rows)
    lines = [f"<h2 class='group' id='{flag}'><code>{flag}</code> (PR #{FLAGS[flag]['pr']}) "
             f"<span class='kind {kind.lower()}'>{kind}</span>"
             + (f"<span class='ask {cls}'>{ask}</span>" if ask else "") + "</h2>",
             f"<p class='nochange'>{kind}: {why}. Sets <code>{json.dumps(FLAGS[flag]['sets'])}</code>.</p>",
             "<div class='scroll'><table class='sum'><tr><th>fixture</th><th>engine</th><th>OFF</th>"
             "<th>ON</th>" + ("<th>third cell</th>" if has_also else "") + "<th>pro</th><th>change</th>"
             "<th>travel OFF (mm)</th><th>travel ON (mm)</th></tr>"]
    width = 8 + has_also
    for r in rows:
        if r.get("status") not in ("rendered", "no change"):
            lines.append(f"<tr><td>{r['fixture']}</td><td colspan='{width}'>{r.get('status')}</td></tr>")
            continue
        change = "none" if r["status"] == "no change" else f"{r['diff']:,} points"
        also = (f"<td>{_side_label(r, 'also')}: {_counts(r['also'])}</td>" if "also" in r
                else ("<td>-</td>" if has_also else ""))
        lines.append(f"<tr><td>{r['fixture']}</td><td>{_engine_note(r)}</td><td>{_counts(r['off'])}</td>"
                     f"<td>{_counts(r['on'])}</td>{also}<td>{_counts(r['pro'])}</td><td>{change}</td>"
                     f"<td>{_travel(r.get('off'))}</td><td>{_travel(r.get('on'))}</td></tr>")
    lines.append("</table></div>")
    return "".join(lines)


#: The page's look. Layout: one column of flag sections, each a header table over
#: crop rows; tiles wrap to one column at phone width, wide tables scroll in place.
PAGE_CSS = (
    ":root{--bg:#f6f7f9;--surface:#ffffff;--fg:#1d232b;--muted:#5b6573;--line:#d9dee5;"
    "--code:#eceff3;--layout:#2457c5;--fabric:#b23a2e;--ask:#1f7a4d;--gate:#a35a00;"
    "--shown:#6b5ca5;--on-badge:#ffffff;"
    "--sans:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;"
    "--mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Consolas,monospace}"
    "@media (prefers-color-scheme:dark){:root:not([data-theme='light']){--bg:#14181e;"
    "--surface:#1c222a;--fg:#e4e8ee;--muted:#9aa5b3;--line:#323b47;--code:#262e38;"
    "--layout:#7ea2f2;--fabric:#ef8a7f;--ask:#5fc493;--gate:#f0ad4e;--shown:#b3a6ea;"
    "--on-badge:#14181e;color-scheme:dark}}"
    ":root[data-theme='dark']{--bg:#14181e;--surface:#1c222a;--fg:#e4e8ee;--muted:#9aa5b3;"
    "--line:#323b47;--code:#262e38;--layout:#7ea2f2;--fabric:#ef8a7f;--ask:#5fc493;"
    "--gate:#f0ad4e;--shown:#b3a6ea;--on-badge:#14181e;color-scheme:dark}"
    "body{font-family:var(--sans);background:var(--bg);color:var(--fg);line-height:1.45;"
    "padding-block:20px 40px;padding-left:max(16px,env(safe-area-inset-left,0px));"
    "padding-right:max(16px,env(safe-area-inset-right,0px));margin:0}"
    "main{max-width:1280px;margin:0 auto;display:flex;flex-direction:column;gap:14px}"
    "h1{font-size:22px;margin:0;text-wrap:balance} p{margin:0;max-width:75ch}"
    "code{font-family:var(--mono);font-size:.92em;background:var(--code);padding:1px 4px;"
    "border-radius:3px;overflow-wrap:anywhere}"
    ".scroll{overflow-x:auto;max-width:100%}"
    "table.sum{border-collapse:collapse;font-size:13px;background:var(--surface);"
    "font-variant-numeric:tabular-nums}"
    "table.sum td,table.sum th{border:1px solid var(--line);padding:4px 8px;text-align:left;"
    "vertical-align:top}"
    "table.sum th{color:var(--muted);font-weight:600;font-size:12px;letter-spacing:.02em}"
    "h2.group{font-size:19px;margin:26px 0 0;padding-top:12px;border-top:3px solid var(--fg);"
    "display:flex;flex-wrap:wrap;align-items:center;gap:8px;text-wrap:balance}"
    ".kind,.ask{font-size:12px;font-weight:600;padding:2px 9px;border-radius:10px;"
    "color:var(--on-badge);letter-spacing:.03em}"
    ".kind.layout{background:var(--layout)} .kind.fabric{background:var(--fabric)}"
    ".ask.ask{background:var(--ask)} .ask.gate3{background:var(--gate)}"
    ".ask.shown{background:var(--shown)}"
    ".nochange{color:var(--muted)}"
    ".row{background:var(--surface);border:1px solid var(--line);border-radius:6px;padding:12px;"
    "display:flex;flex-direction:column;gap:8px;min-width:0}"
    ".flag{font-size:16px;font-weight:600}"
    ".tiles{display:flex;gap:12px;flex-wrap:wrap}"
    ".tile{flex:1 1 280px;min-width:0}"
    ".tile img,.where img{width:100%;height:auto;max-width:100%;border:1px solid var(--line);"
    "display:block}"
    ".nums{font-size:13px;margin-top:4px;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}"
    ".nums b{display:inline-block;min-width:48px}"
    ".where{max-width:520px}"
    "a{color:var(--layout)} a:focus-visible{outline:2px solid var(--layout);outline-offset:2px}"
)
FONT_LINK = ("<link rel='stylesheet' href='https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:"
             "wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap'>")


def ask_table(rows: list[dict], sheet: dict) -> str:
    """The sheet's first table: every flag on it, asked or shown, with the reason and
    its gate-3 read, linking to its section."""
    out = ["<div class='scroll'><table class='sum'><tr><th>flag (PR)</th><th>kind</th>"
           "<th>on this sheet</th><th>gate 3 (bare thread, ON vs OFF)</th><th>fixtures</th></tr>"]
    for flag in sheet:
        fr = [r for r in rows if r["flag"] == flag]
        if not fr:
            continue
        cls, text = ask_status(flag, fr, sheet)
        out.append(f"<tr><td><a href='#{flag}'><code>{flag}</code></a> (#{FLAGS[flag]['pr']})</td>"
                   f"<td>{flag_kind(flag)}</td><td><span class='ask {cls}'>{text}</span></td>"
                   f"<td>{gate3_verdict(fr)}</td><td>{', '.join(r['fixture'] for r in fr)}</td></tr>")
    out.append("</table></div>")
    return "".join(out)


def html_parts(rows: list[dict], src=lambda name: name, date: str = DATE,
               sheet: dict | None = None, intro: list[str] | None = None) -> tuple[str, str]:
    """(head, body) of the sheet. `src` maps a render's file name to the `<img src>`
    value: the name itself for a page beside its renders, a data URI for the
    inlined one. With `sheet` (`W5`), the page opens on its ask list and each
    flag's header says whether it is asked."""
    head = (f"<title>Flip sheet {date}</title>\n"
            "<meta name='claude:viewport-fit-sides' content='cover'>\n"
            f"{FONT_LINK}\n<style>{PAGE_CSS}</style>")
    out = ["<main>", f"<h1>Flip sheet {date} &mdash; OFF | ON | pro</h1>",
           "<p>Layout flags built OFF, each rendered where it changes stitches beside the "
           "professional's file for the same job (hat preset at the pro's width). 40 px/mm: a "
           "0.4 mm thread is 16 px. The flips are Kent's.</p>"]
    out += [f"<p>{p}</p>" for p in intro or []]
    if sheet:
        out.append(ask_table(rows, sheet))
    out.append(summary_table(rows))
    seen: set[str] = set()
    for r in rows:
        if r["flag"] not in seen:
            seen.add(r["flag"])
            out.append(flag_header(r["flag"], [x for x in rows if x["flag"] == r["flag"]], sheet))
        head_row = f"<p class='flag'><code>{r['flag']}</code> (PR #{r['pr']}) &middot; {r['fixture']} " \
                   f"at {r['width_mm']} mm &middot; {_engine_note(r)}</p>"
        if r.get("note"):
            head_row += f"<p class='nochange'>&#9888; {r['note']}</p>"
        if r.get("status") not in ("rendered", "no change"):
            out.append(f"<div class='row'>{head_row}<p class='nochange'>{r.get('status')}</p></div>")
            continue
        nums = "".join(f"<div><b>{_side_label(r, s)}</b> {_fmt(r[s])}</div>" for s in _sides(r))
        if r["status"] == "no change":
            why = "byte-identical DST" if r["byte_identical"] else "0 needle points differ"
            out.append(f"<div class='row'>{head_row}<p class='nochange'><b>No change on this fixture</b> "
                       f"({why}).</p><div class='nums'>{nums}</div></div>")
            continue
        tiles = "".join(f"<div class='tile'><img src='{src(r['images'][s])}' alt='{s}'>"
                        f"<div class='nums'><b>{_side_label(r, s)}</b> {_fmt(r[s])}</div></div>"
                        for s in _sides(r))
        if "off_xray" in r["images"]:
            tiles += "".join(f"<div class='tile'><img src='{src(r['images'][s + '_xray'])}' alt='{s} x-ray'>"
                             f"<div class='nums'><b>{s.upper()}</b> x-ray: sewing order reversed, "
                             f"underlay drawn on top</div></div>" for s in ("off", "on", "pro"))
        where = (f"<div class='where'><img src='{src(r['images']['where'])}' alt='where'>"
                 f"<div class='nums'>where the crop sits (OFF, red box)</div></div>")
        third = (f" The third cell ({_side_label(r, 'also')}) differs from OFF at "
                 f"{r['diff_also']:,} points." if "diff_also" in r else "")
        out.append(f"<div class='row'>{head_row}<p>{r['about']}. {r['diff']:,} needle points differ, "
                   f"{r['in_window']:,} in this {WINDOW_MM[0]:g} x {WINDOW_MM[1]:g} mm crop at "
                   f"{r['box_mm']} mm (plan frame).{third} Sets <code>{json.dumps(r['sets'])}</code>.</p>"
                   f"<div class='tiles'>{tiles}</div>{where}</div>")
    out.append("</main>")
    return head, "\n".join(out)


def html(rows: list[dict], src=lambda name: name, date: str = DATE,
         sheet: dict | None = None, intro: list[str] | None = None) -> str:
    """The sheet as a whole document, for a file opened from disk."""
    head, body = html_parts(rows, src, date, sheet, intro)
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1,viewport-fit=cover'>\n"
            f"{head}</head><body>\n{body}\n</body></html>")


def data_uri(path: Path, quality: int | None = None, max_w: int | None = None) -> str:
    """A render as a base64 JPEG data URI: its own bytes, or re-encoded smaller."""
    raw = Path(path).read_bytes()
    if quality is not None:
        import cv2
        import numpy as np
        img = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
        if max_w and img.shape[1] > max_w:
            h = max(1, round(img.shape[0] * max_w / img.shape[1]))
            img = cv2.resize(img, (max_w, h), interpolation=cv2.INTER_AREA)
        ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not ok:
            raise RuntimeError(f"cannot re-encode {path}")
        raw = buf.tobytes()
    return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")


def inline_html(rows: list[dict], renders: Path, date: str = DATE,
                max_mb: float = INLINE_MAX_MB, sheet: dict | None = None,
                intro: list[str] | None = None, fragment: bool = False,
                pro_dir: Path | None = None) -> tuple[str, tuple]:
    """ONE self-contained page: the sheet with every image inlined. Tries the
    renders as written, then re-encodes smaller (`INLINE_LEVELS`) until the page
    fits `max_mb`; returns the page and the (quality, max width) that fitted --
    the last level if none did. `fragment`: the page without its document
    wrapper (title, style, content), the form an Artifact publish wraps itself.
    `pro_dir`: where the pro's tiles are (`image_file`); the page stays local."""
    renders = Path(renders)
    page, level = "", INLINE_LEVELS[0]
    for level in INLINE_LEVELS:
        cache: dict[str, str] = {}

        def src(name, _q=level[0], _w=level[1]):
            if name not in cache:
                cache[name] = data_uri(image_file(name, renders, pro_dir), _q, _w)
            return cache[name]

        if fragment:
            page = "\n".join(html_parts(rows, src, date, sheet, intro))
        else:
            page = html(rows, src, date, sheet, intro)
        if len(page.encode("utf-8")) <= max_mb * 1024 * 1024:
            break
    return page, level


def w5_intro(base_sha: str | None) -> list[str]:
    """The wave-5 sheet's opening lines: what OFF is, and what it is not."""
    return [f"OFF is main's engine (<code>{base_sha or '-'}</code>): <code>sew_enclosed_white</code> "
            "and <code>small_text_bay_mouth</code> ON (#1112), <code>fine_bars_satin</code> and "
            "<code>outline_loop_mitre</code> ON (#1121), <code>small_text_reset_grow_away</code> "
            "ON (#1113, #1127), <code>script_strokes</code> ON (#1136), and MFab's recipe turning "
            "ON by itself on MFab hat and LC (#1115) with the three keyline switches (#1122) and "
            "the loop chain (#1134) inside it. Every "
            "asked cell was re-digitized on it, or kept from an earlier base only where that "
            "job's OFF is byte-identical; a row drawn on another engine says so.",
            "Not on this sheet: <code>script_strokes</code>, which Kent ruled ON 2026-10-26 and "
            "#1136 flipped; #1119 and #1135 have its renders.",
            "Not asked: <code>keyline_fold_slivers</code>, <code>skip_covered_shapes</code> and "
            "<code>absorb_fragments</code>. All three ON at once (the <code>keyline_trio</code> "
            "row) sew OFF's DST byte for byte on every white job off MFab, so no render can judge "
            "them there; on MFab they are already ON through the gate (#1122).",
            "Gate 3 is <code>tools/hairline_travel</code>'s bare thread (needle-down travel legs "
            "further than the clearance from every laid stitch), read at 0.20 / 0.25 / 0.30 mm as "
            "#1112 read it. A flag whose ON raises it is marked and not asked. Exposed travel "
            "(<code>tools/travel_cover</code>, which also counts travel lying on EARLIER thread) and "
            "travel off the DST's own bodies are information, with no veto.",
            "Stitches, trims and colour changes are read off the DST for OFF, ON and the pro "
            "(never his PES)."]


def report_cmd(a) -> int:
    sheet = W5 if a.w5 else None
    flags = a.flags or (list(W5) if a.w5 else list(FLAGS))
    date = a.date if a.date != DATE or not a.w5 else W5_DATE
    slugs = a.fixtures or None
    renders = Path(a.renders)
    pro_dir = pro_renders.refuse_docs(a.pro_renders or pro_renders.out_dir(renders.name))
    rows = build_rows(Path(a.cache), renders, flags, slugs, a.base, pro_dir)
    intro = (w5_intro(a.base) if a.w5 else []) + list(a.intro or [])
    doc = Path(a.out)
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text(markdown(rows, renders, doc, date, sheet, intro), encoding="utf-8")

    def local(name):    # the page beside the renders reaches the pro's folder on this machine
        return os.path.relpath(image_file(name, renders, pro_dir), renders).replace("\\", "/")

    (renders / "index.html").write_text(html(rows, local, date=date, sheet=sheet, intro=intro),
                                        encoding="utf-8")
    (Path(a.renders) / "rows.json").write_text(json.dumps(rows, indent=1, default=str), encoding="utf-8")
    print(f"wrote {doc} and {Path(a.renders) / 'index.html'} ({len(rows)} rows)")
    if a.inline:
        page, level = inline_html(rows, renders, date, sheet=sheet, intro=intro,
                                  fragment=a.artifact, pro_dir=pro_dir)
        Path(a.inline).parent.mkdir(parents=True, exist_ok=True)
        Path(a.inline).write_text(page, encoding="utf-8")
        print(f"wrote {a.inline}: {len(page.encode('utf-8')) / 1024 / 1024:.1f} MB, "
              f"jpeg q/width {level[0]}/{level[1]} (None = renders as written)")
    return 0


# -------------------------------------------------------------------- cli
def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tools.flip_sheet_renders",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("adopt", help="copy cells from an older cache (see `adopt`)")
    p.add_argument("--flags", nargs="+", required=True)
    p.add_argument("--fixtures", nargs="*")
    p.add_argument("--source", type=Path, required=True, help="the older cache")
    p.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    p.add_argument("--base", help="this cache's OFF engine: adopt only where OFF is byte-identical "
                                  "(omit for rows shown and not asked: copied as they are)")
    for name in ("run", "report"):
        p = sub.add_parser(name)
        p.add_argument("--flags", nargs="*", help="flag names (default: all in FLAGS)")
        p.add_argument("--fixtures", nargs="*", help="fixture slugs (default: FIXTURES)")
        p.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
        if name == "run":
            p.add_argument("--engine", help="a checkout root whose digitizer_core runs the cells")
            p.add_argument("--jobs", type=int, default=3)
            p.add_argument("--off-only", action="store_true", help="digitize only the OFF arms")
        else:
            p.add_argument("--out", type=Path, default=DEFAULT_DOC)
            p.add_argument("--renders", type=Path, default=DEFAULT_RENDERS)
            p.add_argument("--pro-renders", type=Path,
                           help="the pro's tiles: local only, never under docs/ (Kent 2026-10-27); "
                                "default pro_renders/<the --renders folder's name>")
            p.add_argument("--inline", type=Path,
                           help="also write ONE self-contained HTML (images as data URIs)")
            p.add_argument("--date", default=DATE, help="date in the inlined page's title")
            p.add_argument("--w5", action="store_true",
                           help="the wave-5 sheet: W5's flags in its order, each marked asked or shown")
            p.add_argument("--base", help="the sheet's OFF engine (short sha): rows on another say so")
            p.add_argument("--artifact", action="store_true",
                           help="write --inline without its document wrapper (an Artifact publish)")
            p.add_argument("--intro", nargs="*", help="extra opening paragraphs (HTML)")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    utf8_console(sys.stdout)
    a = parse_args(argv)
    return {"run": run_cmd, "report": report_cmd, "adopt": adopt_cmd}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
