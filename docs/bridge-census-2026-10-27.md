# Bridge through every pro census (2026-10-27)

**Measured on main `8341d1f766b03b8075c18979b6845d3866a66d50`** (`origin/main` at 08:14 on 2026-10-27, merged into the lane before the digitize). Numbers only: no pro file, crop or render is committed. Bridge hat and left chest (LC) each digitized **once** with the Studio's request at the pro's width (`tools.small_text_floor_census digitize`, which is `border_census.digitize_one`), then read beside the pro's `BRIDGE LOGO HAT` / `LC` DST by one reader per row, each file in its own frame. Nothing in `digitizer_core/`, `src/` or `tools/` changed.

**Defaults ON on this head that bear on Bridge:** `script_strokes` (#1136, one satin column per pen stroke), `small_text_reset_grow_away` (#1127), `white_keyline_art_recipe` (the MFab gate: ON only on MFab-type art, so inert here), `border_by_size`, `border_from_outline` and its line-art guard, `lettering_columns_corner_fold`, `lettering_columns_inside_stagger`, `lettering_columns_text_lean`, `fine_bars_satin`, `outline_loop_mitre`, `sew_enclosed_white`, `small_text_bay_mouth`, `tie_in_off`, `small_text_cap_reach_edges`. **OFF:** `cut_every_jump`, `silhouette_underfill` (+ `_panels`), `keyline_loop_chain` (rides the MFab gate), `enclosed_white_keyline`, `keyline_fold_slivers`, `monoline_script_satin`, `bean_ink_outlined_letters`, `lettering_columns_apex_cut`, `lettering_columns_italic_lean`, `pro_measured_values`. The OFF rules are read as premise checks (does the pro's Bridge file do what the rule assumes, and how far is ours); no OFF arm was digitized.

**What Bridge is.** The pro's art is redrawn: no bowl, no waves, a black wheel, a yellow field, orange text, a blue anchor, a red script word. Ours traces the customer art (bowl, waves, anchor in the waves) and quantizes its blue text into teal, green and yellow regions, so the two files differ in content by design. Colour blocks, by geometry: pro hat/LC 0 field, 1 wheel, 2 text, 3 anchor, 4 script; ours hat 0 yellow (field fill + yellow satin pieces), 1 teal, 2 black (wheel, bowl), 3 red (script), 4 brown, 5 green; ours LC 0 yellow, 1 black, 2 red (script), 3 brown, 4 teal, 5 light yellow.

| | ours hat | ours LC | pro hat | pro LC |
|---|---|---|---|---|
| width x height, mm | 62.5 x 62.1 | 75.6 x 76.1 | 63.3 x 63.1 | 76.6 x 76.5 |
| needle-down stitches | 9,419 | 14,861 | 6,650 | 8,535 |
| TRIM commands | 24 | 32 | 20 | 20 |
| colour changes | 5 | 5 | 4 | 4 |
| digitize wall time, s | 73.9 | 69.5 | - | - |

**Provenance.** The hat digitize ran 08:16:04 to 08:17:32 and the LC 08:21:12 to 08:22:30, each under one CPU slot take. A stale duplicate of the hat job (a slot waiter that outlived its stop) was running into the same cache and was killed at about 08:17:50. The log holds one completed hat run, and the cached DST and JSON agree (6 blocks, 5 colour changes), but a second hat digitize to confirm byte identity was not run (CPU busy).

The pro's 20th TRIM sits before the closing JUMPs, so 19 of his are needle-up moves between two stitches (`trim_classes` and the move reader read 19). Cross-check against `docs/pro-baseline-2026-10-27.md` (main `2c6b656c`, before `script_strokes` went ON): ours 9,608 / 15,278 stitches and 24 / 32 trims there; the trims match, the stitches fall 2% / 3%.

## The table

Verdict: **AGREES** when the pro's Bridge file shows what the rule assumes; **CONTRADICTS** when it shows the opposite; **N/A** when the rule does not reach Bridge. Where the pro agrees but ours sits far from him, the reach gap is in the reading, not the verdict.

| # | Rule (flag) | Reading (one reader, both files) | Ours hat / LC | Pro hat / LC | Verdict |
|---|---|---|---|---|---|
| 1 | corner fold (`lettering_columns_corner_fold` ON) | `pro_corner_folds.folds` over text and anchor runs up to 12 mm; folds (per run) | 2 (0.08) / 20 (0.74) | 35 (2.50) / 39 (2.79) | **AGREES**. The pro folds Ls (arc median 2.44 / 2.24 mm, width ratio 1.08 / 1.07); ours reaches 0.06x / 0.51x of his count |
| 2 | inside stagger (`lettering_columns_inside_stagger` ON) | `inside_stagger.read` zones, median depth rel, piled ends | 0 zones / 9 zones, rel 0.18, pile 0.0 | 37 zones, rel 0.20, pile 0.0 / 31 zones, rel 0.20, pile 0.0 | **AGREES**. His depth is 0.20 of the cross with no pile; ours LC reads 0.18 and 0.0; the hat has no zone to read |
| 3 | text lean (`lettering_columns_text_lean` ON) | script word, the only lettering at 10 mm or more, `letter_pieces` on its block alone: median cross angle off the text line, flat share (`lean_flat`) | 43.1 deg, 0.06 / 49.9 deg, 0.05 | 37.6 deg, 0.19 / 35.2 deg, 0.20 | **N/A**. Block text is 4 to 5.5 mm, under the 10 mm band; the script word is one the letter door refuses and `script_strokes` takes it first, so `text_lean` never sees it. Neither file squares its crosses to the line |
| 4 | border by size (`border_by_size` ON) | closed shapes at 6 mm or more across, ringed; all shapes of 1 mm2 or more, ringed | 6 mm+: 1 of 1 / 1 of 1; all: 3 / 10 | 6 mm+: 0 of 1 / 0 of 1; all: 2 / 1 | **CONTRADICTS**. Both fields (8.2 and 10.0 mm) get a 1.6 mm ring that the pro sews bare; ours and the pro ring the same shape in 0 of 64 (kappa -0.03 [raw 0.78]) |
| 5 | border from outline and its line-art guard (`border_from_outline`, `_line_art_guard` ON) | `outline_census measure`, pooled over both files (64 shapes), guard off then on | guard off: 5 outline bodies ring, 0 agree, kappa -0.05 [raw 0.887]; guard on: 0 ring, kappa 0.00 [raw 0.969] | pro rings 2 shapes (hat 1, LC 1) with no outline | **AGREES**. The guard reads both outlines as line art (fill share 0.34 / 0.09, dropped 0.066 / 0.045) and the five false rings go. Confirm only |
| 6 | small-text floor (`small_text_cap_*`, floor 4.0 mm, `small_text_cap_reach_edges` ON) | median height of letter-sized sewn pieces (3 to 8 mm), n | 4.25 mm (12) / 4.45 mm (14) | 5.00 mm (14) / 5.47 mm (14) | **AGREES**. The art's text is 2.0 to 2.3 mm (hat) and 2.5 to 2.8 mm (LC); both sew it at 4 to 5.5 mm; ours sits 0.75 / 1.0 mm under him |
| 7 | fine bars satin (`fine_bars_satin` ON) | ring runs in ours.json by aspect (rule needs 6.0 or more, or under 0.5 mm across) | 6 ring runs / 19, max aspect 2.3 (two travel hops 3.3 and 3.5, not shapes) | not read: nothing of his to pair with a bar | **N/A**. No free-standing thin ink bar in Bridge's trace; every small run is a blob (aspect 1.0 to 2.3) |
| 8 | outline loop mitre (`outline_loop_mitre` ON) | needle-down runs that close on themselves, 5 mm or more across | 0 / 1 (one 83-point run, 8.5 x 8.9 mm) | 0 / 0 | **N/A**. The reader finds no outline loop with corners to read in either file; Bridge's rings are a wheel and a bowl arc. Corners were not measured on the loops in `ring_runs` (the DST does not tag them) |
| 9 | garment sizes (`proSized`, the Studio's box) | the pro's size beside the pro's garment box (`garment_size_census`) | box 113.5 x 64.0 / box 96.0 x 64.5 | 63.3 x 63.1, box +1.1% / 76.6 x 76.5, box -15.8% | **hat AGREES, LC CONTRADICTS**. The LC box is the census's named miss: a design fitted to its 64.5 mm height sews Bridge LC 12.1 mm under his 76.6 mm. (Both files here were digitized at his width, so ours is not boxed) |
| 10 | sew enclosed white (`sew_enclosed_white` ON) | white regions in ours.json; white thread in either file | 0 / 0 | none (5 colours) | **N/A**. No white anywhere in Bridge's art or palette |
| 11 | bay mouth (`small_text_bay_mouth` ON) | `small_text.bay_mouths` over the same 3 to 8 mm pieces: mouths, median mm, (under 0.25 / under 0.51) | 12, 0.50 (0 / 7) / 17, 0.40 (0 / 12) | 26, 0.40 (6 / 21) / 23, 0.44 (2 / 15) | **AGREES**. Ours shuts 0 of 29 mouths; he keeps 41 of 49 at 0.25 or more. His median (0.40 / 0.44) sits under the rule's 0.51 (the census median, n 18), inside its 0.27 to 1.20 range |
| 12 | tie-in off (`tie_in_off` ON) | run starts read locked: first four segments, three under 1 mm, a revisit within 0.15 mm | 3 of 44 / 4 of 52 | 0 of 24 / 1 of 24 | **AGREES**. The pro locks 1 of 48 starts (the corpus read 1 of 68); ours still reads 7 of 96 locked, a residual |
| 13 | cut every jump (`cut_every_jump` OFF, premise) | needle-up moves between two stitches, cut or uncut | 38 moves, 24 cut, 14 uncut (22.8 mm, longest 2.98) / 46, 32 cut, 14 uncut (21.5 mm, longest 2.78) | 19 moves, 19 cut, 0 uncut / 19, 19, 0 | **AGREES**. The pro leaves no needle-up move uncut; ours leaves 14 per file |
| 14 | silhouette underfill (`silhouette_underfill` OFF, premise) | `layer_census`: contained pieces sewn ON, OFF, or part on their ground | on 11, off 0, partial 1 / on 13, off 1, partial 0 | on 7, off 0, partial 0 / on 10, off 0, partial 0 | **AGREES**. The pro sews 17 of 17 contained pieces on their ground; ours already does 24 of 26 with the rule OFF |

**CONTRADICTS rows: 4 (border by size, both files) and 9 (LC only).** Row 4 is also in the rule's own comment (`config.py`: "Bridge's and Gaulke's bare"). Row 12's residual and row 13's 14 uncut moves are gaps in ours, not contradictions.

## Also measured (not rules, same readers)

| Reading | Ours hat / LC | Pro hat / LC |
|---|---|---|
| trims by class, `trim_classes` (colour, under later thread, on work, bare) | 0 / 1 / 19 / 4 of 24; 0 / 1 / 27 / 4 of 32 | 0 / 0 / 19 / 0 of 19; 0 / 0 / 19 / 0 of 19 |
| needle-up moves between stitches | 38 / 46 | 19 / 19 |
| satin columns with no underlay beneath (`pro_satin_underlay --per-file`) | 9 of 81 (11.1%) / 4 of 153 (2.6%) | 2 of 103 (1.9%) / 2 of 113 (1.8%) |
| fill row turns (`fill_turns`), count, along median mm | 641, 0.693 / 975, 0.689 | 177, 0.6 / 215, 0.7 |
| enclosed counters in the 3 to 8 mm text pieces (`bays_read`) | 0 / 0 | 6 / 7 |
| script word, `letter_pieces` on the script's block alone: pieces, turned, patches, max cross mm, crosses | 12, 7, 4, 5.19, 509 / 12, 8, 3, 5.39, 579 | 18, 9, 2, 2.50, 619 / 14, 3, 1, 2.94, 860 |

## Re-run

The pro files are gitignored third-party files. Mirror them under any folder `ROOT` (never commit it): `ROOT/Bridge Bar/Bridge Bar Embroidery Files/BRIDGE LOGO HAT.{DST,PES}` and `LC.{DST,PES}`, plus `ROOT/Bridge Bar/Bridge Bar Logo.jpg` (a copy of `digitizer/testdata/photo/logo_bridge_bar.jpg`); `border_census.PAIRS` finds them there. One digitize each, one CPU slot take each (`cpu.lock` or `cpu.lock2`, `holder.txt`, released after):

```
cd digitizer
ROOT=/path/to/pro-mirror; CACHE=/path/to/bridge-cache
export PRO_PARITY_ROOT="$ROOT"; PRO="$ROOT/Bridge Bar/Bridge Bar Embroidery Files"
python -m tools.small_text_floor_census digitize --cache $CACHE bridge_hat
python -m tools.small_text_floor_census digitize --cache $CACHE bridge_lc
# rows 1, 2: pop_read.py FILE BLOCKS  (ours hat 0,1,4,5; ours LC 0,3,4,5; pro 2,3)
# row 3: lp_block.py FILE BLOCK 0     (script: ours hat 3, ours LC 2, pro 4)
# row 4, 5:
python -m tools.border_census table --cache $CACHE --only bridge_hat bridge_lc --jobs 1 --table-out OUT.txt
python -m tools.outline_census measure --cache $CACHE --only bridge_hat bridge_lc            # guard off
python -m tools.outline_census measure --cache $CACHE --only bridge_hat bridge_lc --line-art-guard
# row 6, 11: bays_pop.py FILE BLOCKS  (same blocks as rows 1, 2)
# row 8: loops_read.py FILE...        row 12, 13: moves_ties.py FILE...
python -m tools.trim_classes $CACHE/bridge_hat/ours.dst "$PRO/BRIDGE LOGO HAT.DST"
python -m tools.layer_census $CACHE/bridge_hat/ours.dst "$PRO/BRIDGE LOGO HAT.DST"            # row 14
python -m tools.garment_size_census                                                          # row 9
python -m tools.fill_turns FILE...; python -m tools.pro_satin_underlay --per-file FILE...
```

The `.py` drivers are in the appendix; they import `tools.*` and `digitizer_core.*` from `digitizer/` (run them from there with `python -I`) and add nothing to the repo. Row 5's kappa is `outline_census`'s own; row 4's is Cohen's kappa over the `border_census` table's (a) 13 and (b) 1 rows among 64 shapes. Per gate 4 every agreement here is chance-corrected with the raw share in brackets.

## Appendix: drivers

`moves_ties.py` (rows 12, 13):

```python
import json, math, sys
import pystitch

M = pystitch.COMMAND_MASK

def read(path):
    pat = pystitch.read(str(path))
    st = [(x / 10.0, y / 10.0, c & M) for x, y, c in pat.stitches]
    moves, starts, pend, last, run_pts, cc = [], [], None, None, [], 0
    def close_run():
        nonlocal run_pts
        if run_pts: starts.append(run_pts)
        run_pts = []
    for x, y, c in st:
        if c == pystitch.STITCH:
            if pend is not None:
                cmds, frm = pend
                if "COLOR" not in cmds and frm is not None:
                    moves.append({"cut": "TRIM" in cmds, "mm": math.hypot(x - frm[0], y - frm[1])})
                pend = None
            run_pts.append((x, y)); last = (x, y)
        elif c in (pystitch.JUMP, pystitch.TRIM, pystitch.COLOR_CHANGE, pystitch.STOP):
            if pend is None:
                close_run(); pend = [set(), last]
            pend[0].add({pystitch.JUMP: "JUMP", pystitch.TRIM: "TRIM",
                         pystitch.COLOR_CHANGE: "COLOR", pystitch.STOP: "COLOR"}[c])
            cc += c == pystitch.COLOR_CHANGE
        elif c == pystitch.END:
            break
    close_run()
    return moves, starts, cc

def locked(pts):   # first four segments: three under 1 mm, and a revisit within 0.15 mm
    if len(pts) < 6: return False
    seg = [math.hypot(pts[i+1][0]-pts[i][0], pts[i+1][1]-pts[i][1]) for i in range(4)]
    if sum(s < 1.0 for s in seg) < 3: return False
    return any(math.hypot(pts[i][0]-pts[j][0], pts[i][1]-pts[j][1]) < 0.15
               for i in range(2, 5) for j in range(i))

for p in sys.argv[1:]:
    moves, starts, cc = read(p)
    unc = [m for m in moves if not m["cut"]]
    print(p.split("/")[-1], json.dumps({"needle_up_moves": len(moves), "cut": len(moves) - len(unc),
        "uncut": len(unc), "uncut_mm_total": round(sum(m["mm"] for m in unc), 1),
        "uncut_max_mm": round(max([m["mm"] for m in unc], default=0.0), 2),
        "colour_changes": cc, "run_starts": len(starts), "locked_starts": sum(locked(s) for s in starts)}))
```

`pop_read.py` (rows 1, 2; `python -I pop_read.py FILE.dst BLOCKS [MAX_MM=12]`, run from `digitizer/`):

```python
import json, os, sys
sys.path.insert(0, os.getcwd())
import numpy as np
from tools import inside_stagger as ins, pro_corner_folds as pcf, small_text_columns as stc

path, blocks = sys.argv[1], {int(x) for x in sys.argv[2].split(",")}
mx = float(sys.argv[3]) if len(sys.argv) > 3 else 12.0
runs = []
for bi, b in enumerate(stc.read_blocks(path)):
    if bi not in blocks:
        continue
    for r in stc._runs(b):
        w = np.array(r).max(0) - np.array(r).min(0)
        if max(w) <= mx:
            runs.append(r)
fo = [f for r in runs for f in pcf.folds(r)]
zr = ins.read(runs) if runs else []
rs = [max(f["w_before"], f["w_after"]) / min(f["w_before"], f["w_after"]) for f in fo if f["w_before"] and f["w_after"]]
print(json.dumps({"runs": len(runs), "folds": len(fo),
    "arc_med": round(float(np.median([f["arc"] for f in fo])), 2) if fo else None,
    "wratio_med": round(float(np.median(rs)), 2) if rs else None,
    "zones": len(zr), "zone_summary": ins.summary(zr) if zr else None}, default=float))
```

`bays_read.py` and `bays_pop.py` (rows 6, 11; `python -I bays_pop.py FILE.dst BLOCKS`, both files in one folder):

```python
# bays_read.py
import os, sys
sys.path.insert(0, os.getcwd())
from digitizer_core.small_text import bay_mouths
from tools import small_text_columns as stc

def read(path, h_min=3.0, h_max=8.0):
    out = []
    for p in stc.pieces(stc.read_blocks(path)):
        h = p["y1"] - p["y0"]
        if h_min <= h <= h_max:
            rows = bay_mouths(p["mask"], stc.PPM)
            out.append({"block": p["block"], "h": round(h, 2),
                        "mouths": [round(r["mouth_mm"], 2) for r in rows if r["mouth_mm"] > 0],
                        "enclosed": sum(1 for r in rows if r["mouth_mm"] == 0)})
    return out
```

```python
# bays_pop.py
import json, os, sys
sys.path.insert(0, os.getcwd()); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, bays_read
blocks = {int(x) for x in sys.argv[2].split(",")}
rows = [r for r in bays_read.read(sys.argv[1]) if r["block"] in blocks]
m = sorted(x for r in rows for x in r["mouths"]); h = [r["h"] for r in rows]
print(json.dumps({"pieces": len(rows), "with_bay": sum(1 for r in rows if r["mouths"]), "mouths": len(m),
    "mouth_median": round(float(np.median(m)), 2) if m else None,
    "under_0.25": sum(x < 0.25 for x in m), "under_0.51": sum(x < 0.51 for x in m),
    "enclosed": sum(r["enclosed"] for r in rows),
    "h_median": round(float(np.median(h)), 2) if h else None}))
```

`lp_block.py` (row 3 and the script line above; `python -I lp_block.py FILE.dst BLOCK [MIN_HEIGHT_MM]`):

```python
import json, os, sys
sys.path.insert(0, os.getcwd())
from pathlib import Path
from tools import letter_pieces as lp

path, block = Path(sys.argv[1]), int(sys.argv[2])
min_h = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
_runs = lp.runs_of
lp.runs_of = lambda p: [r for r in _runs(p) if r["block"] == block]   # one colour block, the tool's own reader otherwise
res = lp.read(path)
res["letters"] = [L for L in res["letters"] if L["bbox"][3] - L["bbox"][1] >= min_h]
print(json.dumps({"block": block, "summary": lp.summary(res),
                  "measures": lp.word_measures(res["letters"]) if res["letters"] else {}}))
```

`loops_read.py` (row 8; a run that ends within 1.0 mm of where it began, 5 mm or more across):

```python
import json, math, os, sys
sys.path.insert(0, os.getcwd())
import numpy as np
from tools import small_text_columns as stc

for p in sys.argv[1:]:
    rows = []
    for bi, b in enumerate(stc.read_blocks(p)):
        for r in stc._runs(b):
            a = np.array(r); w = a.max(0) - a.min(0)
            if len(a) >= 30 and min(w) >= 5 and math.hypot(*(a[0] - a[-1])) <= 1.0:
                rows.append({"block": bi, "pts": len(a), "box": [round(float(v), 1) for v in w]})
    print(os.path.basename(p), json.dumps({"loops": len(rows), "rows": rows}))
```
