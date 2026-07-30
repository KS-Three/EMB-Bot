#!/usr/bin/env python
"""Generate digitizer_core/chart_data/ from the repo's .gpl thread charts.

Source: ../tools/palettes/*.gpl — manufacturer color charts redistributed by
the Ink/Stitch project (github.com/inkstitch/inkstitch, palettes/, snapshot
e7108fd). Thread color numbers and their RGB approximations are factual data;
each brand name remains a trademark of its manufacturer and is used only to
identify the corresponding thread line (owner ruling 2026-07-29: facts-doctrine
data is kept in both products).

Brand ids MUST match `tools/build-threads.mjs`, because Studio sends its stored
`embstudio:threadPalette` preference straight to the service. The id rule and
the four legacy overrides below are mirrored from that script;
tests/test_charts.py asserts the two agree rather than trusting this comment.

Run from digitizer/:  .venv/Scripts/python tools/gen_charts.py
Deterministic output: brands sorted by id, entries in file order, LF endings,
so the generated files are byte-identical regardless of source line endings.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from digitizer_core.gpl import parse_gpl  # noqa: E402

PALETTE_DIR = HERE.parent.parent / "tools" / "palettes"
OUT_DIR = HERE.parent / "digitizer_core" / "chart_data"

# POLICY (Kent, 2026-07-29 blueprint grill): no thread charts from companies
# that sell or make embroidery software/machines — we don't carry a
# competitor's brand inside the product. Enforced here (not just by file
# deletion) so a wholesale re-copy from upstream can't silently reintroduce
# them. Mirrors POLICY_EXCLUDED in tools/build-threads.mjs.
POLICY_EXCLUDED = {
    "InkStitch Brother Country.gpl",      # Brother: machines + PE-Design
    "InkStitch Brother Embroidery.gpl",   # Brother: machines + PE-Design
    "InkStitch Janome.gpl",               # Janome: machines + software
    "InkStitch Viking Palette.gpl",       # Husqvarna Viking: machines + software
    "InkStitch Floriani Polyester.gpl",   # RNK: Floriani embroidery software
    "InkStitch Hemingworth.gpl",          # DIME: embroidery software
    "InkStitch RAL.gpl",                  # RAL is a paint standard, not thread
}

# The four charts that shipped before the full sweep keep their original
# ids/labels so a stored app-wide preference keeps resolving.
LEGACY = {
    "InkStitch Isacord Polyester.gpl": ("isacord", "Isacord Polyester 40"),
    "InkStitch Madeira Polyneon.gpl": ("polyneon", "Madeira Polyneon 40"),
    "InkStitch Madeira Rayon.gpl": ("madeira-rayon", "Madeira Rayon 40"),
    "InkStitch Robison-Anton Polyester.gpl": ("robison-anton", "Robison-Anton Polyester 40"),
}

# Smallest legitimate chart shipped is 15 colors (Simthread Glow In The Dark);
# under 10 means the file format changed on us — fail loudly rather than
# silently shipping a gutted chart.
MIN_ENTRIES = 10


def label_for(filename: str) -> str:
    return re.sub(r"^InkStitch\s+", "", filename).removesuffix(".gpl")


def id_for(label: str) -> str:
    return re.sub(r"^-+|-+$", "", re.sub(r"[^a-z0-9]+", "-", label.lower()))


def main() -> None:
    if not PALETTE_DIR.is_dir():
        raise SystemExit(f"palette dir not found: {PALETTE_DIR}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in OUT_DIR.glob("*.json"):
        stale.unlink()

    index: list[dict] = []
    seen: set[str] = set()
    total = 0

    for path in sorted(PALETTE_DIR.glob("*.gpl")):
        if path.name in POLICY_EXCLUDED:
            print(f"EXCLUDED (policy): {path.name}")
            continue
        brand_id, label = LEGACY.get(path.name, (None, None))
        if brand_id is None:
            label = label_for(path.name)
            brand_id = id_for(label)
        if brand_id in seen:
            raise SystemExit(f'duplicate brand id "{brand_id}" from {path.name}')
        seen.add(brand_id)

        entries = parse_gpl(path.read_text(encoding="utf-8"))
        if len(entries) < MIN_ENTRIES:
            raise SystemExit(f"{path.name}: parsed only {len(entries)} entries — format change?")

        (OUT_DIR / f"{brand_id}.json").write_text(
            json.dumps(
                {
                    "id": brand_id,
                    "label": label,
                    "threads": [[num, name, list(rgb)] for num, name, rgb in entries],
                },
                separators=(",", ":"),
            ),
            encoding="utf-8",
            newline="\n",
        )
        index.append({"id": brand_id, "label": label, "count": len(entries)})
        total += len(entries)

    index.sort(key=lambda b: b["id"])
    (OUT_DIR / "index.json").write_text(
        json.dumps(index, indent=1), encoding="utf-8", newline="\n"
    )

    print(f"\n{len(index)} brands, {total} colors -> {OUT_DIR}")


if __name__ == "__main__":
    main()
