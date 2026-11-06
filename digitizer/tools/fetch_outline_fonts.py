#!/usr/bin/env python
"""Fetch the outline-font starter set from google/fonts at a PINNED commit.

Writes `digitizer_core/outline_fonts/<family>/<file>.ttf` + `OFL.txt` and
regenerates `digitizer_core/outline_fonts/fonts.json` (the registry
`digitizer_core.outline_fonts` reads). Every file's sha256 is recorded, so a
re-run on another machine either reproduces the set byte for byte or says
which file moved.

    .venv/Scripts/python tools/fetch_outline_fonts.py            # fetch + write
    .venv/Scripts/python tools/fetch_outline_fonts.py --check    # verify only

Licence rule (same as tools/build-embf.mjs's ALLOWED_LICENSES): OFL-1.1 only
here — every family below lives under google/fonts `ofl/`, is shipped
UNMODIFIED (OFL's Reserved Font Name clause binds Modified Versions only;
docs/font-license-audit-2026-07-31.md item 10), and its OFL.txt rides along.
Apache families (Roboto's old home, Permanent Marker) are deliberately out
until Kent widens the list.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "digitizer_core" / "outline_fonts"

# google/fonts main, 2026-11-06. Bump deliberately: a font's outlines change
# with its upstream version, and a changed outline is a changed stitch plan.
COMMIT = "86aced91de05cd4f96a06838124cca45be337b2b"
RAW = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}/ofl"

# (family dir, display family, group, [(file, weight name, weight, variable)])
# A variable file is listed once and the registry exposes its Regular (400)
# and Bold (700) instances; a static family lists each file it ships.
FAMILIES = [
    ("montserrat", "Montserrat", "Sans", [("Montserrat[wght].ttf", None, None, True)]),
    ("opensans", "Open Sans", "Sans", [("OpenSans[wdth,wght].ttf", None, None, True)]),
    ("roboto", "Roboto", "Sans", [("Roboto[wdth,wght].ttf", None, None, True)]),
    ("poppins", "Poppins", "Sans", [("Poppins-Regular.ttf", "Regular", 400, False),
                                    ("Poppins-Bold.ttf", "Bold", 700, False)]),
    ("oswald", "Oswald", "Sans", [("Oswald[wght].ttf", None, None, True)]),
    ("nunito", "Nunito", "Sans", [("Nunito[wght].ttf", None, None, True)]),
    ("fredoka", "Fredoka", "Sans", [("Fredoka[wdth,wght].ttf", None, None, True)]),
    ("playfairdisplay", "Playfair Display", "Serif", [("PlayfairDisplay[wght].ttf", None, None, True)]),
    ("lora", "Lora", "Serif", [("Lora[wght].ttf", None, None, True)]),
    ("ebgaramond", "EB Garamond", "Serif", [("EBGaramond[wght].ttf", None, None, True)]),
    ("librebaskerville", "Libre Baskerville", "Serif", [("LibreBaskerville[wght].ttf", None, None, True)]),
    ("lobster", "Lobster", "Script", [("Lobster-Regular.ttf", "Regular", 400, False)]),
    ("pacifico", "Pacifico", "Script", [("Pacifico-Regular.ttf", "Regular", 400, False)]),
    ("dancingscript", "Dancing Script", "Script", [("DancingScript[wght].ttf", None, None, True)]),
    ("greatvibes", "Great Vibes", "Script", [("GreatVibes-Regular.ttf", "Regular", 400, False)]),
    ("kaushanscript", "Kaushan Script", "Script", [("KaushanScript-Regular.ttf", "Regular", 400, False)]),
    ("bebasneue", "Bebas Neue", "Display", [("BebasNeue-Regular.ttf", "Regular", 400, False)]),
    ("anton", "Anton", "Display", [("Anton-Regular.ttf", "Regular", 400, False)]),
    ("alfaslabone", "Alfa Slab One", "Display", [("AlfaSlabOne-Regular.ttf", "Regular", 400, False)]),
    ("bangers", "Bangers", "Display", [("Bangers-Regular.ttf", "Regular", 400, False)]),
    ("graduate", "Graduate", "Display", [("Graduate-Regular.ttf", "Regular", 400, False)]),
]

VARIABLE_INSTANCES = [("Regular", 400), ("Bold", 700)]


def _slug(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as r:  # noqa: S310 - pinned GitHub raw URL
        data = r.read()
    if len(data) < 1000:
        raise SystemExit(f"{url}: {len(data)} bytes — not a font/licence file")
    dest.write_bytes(data)


def build_registry() -> list[dict]:
    fonts: list[dict] = []
    for family_dir, family, group, files in FAMILIES:
        lic = f"{family_dir}/OFL.txt"
        for fname, wname, weight, variable in files:
            rel = f"{family_dir}/{fname}"
            entry_base = {
                "family": family,
                "group": group,
                "file": rel,
                "variable": variable,
                "licenseId": "OFL-1.1",
                "licenseFile": lic,
                "source": f"https://github.com/google/fonts/tree/{COMMIT}/ofl/{family_dir}",
                "sha256": _sha256(OUT / rel),
            }
            instances = VARIABLE_INSTANCES if variable else [(wname, weight)]
            for iname, iweight in instances:
                name = family if iname == "Regular" else f"{family} {iname}"
                fonts.append({
                    "key": _slug(name),
                    "name": name,
                    "weight": iweight,
                    "style": iname,
                    **entry_base,
                })
    return fonts


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify files against fonts.json, fetch nothing")
    args = ap.parse_args()

    if args.check:
        reg = json.loads((OUT / "fonts.json").read_text(encoding="utf-8"))
        bad = 0
        for f in reg["fonts"]:
            p = OUT / f["file"]
            if not p.exists() or _sha256(p) != f["sha256"]:
                print("MISMATCH", f["file"]); bad += 1
            if not (OUT / f["licenseFile"]).exists():
                print("MISSING LICENCE", f["licenseFile"]); bad += 1
        print(f"{len(reg['fonts'])} entries, {bad} problems")
        sys.exit(1 if bad else 0)

    total = 0
    for family_dir, _family, _group, files in FAMILIES:
        for fname, *_ in files:
            dest = OUT / family_dir / fname
            if not dest.exists():
                _fetch(f"{RAW}/{family_dir}/{fname}", dest)
            total += dest.stat().st_size
            print(f"{dest.relative_to(OUT)}  {dest.stat().st_size:,} B")
        lic = OUT / family_dir / "OFL.txt"
        if not lic.exists():
            _fetch(f"{RAW}/{family_dir}/OFL.txt", lic)
    fonts = build_registry()
    (OUT / "fonts.json").write_text(
        json.dumps({"version": 1, "commit": COMMIT, "fonts": fonts}, indent=1) + "\n",
        encoding="utf-8")
    print(f"\n{len(fonts)} font entries from {len(FAMILIES)} families, {total/1e6:.1f} MB of TTF")


if __name__ == "__main__":
    main()
