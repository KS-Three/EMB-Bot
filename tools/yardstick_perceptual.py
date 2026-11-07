#!/usr/bin/env python3
"""tools/yardstick_perceptual.py: FLIP, LPIPS and DreamSim between a rendered
"ours" stitch file and a rendered reference, for a list of pairs; with Kent's
labels, Cohen's kappa against his picks (bootstrap 95% intervals, never a
raw share: ROADMAP gate 4).

    python tools/yardstick_perceptual.py score PAIRS [--labels [PATH]] --out DIR
    python tools/yardstick_perceptual.py oracle PAIRS --out DIR
    python tools/yardstick_perceptual.py from-pro-pooled --runs DIR --out PAIRS.csv
    python tools/yardstick_perceptual.py from-tripwire --runs DIR --out PAIRS.csv
    python tools/yardstick_perceptual.py metrics

PAIRS is a CSV (header row) or a JSON list of objects. Columns:

    ours_path   a machine file (DST, PES, ...) -- what the engine sewed
    ref_path    the machine file it is measured against (the pro's, or
                another arm's)
    id          optional row id (defaults to the two file stems)
    label       optional: Kent's pick for an A/B pair, one of
                before / after / same / both_bad / tie
    pair_id     with `label`: the two rows of one A/B pair share it
    arm         with `label`: `before` or `after` -- which side this row is
    design      optional cluster for the second bootstrap (defaults to the
                ref file's stem): pairs from one logo are not independent

Each row is rendered through the repo's own stitch renderer
(`digitizer_core.stitchviz.render_design`, the pro-parity overlay's frame
and registration), both sides on one canvas, monochrome by default, and
scored with every metric that is installed. A metric whose package is
missing is a column of `n/a` with the reason, never a crash: the heavy
dependencies live in `tools/requirements-yardstick.txt`, NOT in the
digitizer's own venv (`docs/yardstick-perceptual.md`).

The instrument's pick on an A/B pair is the arm whose render is CLOSER to
the reference (lower distance); equal to `--tie-band` is a tie. The kappa is
`tools.eye_pairs.pooled`'s: linear-weighted 3-way with ties in, plain 2x2 on
the pairs both decided, percentile bootstrap over pairs and over designs,
`pooled.reading` saying what the intervals license. `mse` is a pixel
control, not a candidate: a perceptual metric that cannot beat it has
earned nothing.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import json
import os
import platform
import sys
import warnings
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
DIGITIZER = REPO / "digitizer"
for p in (DIGITIZER, DIGITIZER / "tools", DIGITIZER / "tools" / "pro_parity"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import cv2                                                      # noqa: E402
import pairframe as pf                                          # noqa: E402
from digitizer_core.stitchviz import render_design              # noqa: E402
from tools.eye_pairs import pooled                              # noqa: E402

#: Metric columns in the order the score table carries them. `mse` is the
#: pixel control; the four others are the candidates the 11-06 yardstick
#: brief names. Every one is a DISTANCE: 0 for identical renders, larger is
#: worse.
METRICS = ("mse", "flip", "lpips_alex", "lpips_vgg", "dreamsim")
LABELS = tuple(pooled.VOCABULARY) + ("tie",)
ARMS = ("before", "after")
DEFAULT_PPM = 12.0          # pro_parity.overlay.DEFAULT_PPM: the pair pages' scale
DEFAULT_PAD_MM = 3.0
DEFAULT_MAX_PX = 1024       # cap on the long side before scoring (CPU time, LPIPS memory)
MONO_RGB = (20, 20, 20)     # every block one dark grey: colour order is not what is scored
WHITE = (255, 255, 255)
SCORE_DECIMALS = 6
SEED = 20261107
_DREAMSIM_CACHE = Path(os.environ.get("YARDSTICK_DREAMSIM_CACHE",
                                      Path.home() / ".cache" / "dreamsim"))


# ------------------------------------------------------------------ pairs

def read_pairs(path: Path) -> list[dict]:
    """The pair list as a list of dicts with the schema in the module doc;
    paths relative to the list's own folder are made absolute there."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        rows = json.loads(text)
        if isinstance(rows, dict):
            rows = rows.get("pairs", [])
    else:
        rows = list(csv.DictReader(text.splitlines()))
    out = []
    for i, r in enumerate(rows):
        r = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items() if k}
        for key in ("ours_path", "ref_path"):
            if not r.get(key):
                raise SystemExit(f"{path}: row {i + 1} has no {key}")
            p = Path(r[key])
            r[key] = str(p if p.is_absolute() else (path.parent / p).resolve())
        r["id"] = r.get("id") or f"{Path(r['ours_path']).stem}~{Path(r['ref_path']).stem}"
        r["design"] = r.get("design") or Path(r["ref_path"]).stem
        for key in ("label", "pair_id", "arm"):
            if r.get(key) in ("", None):
                r.pop(key, None)
        out.append(r)
    if not out:
        raise SystemExit(f"{path}: no pairs")
    return out


def attach_labels(rows: list[dict], labels: Path | None) -> list[dict]:
    """Labels from a separate CSV/JSON (`pair_id`, `label`, optional
    `design`) merged onto the rows by `pair_id`; rows keep their own label
    where the file is silent."""
    if labels is None:
        return rows
    ltext = Path(labels).read_text(encoding="utf-8")
    if Path(labels).suffix.lower() == ".json":
        items = json.loads(ltext)
        items = items.items() if isinstance(items, dict) else [(x["pair_id"], x) for x in items]
        table = {k: (v if isinstance(v, dict) else {"label": v}) for k, v in items}
    else:
        table = {r["pair_id"].strip(): r for r in csv.DictReader(ltext.splitlines())}
    for r in rows:
        hit = table.get(r.get("pair_id", ""))
        if hit:
            r["label"] = hit.get("label", r.get("label"))
            if hit.get("design"):
                r["design"] = hit["design"]
    return rows


def ab_pairs(rows: list[dict]) -> list[dict]:
    """Rows grouped into A/B pairs: {pair_id, design, kent, before: row,
    after: row}. Refuses a label outside the vocabulary, a pair without
    both arms, two rows on one arm, or arms that disagree on the label."""
    groups: dict[str, dict] = {}
    for r in rows:
        if "label" not in r and "pair_id" not in r:
            continue
        pid = r.get("pair_id")
        if not pid:
            raise SystemExit(f"row {r['id']}: a label needs a pair_id (and an arm)")
        if r.get("arm") not in ARMS:
            raise SystemExit(f"row {r['id']}: arm must be one of {ARMS}, got {r.get('arm')!r}")
        g = groups.setdefault(pid, {"pair_id": pid, "design": r["design"], "labels": set()})
        if r["arm"] in g:
            raise SystemExit(f"pair {pid}: two rows on arm {r['arm']!r}")
        g[r["arm"]] = r
        if "label" in r:
            if r["label"] not in LABELS:
                raise SystemExit(f"pair {pid}: label {r['label']!r} not in {LABELS}")
            g["labels"].add(r["label"])
    out = []
    for pid, g in groups.items():
        missing = [a for a in ARMS if a not in g]
        if missing:
            raise SystemExit(f"pair {pid}: no {missing[0]!r} row")
        if len(g["labels"]) > 1:
            raise SystemExit(f"pair {pid}: arms disagree on the label {sorted(g['labels'])}")
        if not g["labels"]:
            continue                                    # paired, unlabelled: scored, not read
        lab = next(iter(g["labels"]))
        g["kent"] = pooled.VOCABULARY.get(lab, lab)     # same / both_bad -> tie
        g.pop("labels")
        out.append(g)
    return out


# ---------------------------------------------------------------- render

def _design(path: Path, reg, name: str, mono: bool) -> dict:
    d = pf.design_for(Path(path), reg, [MONO_RGB] if mono else None, name)
    if mono:
        # A PES carries its own thread list and a DST none, so the fallback
        # alone would draw one side in colour and the other in grey; every
        # block of both sides takes the one grey, and structure is all that
        # is scored.
        r, g, b = MONO_RGB
        d["colors"] = [{"r": r, "g": g, "b": b} for _ in (d.get("colors") or [None])]
    return d


def render_pair(ours: Path, ref: Path, *, ppm: float = DEFAULT_PPM, pad_mm: float = DEFAULT_PAD_MM,
                register: bool = True, mono: bool = True, max_px: int = DEFAULT_MAX_PX) -> dict:
    """Both files drawn on ONE canvas -- the reference's frame (`pad_mm`
    round its sewn extent), `ours` registered onto it (scale, y-flip,
    translation: `pairframe.register_pair`) unless `register` is off.
    -> {ours, ref: uint8 HxWx3 BGR, reg: dict | None, size: (h, w)}."""
    reg = None
    if register and Path(ours).resolve() != Path(ref).resolve():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", pf.RegistrationWarning)
            reg = pf.register_pair(Path(ref), Path(ours))
    ref_d = _design(ref, None, "ref", mono)
    ours_d = _design(ours, reg, "ours", mono)
    frame = pf.frame_for([ref_d], ppm, pad_mm=pad_mm)
    imgs = {}
    for name, d in (("ref", ref_d), ("ours", ours_d)):
        img = _render_in(d, frame)
        imgs[name] = _finish(img, mono, max_px)
    return {**imgs, "reg": reg.as_dict() if reg is not None else None, "size": imgs["ref"].shape[:2]}


def _render_in(design: dict, frame) -> np.ndarray:
    # pro_parity.overlay.render_side's two steps (clip to the frame, pin its
    # corners), with this tool's fabric; imported here so `metrics` and the
    # pair-list helpers do not pay for overlay's imports.
    from overlay import _fit_to_frame                        # noqa: PLC0415
    d = pf.pin_frame(_fit_to_frame(design, frame), frame.bounds_units)
    return render_design(d, px_per_mm=frame.ppm, fabric_bgr=WHITE, pad_mm=frame.pad_mm, lit=True)


def _finish(img: np.ndarray, mono: bool, max_px: int) -> np.ndarray:
    if mono:
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
    h, w = img.shape[:2]
    long = max(h, w)
    if max_px and long > max_px:
        s = max_px / long
        img = cv2.resize(img, (max(1, int(round(w * s))), max(1, int(round(h * s)))),
                         interpolation=cv2.INTER_AREA)
    return img


def blank_like(img: np.ndarray) -> np.ndarray:
    return np.full_like(img, 255)


# --------------------------------------------------------------- metrics

class Metric:
    """One distance over two uint8 BGR renders of one size. `load` imports
    the package once; a failure leaves `unavailable` set and the column
    reads `n/a`."""

    name = "metric"
    package = None

    def __init__(self) -> None:
        self.unavailable: str | None = None
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            self._load()
        except Exception as e:                   # noqa: BLE001 -- the column says why
            self.unavailable = f"{type(e).__name__}: {e}"[:300]

    def _load(self) -> None:
        pass

    def __call__(self, ref: np.ndarray, test: np.ndarray) -> float | None:
        self.load()
        if self.unavailable:
            return None
        return float(self._score(ref, test))

    def _score(self, ref: np.ndarray, test: np.ndarray) -> float:
        raise NotImplementedError


def _rgb01(img: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


class MSE(Metric):
    """Pixel control: mean squared difference of the two renders in [0, 1]."""
    name = "mse"

    def _score(self, ref, test):
        d = _rgb01(ref) - _rgb01(test)
        return float(np.mean(d * d))


class FLIP(Metric):
    """NVIDIA FLIP (LDR, sRGB inputs, default 67 pixels per degree), the mean
    over the error map. Package `flip-evaluator`."""
    name = "flip"
    package = "flip-evaluator"

    def _load(self):
        self.mod = importlib.import_module("flip_evaluator")

    def _score(self, ref, test):
        _m, mean, _p = self.mod.evaluate(_rgb01(ref), _rgb01(test), "LDR",
                                         inputsRGB=True, applyMagma=False, computeMeanError=True)
        return mean


def _torch():
    torch = importlib.import_module("torch")
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 1)))
    torch.manual_seed(0)
    return torch


def _nchw(torch, img01: np.ndarray):
    t = torch.from_numpy(np.ascontiguousarray(img01)).permute(2, 0, 1).unsqueeze(0)
    return t.float()


class LPIPS(Metric):
    """Learned Perceptual Image Patch Similarity (Zhang 2018) on the given
    backbone, inputs scaled to [-1, 1]. Packages `lpips`, `torch` (CPU)."""
    package = "lpips (+ torch)"

    def __init__(self, net: str) -> None:
        super().__init__()
        self.net = net
        self.name = f"lpips_{net}"

    def _load(self):
        self.torch = _torch()
        lpips = importlib.import_module("lpips")
        self.model = lpips.LPIPS(net=self.net, verbose=False).eval()

    def _score(self, ref, test):
        torch = self.torch
        with torch.no_grad():
            a = _nchw(torch, _rgb01(ref)) * 2 - 1
            b = _nchw(torch, _rgb01(test)) * 2 - 1
            return self.model(a, b).item()


class DreamSim(Metric):
    """DreamSim (Fu 2023), 1 - cosine of the two embeddings; the package's own
    preprocessing (224 px). Packages `dreamsim`, `torch` (CPU); weights are
    fetched to `YARDSTICK_DREAMSIM_CACHE` (default ~/.cache/dreamsim) on
    first use."""
    name = "dreamsim"
    package = "dreamsim (+ torch; weights downloaded on first use)"

    def __init__(self, kind: str = "ensemble") -> None:
        super().__init__()
        self.kind = kind

    def _load(self):
        self.torch = _torch()
        ds = importlib.import_module("dreamsim")
        _DREAMSIM_CACHE.mkdir(parents=True, exist_ok=True)
        self.model, self.preprocess = ds.dreamsim(pretrained=True, device="cpu",
                                                  cache_dir=str(_DREAMSIM_CACHE),
                                                  dreamsim_type=self.kind)
        self.PIL = importlib.import_module("PIL.Image")

    def _score(self, ref, test):
        torch = self.torch
        with torch.no_grad():
            a = self.preprocess(self.PIL.fromarray(cv2.cvtColor(ref, cv2.COLOR_BGR2RGB)))
            b = self.preprocess(self.PIL.fromarray(cv2.cvtColor(test, cv2.COLOR_BGR2RGB)))
            return self.model(a, b).item()


def make_metrics(only: list[str] | None = None, dreamsim_type: str = "ensemble") -> list[Metric]:
    ms = [MSE(), FLIP(), LPIPS("alex"), LPIPS("vgg"), DreamSim(dreamsim_type)]
    if only:
        bad = set(only) - set(METRICS)
        if bad:
            raise SystemExit(f"unknown metric(s) {sorted(bad)}; choose from {METRICS}")
        ms = [m for m in ms if m.name in only]
    return ms


def availability(metrics: list[Metric]) -> dict[str, str | None]:
    """metric -> None when it scores, else the reason it is `n/a`."""
    for m in metrics:
        m.load()
    return {m.name: m.unavailable for m in metrics}


# ----------------------------------------------------------------- score

def score_rows(rows: list[dict], metrics: list[Metric], *, oracles: bool = False, **render_kw) -> list[dict]:
    """One scored row per pair; with `oracles`, two more per distinct
    reference: `ref vs itself` (every metric must read 0) and `ref vs a
    blank canvas` (must read the worst of the set)."""
    out = []
    seen_ref: set[str] = set()
    for r in rows:
        rp = render_pair(Path(r["ours_path"]), Path(r["ref_path"]), **render_kw)
        out.append(_scored(r, rp["ref"], rp["ours"], metrics, reg=rp["reg"], kind="pair"))
        if oracles and r["ref_path"] not in seen_ref:
            seen_ref.add(r["ref_path"])
            stem = Path(r["ref_path"]).stem
            out.append(_scored({"id": f"{stem}~self", "ours_path": r["ref_path"], "ref_path": r["ref_path"],
                                "design": r["design"]}, rp["ref"], rp["ref"], metrics, reg=None, kind="self"))
            out.append(_scored({"id": f"{stem}~blank", "ours_path": "(blank canvas)", "ref_path": r["ref_path"],
                                "design": r["design"]}, rp["ref"], blank_like(rp["ref"]), metrics,
                               reg=None, kind="blank"))
    return out


def _scored(r: dict, ref: np.ndarray, ours: np.ndarray, metrics: list[Metric], *, reg, kind: str) -> dict:
    row = {"id": r["id"], "kind": kind, "pair_id": r.get("pair_id", ""), "arm": r.get("arm", ""),
           "label": r.get("label", ""), "design": r.get("design", ""),
           "ours_path": r["ours_path"], "ref_path": r["ref_path"],
           "px": f"{ref.shape[1]}x{ref.shape[0]}",
           "reg_iou": "" if reg is None else f"{reg['iou']:.4f}",
           "reg_scale": "" if reg is None else f"{reg['scale']:.4f}"}
    for m in metrics:
        v = m(ref, ours)
        # `+ 0.0` turns a rounded -0.0 (DreamSim's 1 - cos on identical
        # inputs lands a hair under zero) into 0.0, so the table never
        # carries "-0.000000" and its md5 does not hang on the sign of noise
        row[m.name] = "n/a" if v is None else f"{round(v, SCORE_DECIMALS) + 0.0:.{SCORE_DECIMALS}f}"
    return row


def oracle_check(scored: list[dict], metrics: list[Metric]) -> dict:
    """The two sanity oracles per metric that scored: every `self` row reads
    0 (to 1e-6) and every `blank` row is at least every other row of the
    set; `blank_worst_same_ref` asks the same of each blank against only the
    rows of its own reference.
    -> {metric: {self_zero, blank_worst, blank_worst_same_ref, refs_checked,
    worst_self, blank_min, pair_max}}."""
    res = {}
    for m in metrics:
        if m.unavailable:
            res[m.name] = {"unavailable": m.unavailable}
            continue
        vals = {k: [float(r[m.name]) for r in scored if r["kind"] == k and r[m.name] != "n/a"]
                for k in ("self", "blank", "pair")}
        worst_self = max(abs(v) for v in vals["self"]) if vals["self"] else None
        blank_min = min(vals["blank"]) if vals["blank"] else None
        others = vals["pair"] + vals["self"]
        pair_max = max(others) if others else None
        # Same-reference reading (added after `lpips_vgg` failed the global
        # one, 2026-11-07): each blank against only the rows scored against
        # ITS OWN reference. The kappa compares two arms against one pro, so
        # this is the ordering it relies on; the global reading above stays.
        by_ref: dict[str, dict[str, list[float]]] = {}
        for r in scored:
            if r["kind"] in ("self", "blank", "pair") and r[m.name] != "n/a":
                slot = by_ref.setdefault(r["ref_path"], {"blank": [], "other": []})
                slot["blank" if r["kind"] == "blank" else "other"].append(float(r[m.name]))
        checked = [s for s in by_ref.values() if s["blank"] and s["other"]]
        same_ref = bool(checked) and all(min(s["blank"]) >= max(s["other"]) for s in checked)
        res[m.name] = {"self_zero": worst_self is not None and worst_self <= 1e-6,
                       "blank_worst": blank_min is not None and pair_max is not None and blank_min >= pair_max,
                       "blank_worst_same_ref": same_ref, "refs_checked": len(checked),
                       "worst_self": worst_self, "blank_min": blank_min, "pair_max": pair_max}
    return res


# ----------------------------------------------------------------- kappa

def instrument_pick(before: float, after: float, tie_band: float = 0.0) -> str:
    """The arm whose render is closer to the reference; within `tie_band`
    (a fraction of the larger distance) is a tie, as is an exact equality."""
    hi = max(abs(before), abs(after), 1e-12)
    if abs(after - before) <= tie_band * hi or round(after - before, 9) == 0:
        return "tie"
    return "after" if after < before else "before"


def agreement(pairs: list[dict], scored: list[dict], metric: str, *, tie_band: float = 0.0,
              seed: int = SEED) -> dict:
    """Chance-corrected agreement of `metric`'s pick with Kent's over the A/B
    pairs: the `pooled.agreement` shape (3-way linear-weighted kappa with
    ties in, 2x2 on the pairs both decided, percentile bootstrap over pairs
    and over designs, `pooled.reading`). No raw agreement anywhere."""
    by_id = {r["id"]: r for r in scored if r["kind"] == "pair"}
    picks = []
    for p in pairs:
        b, a = by_id[p["before"]["id"]].get(metric), by_id[p["after"]["id"]].get(metric)
        if b in (None, "n/a") or a in (None, "n/a"):
            continue
        picks.append((p, instrument_pick(float(b), float(a), tie_band)))
    res = {"metric": metric, "n_scored": len(picks),
           "n_kent_decided": sum(1 for p, _ in picks if p["kent"] != "tie"),
           "n_instrument_silent_on_decided": sum(1 for p, i in picks if p["kent"] != "tie" and i == "tie"),
           "table_3way": None}
    if not picks:
        res.update(kappa_3way=None, reading_3way="no scored pair", kappa_decided=None,
                   n_decided=0, reading_decided="no scored pair")
        return res
    rng = np.random.default_rng(seed)
    k3 = np.array([pooled.SIDES.index(p["kent"]) for p, _ in picks], dtype=int)
    i3 = np.array([pooled.SIDES.index(i) for _, i in picks], dtype=int)
    fx = [p["design"] for p, _ in picks]
    t3 = pooled._table(k3, i3, 3)
    res["table_3way"] = t3.tolist()                 # rows Kent (before, tie, after), cols instrument
    res["kappa_3way"] = pooled.kappa_from_table(t3, "linear")
    lo, hi, used = pooled._boot(k3, i3, fx, 3, "linear", cluster=False, rng=rng)
    clo, chi, cused = pooled._boot(k3, i3, fx, 3, "linear", cluster=True, rng=rng)
    res.update(ci3_pairs=[lo, hi], ci3_designs=[clo, chi], ci3_resamples=[used, cused],
               reading_3way=pooled.reading(len(picks), (lo, hi), (clo, chi)))
    dec = [(p, i) for p, i in picks if p["kent"] != "tie" and i != "tie"]
    res["n_decided"] = len(dec)
    k2 = np.array([0 if p["kent"] == "before" else 1 for p, _ in dec], dtype=int)
    i2 = np.array([0 if i == "before" else 1 for _, i in dec], dtype=int)
    res["kappa_decided"] = pooled.kappa_from_table(pooled._table(k2, i2, 2)) if dec else None
    lo, hi, used = pooled._boot(k2, i2, [p["design"] for p, _ in dec], 2, "none", cluster=False, rng=rng)
    clo, chi, cused = pooled._boot(k2, i2, [p["design"] for p, _ in dec], 2, "none", cluster=True, rng=rng)
    res.update(ci2_pairs=[lo, hi], ci2_designs=[clo, chi], ci2_resamples=[used, cused],
               reading_decided=pooled.reading(len(dec), (lo, hi), (clo, chi)))
    # the exit's second clause: pairs Kent decided where the instrument chose the OTHER side
    res["worse_pairs"] = [p["pair_id"] for p, i in picks if p["kent"] != "tie" and i != "tie" and i != p["kent"]]
    return res


# ---------------------------------------------------------------- output

COLUMNS = ("id", "kind", "pair_id", "arm", "label", "design", "px", "reg_iou", "reg_scale",
           *METRICS, "ours_path", "ref_path")


def write_table(scored: list[dict], out: Path, metrics: list[Metric]) -> str:
    """scores.csv (fixed column order, fixed decimals) -> its md5."""
    cols = [c for c in COLUMNS if c not in METRICS or c in {m.name for m in metrics}]
    out.mkdir(parents=True, exist_ok=True)
    buf = _Lines()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(cols)
    for r in scored:
        w.writerow([r.get(c, "") for c in cols])
    text = "".join(buf.lines)
    (out / "scores.csv").write_text(text, encoding="utf-8", newline="")
    return hashlib.md5(text.encode("utf-8")).hexdigest()


class _Lines:
    def __init__(self):
        self.lines = []

    def write(self, s):
        self.lines.append(s)


def _f(v, nd=3):
    return "-" if v is None else f"{v:+.{nd}f}"


def _ci(ci):
    return "-" if not ci or ci[0] is None else f"[{ci[0]:+.2f}, {ci[1]:+.2f}]"


def markdown(scored: list[dict], metrics: list[Metric], avail: dict, kappas: dict | None,
             oracle: dict | None, md5: str) -> str:
    L = ["# yardstick_perceptual", ""]
    L.append("| metric | status |")
    L.append("|---|---|")
    for m in metrics:
        L.append(f"| {m.name} | {'scored' if not avail[m.name] else 'n/a: ' + avail[m.name]} |")
    L += ["", f"scores.csv md5 `{md5}` ({len(scored)} rows)", ""]
    if oracle:
        L += ["## Oracles", "", "| metric | self reads 0 | blank is worst | blank is worst, same reference "
              "| worst self | blank min | pair max |", "|---|---|---|---|---|---|---|"]
        for name, o in oracle.items():
            if "unavailable" in o:
                L.append(f"| {name} | n/a | n/a | n/a | | | |")
                continue
            L.append(f"| {name} | {'yes' if o['self_zero'] else 'NO'} | {'yes' if o['blank_worst'] else 'NO'} | "
                     f"{'yes' if o['blank_worst_same_ref'] else 'NO'} | {o['worst_self']:.6f} | {o['blank_min']:.6f} | {o['pair_max']:.6f} |")
        L.append("")
    if kappas:
        L += ["## Agreement with Kent's picks (Cohen's kappa, 95% bootstrap intervals; n beside every figure)",
              "", "No raw agreement share is computed (ROADMAP gate 4).", "",
              "| metric | n | n Kent decided | kappa 3-way (ties in) | CI pairs | CI designs | reading "
              "| n both decided | kappa 2x2 | CI pairs | CI designs | reading "
              "| instrument silent on decided | worse pairs |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for name, k in kappas.items():
            L.append(f"| {name} | {k['n_scored']} | {k['n_kent_decided']} | {_f(k.get('kappa_3way'))} | "
                     f"{_ci(k.get('ci3_pairs'))} | {_ci(k.get('ci3_designs'))} | {k.get('reading_3way')} | "
                     f"{k.get('n_decided', 0)} | {_f(k.get('kappa_decided'))} | {_ci(k.get('ci2_pairs'))} | "
                     f"{_ci(k.get('ci2_designs'))} | {k.get('reading_decided')} | "
                     f"{k['n_instrument_silent_on_decided']} | {len(k.get('worse_pairs', []))} |")
        L.append("")
        L.append("A metric clears chance when BOTH 3-way intervals sit above zero (`above chance`); "
                 "the exit's second clause needs `worse pairs` at 0.")
        L.append("")
    cols = [c for c in COLUMNS if c not in ("ours_path", "ref_path")
            and (c not in METRICS or c in {m.name for m in metrics})]
    L += ["## Scores", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in scored:
        L.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(L) + "\n"


def environment(metrics: list[Metric]) -> dict:
    env = {"python": platform.python_version(), "platform": platform.platform(), "cv2": cv2.__version__,
           "numpy": np.__version__}
    for mod in ("torch", "lpips", "dreamsim", "flip_evaluator"):
        try:
            m = importlib.import_module(mod)
            env[mod] = getattr(m, "__version__", "present")
        except Exception as e:                                   # noqa: BLE001
            env[mod] = f"absent ({type(e).__name__})"
    try:
        import subprocess
        env["engine_head"] = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                                            capture_output=True, text=True, check=False).stdout.strip()
    except Exception:                                            # noqa: BLE001
        env["engine_head"] = None
    return env


# ------------------------------------------------------------- pair lists

def from_pro_pooled(runs: Path, inputs: Path | None, out: Path) -> int:
    """Kent's labelled pairs with a pro file (`docs/eye-pairs-2026-11-01/
    pro-pair-inputs.json` via `pro_pooled_build.labelled_pairs`) as a pair
    list, each arm's `ours.dst` under `runs/<tree>/<fixture>/<side>/`
    (`pro_pooled_build.py render --runs DIR` writes them), the pro's DST as
    the reference. Pairs whose render is missing are listed to stderr."""
    from tools.eye_pairs import pro_pooled_build as ppb
    from tools.pro_baseline import JOBS, resolve
    from tools.tripwire import materialise
    inp = json.loads(Path(inputs).read_text(encoding="utf-8")) if inputs else None
    try:
        # scratch_kent/ when it holds the pro files, else the committed zip
        materialise(Path(runs) / "_kent", sorted(set(ppb.FIXTURE_JOB.values())))
    except SystemExit as e:
        print(f"pro files: {e} (pairs on those jobs are skipped below)", file=sys.stderr)
    rows, missing = [], []
    for p in ppb.labelled_pairs(inp):
        if "before_design" not in p:
            missing.append(f"{p['id']}: {p['unscored_why']}")
            continue
        job = ppb.FIXTURE_JOB[p["fixture"]]
        try:
            pro = resolve(JOBS[job][3])
        except SystemExit as e:
            missing.append(f"{p['id']}: pro file: {e}")
            continue
        arm_rows = []
        for arm, design in (("before", p["before_design"]), ("after", p["after_design"])):
            tree, side, _kw = design
            dst = ppb.design_dir(Path(runs), tree, p["fixture"], side) / "ours.dst"
            if not dst.exists():
                missing.append(f"{p['id']}: {arm} not rendered ({dst})")
                break
            arm_rows.append({"id": f"{p['id']}:{arm}", "ours_path": str(dst), "ref_path": str(pro),
                             "label": p["label"], "pair_id": p["id"], "arm": arm, "design": p["fixture"]})
        else:
            rows.extend(arm_rows)
    _write_pairs(rows, out)
    for m in missing:
        print(f"skipped {m}", file=sys.stderr)
    print(f"{len(rows) // 2} labelled pairs ({len(rows)} rows) -> {out}; {len(missing)} skipped")
    return 0


def from_tripwire(runs: Path, out: Path) -> int:
    """The committed tripwire jobs (`tools.tripwire.committed_jobs`) as
    unlabelled pairs: `runs/<job>/ours.dst` (`pro_baseline.py digitize
    --runs DIR` writes them) against the pro's DST."""
    from tools.pro_baseline import JOBS, resolve
    from tools.tripwire import committed_jobs, materialise
    jobs = committed_jobs()
    # the pro files are in the committed zip; `materialise` extracts what
    # these jobs need beside the runs (tripwire's own `RUNS/_kent` layout)
    materialise(Path(runs) / "_kent", jobs)
    rows = []
    for job in jobs:
        ours = Path(runs) / job / "ours.dst"
        if not ours.exists():
            print(f"skipped {job}: {ours} missing", file=sys.stderr)
            continue
        rows.append({"id": job, "ours_path": str(ours), "ref_path": str(resolve(JOBS[job][3])), "design": job})
    _write_pairs(rows, out)
    print(f"{len(rows)} pairs -> {out}")
    return 0


def _write_pairs(rows: list[dict], out: Path) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".json":
        out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        return
    cols = ["id", "ours_path", "ref_path", "label", "pair_id", "arm", "design"]
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})


# ------------------------------------------------------------------- CLI

def run(pairs_path: Path, out: Path, *, labels=None, metrics_only=None, oracles=False, tie_band=0.0,
        ppm=DEFAULT_PPM, pad_mm=DEFAULT_PAD_MM, max_px=DEFAULT_MAX_PX, register=True, mono=True,
        dreamsim_type="ensemble", quiet=False) -> dict:
    rows = read_pairs(Path(pairs_path))
    if labels not in (None, False):
        rows = attach_labels(rows, None if labels is True else Path(labels))
    pairs = ab_pairs(rows)
    if labels not in (None, False) and not pairs:
        raise SystemExit(f"--labels given but {pairs_path} has no labelled A/B pair "
                         f"(rows need label, pair_id and arm; or pass --labels PATH)")
    metrics = make_metrics(metrics_only, dreamsim_type)
    avail = availability(metrics)
    if not quiet:
        for name, why in avail.items():
            print(f"{name}: {'ok' if why is None else 'n/a -- ' + why}", file=sys.stderr)
    scored = score_rows(rows, metrics, oracles=oracles, ppm=ppm, pad_mm=pad_mm, max_px=max_px,
                        register=register, mono=mono)
    out = Path(out)
    md5 = write_table(scored, out, metrics)
    oracle = oracle_check(scored, metrics) if oracles else None
    kappas = {m.name: agreement(pairs, scored, m.name, tie_band=tie_band)
              for m in metrics if not m.unavailable} if pairs else None
    report = {"schema": 1, "pairs": str(pairs_path), "n_rows": len(rows), "n_labelled_pairs": len(pairs),
              "settings": {"ppm": ppm, "pad_mm": pad_mm, "max_px": max_px, "register": register, "mono": mono,
                           "tie_band": tie_band, "dreamsim_type": dreamsim_type, "seed": SEED,
                           "bootstrap_B": pooled.B},
              "metrics": avail, "scores_md5": md5, "oracles": oracle, "kappa": kappas,
              "env": environment(metrics)}
    (out / "report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    (out / "report.md").write_text(markdown(scored, metrics, avail, kappas, oracle, md5), encoding="utf-8")
    if not quiet:
        print(f"{len(scored)} rows -> {out / 'scores.csv'} (md5 {md5}); report.md / report.json beside it")
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def scoring(p):
        p.add_argument("pairs", type=Path, help="CSV or JSON pair list")
        p.add_argument("--out", type=Path, required=True, help="folder for scores.csv, report.md, report.json")
        p.add_argument("--metrics", nargs="*", choices=METRICS, help="score only these (default: all)")
        p.add_argument("--tie-band", type=float, default=0.0,
                       help="instrument tie when |after-before| <= band * max(|before|,|after|) (default 0)")
        p.add_argument("--ppm", type=float, default=DEFAULT_PPM, help=f"render px per mm (default {DEFAULT_PPM})")
        p.add_argument("--pad-mm", type=float, default=DEFAULT_PAD_MM)
        p.add_argument("--max-px", type=int, default=DEFAULT_MAX_PX, help="cap on the render's long side")
        p.add_argument("--no-register", action="store_true", help="draw ours as the file lies, unaligned")
        p.add_argument("--colour", action="store_true", help="keep thread colours (default: monochrome)")
        p.add_argument("--dreamsim-type", default="ensemble",
                       help="dreamsim backbone: ensemble (default), dino_vitb16, clip_vitb32, open_clip_vitb32")
        p.add_argument("--quiet", action="store_true")

    s = sub.add_parser("score", help="score every pair; with labels, the kappa against them")
    scoring(s)
    s.add_argument("--labels", nargs="?", const=True, default=None, metavar="PATH",
                   help="read Kent's picks: from the pair list's label column, or from PATH (pair_id,label)")
    s.add_argument("--oracles", action="store_true", help="add the self and blank-canvas rows and check them")
    o = sub.add_parser("oracle", help="score the pairs plus the self / blank oracles; exit 1 if one fails")
    scoring(o)
    f = sub.add_parser("from-pro-pooled", help="pair list from Kent's labelled pro pairs and a render dir")
    f.add_argument("--runs", type=Path, required=True, help="pro_pooled_build.py render --runs DIR")
    f.add_argument("--inputs", type=Path, default=None, help="pro-pair-inputs.json (default: the committed one)")
    f.add_argument("--out", type=Path, required=True, help="pairs CSV (or .json) to write")
    t = sub.add_parser("from-tripwire", help="pair list from the committed tripwire jobs and a digitize dir")
    t.add_argument("--runs", type=Path, required=True, help="pro_baseline.py digitize --runs DIR")
    t.add_argument("--out", type=Path, required=True)
    sub.add_parser("metrics", help="which metrics this interpreter can score, and why not")
    a = ap.parse_args(argv)

    if a.cmd == "metrics":
        for name, why in availability(make_metrics()).items():
            print(f"{name}: {'ok' if why is None else 'n/a -- ' + why}")
        return 0
    if a.cmd == "from-pro-pooled":
        return from_pro_pooled(a.runs, a.inputs, a.out)
    if a.cmd == "from-tripwire":
        return from_tripwire(a.runs, a.out)
    rep = run(a.pairs, a.out, labels=getattr(a, "labels", None), metrics_only=a.metrics,
              oracles=(a.cmd == "oracle" or getattr(a, "oracles", False)), tie_band=a.tie_band,
              ppm=a.ppm, pad_mm=a.pad_mm, max_px=a.max_px, register=not a.no_register, mono=not a.colour,
              dreamsim_type=a.dreamsim_type, quiet=a.quiet)
    if a.cmd == "oracle":
        bad = [(n, o) for n, o in rep["oracles"].items()
               if "unavailable" not in o and not (o["self_zero"] and o["blank_worst"])]
        for n, o in bad:
            print(f"ORACLE FAILED {n}: self_zero={o['self_zero']} blank_worst={o['blank_worst']} "
                  f"worst_self={o['worst_self']} blank_min={o['blank_min']} pair_max={o['pair_max']}")
        return 1 if bad else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
