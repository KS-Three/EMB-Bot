"""How much does the PRO agree with THEMSELVES? The scorecard's noise floor.

`scorecard.py` grades EMB-Bot on similarity to one professional file. That is
only a fair 0-100 scale if a professional would score ~100 against another
professional rendition of the same logo. Where the pro's own two files disagree,
the points between their agreement and 100 are not a gap any engine can close —
they measure the digitizer's discretion, not our deficit.

This instrument measures that ceiling per component, by feeding the scorecard
two of the pro's OWN files for one logo: file A as `pro`, file B as `ours`.
Everything downstream — registration, rasterisation, cell statistics, the
chance corrections — is the shipped scorecard, unmodified, so the numbers are
directly comparable to a real design's score.

Found this way on 2026-08-15, on `direction`: Hotel Fremont's cap and patch
files agree with each other at raw 0.564, while EMB-Bot agrees with the cap
version at 0.777. **The pro varies more between their own two renditions than we
vary from one of them.** Chance-corrected, 0.564 is 0.13 — so ~2.6 of
`direction`'s 20 points are reachable, and the component's weight overstates a
closable gap by roughly 8x.

## Pair selection, and why it is strict

`scorecard.py` registers by TRANSLATION only — it never rescales. So a pair must
be near the same physical size or the comparison measures a size mismatch
instead of a treatment difference. `MAX_SIZE_DELTA` enforces that, and any pair
outside it is reported and skipped rather than silently scored.

Pairs must also be the same ARTWORK. Two different logos for one customer would
measure nothing. The pairs below are same-customer, same-logo, same-size files
that differ only in the product they were digitized for — exactly the variation
this is trying to quantify.

## Read the results with these three caveats

1. **PES-vs-DST pairs are refused** (`has_real_colours`). DST carries no palette,
   so one side would be `GREYS` placeholders.

2. **DST-vs-DST pairs INFLATE `coverage`.** Both sides get the same fabricated
   `GREYS` ramp by block index, so the visible-colour-surface term always agrees
   and cannot penalise a real colour difference. `machine_hat_vs_lc` scoring
   coverage 1.00 is partly that artifact. Trust PES-vs-PES for `coverage`; the
   other components are colour-independent and unaffected.

3. **Some pairs are the SAME FILE saved twice.** `becker_hat_vs_chest_small`
   (8694 vs 8698 stitches) and `machine_hat_vs_lc` (13886 vs 13875) are one
   digitizing job reused for cap front and left chest, not two renditions. They
   are useful as a self-test — the scorecard SHOULD return ~100 on them, and does
   (96.0 and 99.9) — but they say nothing about a pro's discretion, and averaging
   them in overstates the ceiling. That reuse is itself a finding: it explains
   why `pro-parity-real-art-2026-08-15.md` §5b measured no hat-vs-left-chest
   difference in solidity. There was no second decision to differ.

Which leaves **two** genuinely independent, colour-comparable renditions today —
`hotel_hat_vs_patch` (75.2) and `machine_beanie_two_files` (83.6). Growing that
sample needs scale-normalised registration in `scorecard.py`, because every other
same-logo PES pair in the file set is 4-17% apart in width and `MAX_SIZE_DELTA`
correctly refuses it.

Usage:
    PRO_PARITY_OUT=<out> python selfconsistency.py
    python scorecard.py <out>/selfconsistency/*/
"""
import json
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pystitch

import prep_all

ROOT = Path(os.environ.get("PRO_PARITY_ROOT", r"G:/My Drive/EMB-Bot/Embroidery Files"))
prep_all.ROOT = ROOT


def has_real_colours(path):
    """Does this file carry a thread palette, or will `decode()` fabricate one?

    DST carries no colour at all, so `prep_all.decode` substitutes its `GREYS`
    placeholder ramp. Comparing a PES's real palette against that ramp makes
    `coverage`'s visible-colour-surface term report a disagreement that is an
    artifact of the FORMAT, not of either digitizer's choices — measured
    2026-08-15 on `toat_beanie_two_files`, where two files 4 stitches apart
    scored coverage 0.50 while every other component read 1.00. A pair must
    therefore be colour-comparable on both sides or not scored at all.
    """
    threads = pystitch.read(str(path)).threadlist
    return bool(threads) and not all(
        (t.get_red(), t.get_green(), t.get_blue()) == (0, 0, 0) for t in threads
    )

# Fractional width difference above which a pair is skipped. 3%: tight enough
# that translation-only registration stays honest, loose enough to admit the
# hat/left-chest pairs a pro sizes to the same nominal width.
MAX_SIZE_DELTA = 0.03

# (pair name, file A, file B, what varies between them)
PAIRS = [
    ("hotel_hat_vs_patch",
     "Hotel Fremont/Hotel Hat/HOTEL FREMONT HAT.PES",
     "Hotel Fremont/Hotel Patch/HOTEL FREMONT .PES",
     "cap front vs twill patch"),
    ("becker_hat_vs_chest_small",
     "Becker Marine/Becker Hat & Polo Small/Becker Hat Small/beckers logo hat 2 A.PES",
     "Becker Marine/Becker Hat & Polo Small/Becker Chest Small/beckers logo LC 2 A.PES",
     "cap front vs left chest, same nominal size"),
    ("machine_hat_vs_lc",
     "To a T Machine/Machine HAT.DST",
     "To a T Machine/Machine LC.DST",
     "cap front vs left chest"),
    ("machine_beanie_two_files",
     "To a T_Becker Beanies/Machine beanie.PES",
     "To a T Machine/Machine beanie E-1 (1).PES",
     "two beanie files for one logo"),
    ("toat_beanie_two_files",
     "To a T_Becker Beanies/Machine beanie.PES",
     "To a T_Becker Beanies/To a T Beanie.DST",
     "two beanie files, same folder"),
]


def write_side(blocks, breaks, threads, outdir, which):
    """Write `<which>_stitches.csv` + `<which>_blocks.json` the way the
    scorecard expects. Row k is the k'th STITCH; `trim` is 1 exactly when a
    TRIM / COLOR_CHANGE / STOP stands between this stitch and the one before,
    `jump` marks a needle-up float — identical to `prep_all.main`'s pro writer,
    so both sides of this comparison are produced by one rule."""
    with open(outdir / f"{which}_stitches.csv", "w") as f:
        f.write("block,run,trim,jump,x_mm,y_mm\n")
        for i, runs in enumerate(blocks):
            for ri, (r, kind) in enumerate(zip(runs, breaks[i])):
                t = 1 if kind in ("trim", "color") else 0
                j = 1 if kind == "jump" else 0
                for k, (x, y) in enumerate(r):
                    f.write(f"{i},{ri},{t if k == 0 else 0},"
                            f"{j if k == 0 else 0},{x:.2f},{y:.2f}\n")
    # Only `block` and `rgb` are read (scorecard.colour_groups), so this is the
    # complete contract, not a reduced stand-in.
    (outdir / f"{which}_blocks.json").write_text(json.dumps(
        [{"block": i, "rgb": list(threads[i % len(threads)])}
         for i in range(len(blocks))], indent=1))


def main():
    out = Path(os.environ["PRO_PARITY_OUT"]) / "selfconsistency"
    out.mkdir(parents=True, exist_ok=True)
    done = 0
    for name, rel_a, rel_b, varies in PAIRS:
        pa, pb = prep_all.find_file(rel_a), prep_all.find_file(rel_b)
        if pa is None or pb is None:
            print(f"[{name}] SKIP - file not found")
            continue
        ca, cb = has_real_colours(pa), has_real_colours(pb)
        if ca != cb:
            print(f"[{name}] SKIP - colour-incomparable: {pa.suffix} carries "
                  f"{'real' if ca else 'no'} thread colours, {pb.suffix} carries "
                  f"{'real' if cb else 'no'}. `coverage` would score the format "
                  f"difference (see has_real_colours)")
            continue
        ba, ka, ta, bda, _, _ = prep_all.decode(pa)
        bb_, kb, tb, bdb, _, _ = prep_all.decode(pb)
        wa, wb = bda[2] - bda[0], bdb[2] - bdb[0]
        delta = abs(wa - wb) / max(wa, wb)
        if delta > MAX_SIZE_DELTA:
            print(f"[{name}] SKIP - {wa:.1f} vs {wb:.1f} mm is {delta:.1%} apart "
                  f"(cap {MAX_SIZE_DELTA:.0%}); translation-only registration "
                  f"would score the size difference")
            continue
        d = out / name
        d.mkdir(parents=True, exist_ok=True)
        write_side(ba, ka, ta, d, "pro")
        write_side(bb_, kb, tb, d, "ours")
        (d / "pair.json").write_text(json.dumps({
            "pair": name, "varies": varies,
            "a": {"file": str(pa), "width_mm": round(wa, 1),
                  "stitches": sum(len(p) for r in ba for p in r), "blocks": len(ba)},
            "b": {"file": str(pb), "width_mm": round(wb, 1),
                  "stitches": sum(len(p) for r in bb_ for p in r), "blocks": len(bb_)},
            "size_delta": round(delta, 4),
        }, indent=1))
        print(f"[{name}] {wa:.1f} vs {wb:.1f} mm ({delta:.1%})  "
              f"{sum(len(p) for r in ba for p in r)} vs "
              f"{sum(len(p) for r in bb_ for p in r)} stitches  -- {varies}")
        done += 1
    # scorecard.py reads manifest.json from the design dirs' parent for its
    # authoritative trim re-decode; both sides here already carry a `trim`
    # column, so an empty manifest is correct rather than merely tolerated.
    (out / "manifest.json").write_text("[]")
    print(f"\n{done}/{len(PAIRS)} pairs written to {out}")
    print(f"score with:  python {Path(__file__).parent / 'scorecard.py'} {out}/*/")


if __name__ == "__main__":
    main()
