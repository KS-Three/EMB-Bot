"""Stage 0's flat/gradient gate, shipped vs scale-relative, across export
resolutions and resamplers — the instrument behind
`cfg.stage0_scale_relative_grad` (built OFF 2026-11-06, ROADMAP phase 2;
`docs/stage0-scale-relative-grad-2026-11-06.md`).

ROADMAP phase 2's exit: the same artwork routes the same way at any export
resolution, and real logos reach the lane their content is. The shipped gate
reads `gradient_smoothness`, which swings 7-34x across a 146-2000 px sweep
(the 08-15 spec §5c). This tool reads every artwork at a ladder of widths
under three PIL filters and through the Studio's own path, runs stage 0 ONCE
per raster with the flag ON (which computes every signal), and re-derives the
OFF class from the same signals with the module's own gates
(`decide_photo`, `decide_flat_gradient`), so both arms see byte-identical
pixels. The re-derivation is checked against a real OFF `classify` on every
native rung; a disagreement is an error, not a footnote.

    python -m tools.stage0_scale_relative run --out sr.json          # from digitizer/
    python -m tools.stage0_scale_relative tables sr.json

Rows and labels:

* committed real artwork, labelled by Kent (the 08-15 spec §3, color_diversity's
  CORPUS): flat customer logos; `drone_render` and `owl_kent` tonal;
* the scale test's synthetic fixtures — measured, never labelled for a margin
  (ROADMAP gate 2);
* the Commons corpus (`python -m tools.photo_corpus fetch`): 18 photographs
  labelled tonal (real tonal artwork, Kent 2026-10-27), 21 logo styles
  UNLABELLED — nobody has ruled flat or gradient on them, so they are reported
  and never counted;
* local-only real artwork when the laptop has it (gitignored `scratch_kent/`):
  `proseal.jpg` flat, `Instagram_icon.png` tonal (Kent's own icon, a
  multi-stop sweep: DOCTRINE 2026-09-30, "Stage 0 was right"). Their readings
  may be committed; the files never are.

Rungs: `native`; `<filter>@<width>` for LANCZOS / BILINEAR / NEAREST at 146,
250, 400, 640, 1000, 1200, 2000 px, DOWNSCALES ONLY (an upscale invents
interpolation, the scale test's rule; measured separately in the doc);
`studio_<interp>` — the Studio's `PROCESS_MAX_PX = 1200` long-edge cap with
cv2 INTER_AREA / INTER_LINEAR / INTER_CUBIC (DOCTRINE 2026-09-11: the product
never sends native bytes), only where the file is larger than 1200.

Every number is an instrument reading, not a quality claim (ROADMAP gate 4);
the one agreement figure is Cohen's kappa against Kent's labels.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent            # digitizer/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core import stage0_classify as s0  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402

TESTDATA = ROOT / "testdata"
CORPUS_DIR = TESTDATA / "photo" / "corpus"


def _scratch_kent() -> Path:
    """`scratch_kent/` in this checkout, else in the primary one (a lane under
    `.claude/worktrees/` has no gitignored folders of its own)."""
    here = ROOT.parent / "scratch_kent"
    if here.exists():
        return here
    import subprocess
    try:
        common = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                                cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return here
    return Path(common).parent / "scratch_kent"


SCRATCH_KENT = _scratch_kent()

WIDTHS = (146, 250, 400, 640, 1000, 1200, 2000)
FILTERS = ("LANCZOS", "BILINEAR", "NEAREST")
STUDIO_MAX_PX = 1200
STUDIO_INTERPS = ("INTER_AREA", "INTER_LINEAR", "INTER_CUBIC")

# name -> (path relative to testdata, label, provenance). Labels are Kent's
# (spec 2026-08-15 §3; owl_kent 2026-09-11; the Commons photographs 2026-10-27).
COMMITTED: dict[str, tuple[str, str, str]] = {
    "becker":        ("becker_marine_logo.png",                "flat",  "real"),
    "tires":         ("logo_script_tires.png",                 "flat",  "real"),
    "enthusiast":    ("photo/enthusiast_logo.png",             "flat",  "real"),
    "fremont":       ("photo/logo_hotel_fremont.webp",         "flat",  "real"),
    "bridge":        ("photo/logo_bridge_bar.jpg",             "flat",  "real"),
    "gaulke":        ("photo/logo_gaulke_roofing.png",         "flat",  "real"),
    "golden_tee":    ("photo/logo_golden_tee.jpg",             "flat",  "real"),
    "screenshot":    ("photo/screenshot_phone_ui_golke.jpg",   "flat",  "real"),
    "mfab_hat":      ("art/logo_mfab_hat.png",                 "flat",  "real"),
    "mfab_lc":       ("art/logo_mfab_lc.png",                  "flat",  "real"),
    "toat_beanie":   ("art/logo_toat_beanie.png",              "flat",  "real"),
    "toat_machine":  ("art/logo_toat_machine.png",             "flat",  "real"),
    "golke_art":     ("art/logo_golke_roofing.png",            "flat",  "real"),
    "fremont_patch": ("art/logo_hotel_fremont_patch.png",      "flat",  "real"),
    "drone":         ("photo/drone_render.png",                "tonal", "real"),
    "owl_kent":      ("photo/owl_kent.jpg",                    "tonal", "real"),
    "logo_alpha":    ("logo_alpha.png",                        "flat",  "synthetic"),
    "logo_whitebg":  ("logo_whitebg.png",                      "flat",  "synthetic"),
    "ribbon_curve":  ("ribbon_curve.png",                      "flat",  "synthetic"),
    "summit":        ("photo/summit_badge.png",                "tonal", "synthetic"),
    "ramp_lin":      ("photo/gradient_ramp_linear.png",        "tonal", "synthetic"),
    "ramp_rad":      ("photo/gradient_ramp_radial.png",        "tonal", "synthetic"),
}
# The four fixtures the scale test pins as departing from their native class.
DEPARTS_FROM_NATIVE = ("logo_alpha", "logo_whitebg", "ribbon_curve", "enthusiast")
LOCAL_ONLY = {
    "proseal":   ("proseal.jpg",        "flat",  "real"),
    "instagram": ("Instagram_icon.png", "tonal", "real"),
}


def rows(corpus: bool = True, local: bool = True) -> list[tuple[str, Path, str, str]]:
    """-> [(name, path, label, provenance)] for every artwork present."""
    out = [(n, TESTDATA / rel, lab, prov) for n, (rel, lab, prov) in COMMITTED.items()]
    if corpus and (CORPUS_DIR / "corpus.json").exists():
        for r in json.loads((CORPUS_DIR / "corpus.json").read_text(encoding="utf-8")):
            for ext in (".jpg", ".png"):
                p = CORPUS_DIR / (r["slug"] + ext)
                if p.exists():
                    lab = "tonal" if r["kind"] == "photo" else "unlabelled"
                    out.append((r["slug"], p, lab, "commons"))
    if local:
        out += [(n, SCRATCH_KENT / f, lab, prov) for n, (f, lab, prov) in LOCAL_ONLY.items()
                if (SCRATCH_KENT / f).exists()]
    return [r for r in out if r[1].exists()]


# --- rasters -----------------------------------------------------------------

def _png(im) -> bytes:
    b = io.BytesIO()
    im.save(b, "PNG")
    return b.getvalue()


def rasters(path: Path, widths=WIDTHS, filters=FILTERS, studio: bool = True):
    """Yield (rung, width_px, bytes): native, each filter's downscales, and
    the Studio's 1200-px cap where the file exceeds it."""
    import cv2
    from PIL import Image
    im = Image.open(path)
    conv = im.convert("RGBA") if im.mode in ("RGBA", "LA", "P") else im.convert("RGB")
    yield "native", conv.width, path.read_bytes()
    for f in filters:
        for w in widths:
            if w >= conv.width:
                continue
            h = max(1, round(conv.height / conv.width * w))
            yield f"{f}@{w}", w, _png(conv.resize((w, h), getattr(Image, f)))
    if studio and max(conv.size) > STUDIO_MAX_PX:
        arr = np.array(conv)
        sc = STUDIO_MAX_PX / max(conv.size)
        size = (max(1, round(conv.width * sc)), max(1, round(conv.height * sc)))
        for interp in STUDIO_INTERPS:
            small = cv2.resize(arr, size, interpolation=getattr(cv2, interp))
            yield f"studio_{interp}", size[0], _png(Image.fromarray(small))


# --- the two arms from one set of signals ---------------------------------------

def derive(signals: dict, scale_relative: bool, texture_gate: bool = True) -> str:
    """The class `stage0_classify.classify` returns for `signals` under one arm
    of `stage0_scale_relative_grad` — the module's own gates, in its order."""
    gv = signals["gradient_smoothness"]
    is_photo, photo_conf, _route = s0.decide_photo(
        signals["unique_color_mass"], signals["texture_frac"], signals["two_tone_mass"],
        bool(signals["cutout_alpha"]), texture_gate)
    if is_photo:
        conf = min(photo_conf, s0._gate_confidence(gv, s0.GRAD_VAR_SUBJECT_MIN, s0.GRAD_VAR_SUBJECT_MARGIN))
        cls = "photo_subject" if gv >= s0.GRAD_VAR_SUBJECT_MIN else "photo_scene"
    else:
        grad, gconf = s0.decide_flat_gradient(gv, signals["tonal_frac"], scale_relative)
        conf = min(photo_conf, gconf)
        cls = "gradient" if grad else "flat"
    if cls != "flat" and conf < s0.CONFIDENCE_FLOOR:
        cls = "flat"
    return cls


def measure(name: str, path: Path, label: str, prov: str, **kw) -> list[dict]:
    out = []
    on_cfg = PipelineConfig(stage0_scale_relative_grad=True)
    for rung, width, data in rasters(path, **kw):
        r = s0.classify(data, on_cfg)
        sig = r.signals
        off = derive(sig, False)
        on = derive(sig, True)
        if on != r.class_:
            raise AssertionError(f"{name} {rung}: re-derived ON {on} != classify {r.class_}")
        if rung == "native":
            real_off = s0.classify(data, PipelineConfig()).class_
            if real_off != off:
                raise AssertionError(f"{name}: re-derived OFF {off} != classify {real_off}")
        out.append({"name": name, "label": label, "provenance": prov, "rung": rung, "width": width,
                    "off": off, "on": on,
                    **{k: (round(float(sig[k]), 6) if not isinstance(sig[k], (bool, str)) else sig[k])
                       for k in ("tonal_frac", "gradient_smoothness", "unique_color_mass",
                                 "texture_frac", "two_tone_mass", "cutout_alpha", "photo_route")}})
    return out


def run(out: Path, only: list[str] | None = None, **kw) -> list[dict]:
    data: list[dict] = json.loads(out.read_text(encoding="utf-8")) if out.exists() else []
    done = {d["name"] for d in data}
    for name, path, label, prov in rows():
        if (only and name not in only) or name in done:
            continue
        t0 = time.time()
        data.extend(measure(name, path, label, prov, **kw))
        out.write_text(json.dumps(data, indent=0), encoding="utf-8")
        print(f"{name}: {time.time() - t0:.1f}s", file=sys.stderr, flush=True)
    return data


# --- tables ---------------------------------------------------------------------

def kappa(truth: list[bool], pred: list[bool]) -> float | None:
    """Cohen's kappa for two binary raters; None when chance agreement is 1."""
    n = len(truth)
    if n == 0:
        return None
    po = sum(t == p for t, p in zip(truth, pred)) / n
    pt, pp = sum(truth) / n, sum(pred) / n
    pe = pt * pp + (1 - pt) * (1 - pp)
    return None if pe >= 1 else (po - pe) / (1 - pe)


def _tonal(cls: str) -> bool:
    return cls != "flat"


def _by_name(data: list[dict]) -> dict[str, list[dict]]:
    by: dict[str, list[dict]] = {}
    for d in data:
        by.setdefault(d["name"], []).append(d)
    return by


def _spread(vals: list[float]) -> str:
    lo, hi = min(vals), max(vals)
    if hi <= 0:
        return "0 (all zero)"
    return "inf (min 0)" if lo <= 0 else f"{hi / lo:.1f}x"


def tables(data: list[dict]) -> str:
    """Both arms are re-derived from the stored signals with the module's
    CURRENT gates, so a run read before a constant moved still tables right."""
    data = [{**r, "off": derive(r, False), "on": derive(r, True)} for r in data]
    by = _by_name(data)
    out = ["## 1. Per artwork, every rung (native + downscales x 3 filters + Studio path)\n",
           "| artwork | label | rungs | gradient_smoothness spread | tonal_frac spread | tonal_frac min-max | OFF classes | ON classes |",
           "|---|---|---|---|---|---|---|---|"]
    for name, rs in by.items():
        gv = [r["gradient_smoothness"] for r in rs]
        tf = [r["tonal_frac"] for r in rs]
        offs = sorted({r["off"] for r in rs})
        ons = sorted({r["on"] for r in rs})
        out.append(f"| {name} | {rs[0]['label']}/{rs[0]['provenance']} | {len(rs)} | {_spread(gv)} | "
                   f"{_spread(tf)} | {min(tf):.3f}-{max(tf):.3f} | {', '.join(offs)} | {', '.join(ons)} |")

    out += ["\n## 2. One class at every rung (the phase-2 property)\n",
            "| set | artworks | one class OFF | one class ON |", "|---|---|---|---|"]
    for title, keep in (("real, labelled", lambda r: r["provenance"] == "real"),
                        ("Commons photographs", lambda r: r["provenance"] == "commons" and r["label"] == "tonal"),
                        ("Commons logos (unlabelled)", lambda r: r["provenance"] == "commons" and r["label"] != "tonal"),
                        ("synthetic", lambda r: r["provenance"] == "synthetic")):
        names = [n for n, rs in by.items() if keep(rs[0])]
        one_off = sum(len({r["off"] for r in by[n]}) == 1 for n in names)
        one_on = sum(len({r["on"] for r in by[n]}) == 1 for n in names)
        out.append(f"| {title} | {len(names)} | {one_off} | {one_on} |")
    out.append("\nDEPARTS_FROM_NATIVE (the scale test's strict xfails), ON: "
               + "; ".join(f"{n} {sorted({r['on'] for r in by[n]})}" for n in DEPARTS_FROM_NATIVE if n in by))

    real = [r for r in data if r["provenance"] in ("real", "commons") and r["label"] in ("flat", "tonal")]
    flat = [r for r in real if r["label"] == "flat"]
    tonal = [r for r in real if r["label"] == "tonal"]
    out += ["\n## 3. tonal_frac margin on labelled real artwork (owl_kent enrolled)\n",
            f"Gate `TONAL_GRADIENT_MIN` {s0.TONAL_GRADIENT_MIN}. Every labelled real raster, whichever "
            "territory the photo gate put it in.\n",
            "| rungs | tonal set | real tonal artworks | flat max | tonal min | gap |", "|---|---|---|---|---|---|"]
    rung_sets = (("native + Studio path", lambda r: r["rung"] == "native" or r["rung"].startswith("studio_")),
                 ("+ downscales >= 400 px", lambda r: "@" not in r["rung"] or int(r["rung"].split("@")[1]) >= 400),
                 ("every rung", lambda r: True))
    for title, keep in rung_sets:
        for tset, tkeep in (("all", lambda r: True), ("without drone_render", lambda r: r["name"] != "drone")):
            f = [r for r in flat if keep(r)]
            t = [r for r in tonal if keep(r) and tkeep(r)]
            if not (f and t):
                continue
            fmax = max(f, key=lambda r: r["tonal_frac"])
            tmin = min(t, key=lambda r: r["tonal_frac"])
            out.append(f"| {title} | {tset} | {len({r['name'] for r in t})} | {fmax['tonal_frac']:.3f} ({fmax['name']} {fmax['rung']}) | "
                       f"{tmin['tonal_frac']:.3f} ({tmin['name']} {tmin['rung']}) | {tmin['tonal_frac'] - fmax['tonal_frac']:+.3f} |")
    out += ["\n## 4. Chance-corrected agreement with Kent's labels (tonal = any non-flat class)\n",
            "| rows | n rasters | kappa OFF | kappa ON | flat rasters routed non-flat OFF / ON | tonal rasters routed flat OFF / ON |",
            "|---|---|---|---|---|---|"]
    for title, keep in (("all labelled real", lambda r: True),
                        ("native only", lambda r: r["rung"] == "native"),
                        ("native + Studio path", lambda r: r["rung"] == "native" or r["rung"].startswith("studio_")),
                        ("downscales only", lambda r: "@" in r["rung"])):
        sel = [r for r in real if keep(r)]
        truth = [r["label"] == "tonal" for r in sel]
        k_off = kappa(truth, [_tonal(r["off"]) for r in sel])
        k_on = kappa(truth, [_tonal(r["on"]) for r in sel])
        fo = sum(1 for r in sel if r["label"] == "flat" and _tonal(r["off"]))
        fn = sum(1 for r in sel if r["label"] == "flat" and _tonal(r["on"]))
        to = sum(1 for r in sel if r["label"] == "tonal" and not _tonal(r["off"]))
        tn = sum(1 for r in sel if r["label"] == "tonal" and not _tonal(r["on"]))
        nf = sum(1 for r in sel if r["label"] == "flat")
        nt = len(sel) - nf

        def fmt(k):
            return "n/a" if k is None else f"{k:+.3f}"
        out.append(f"| {title} | {len(sel)} | {fmt(k_off)} | {fmt(k_on)} | {fo}/{nf} -> {fn}/{nf} | {to}/{nt} -> {tn}/{nt} |")

    out += ["\n## 5. Real flat customer logos: lane at native and through the Studio path\n",
            "| artwork | native OFF | native ON | Studio OFF | Studio ON | downscales routed non-flat OFF / ON |",
            "|---|---|---|---|---|---|"]
    for name, rs in by.items():
        if not (rs[0]["provenance"] == "real" and rs[0]["label"] == "flat"):
            continue
        nat = next(r for r in rs if r["rung"] == "native")
        st = [r for r in rs if r["rung"].startswith("studio_")] or [nat]
        downs = [r for r in rs if "@" in r["rung"]]
        out.append(f"| {name} | {nat['off']} | {nat['on']} | {'/'.join(sorted({r['off'] for r in st}))} | "
                   f"{'/'.join(sorted({r['on'] for r in st}))} | "
                   f"{sum(_tonal(r['off']) for r in downs)}/{len(downs)} -> {sum(_tonal(r['on']) for r in downs)}/{len(downs)} |")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="measure (resumes: names already in --out are skipped)")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--only", nargs="*")
    r.add_argument("--filters", nargs="*", default=list(FILTERS), choices=list(FILTERS))
    t = sub.add_parser("tables")
    t.add_argument("json", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        print(tables(run(a.out, a.only, filters=tuple(a.filters))))
    else:
        print(tables(json.loads(a.json.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    main()
