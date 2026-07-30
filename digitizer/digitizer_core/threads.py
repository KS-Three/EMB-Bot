"""Thread chart access: Lab-space nearest matching and snap-with-merge.

Color-space convention (PINNED — see plan doc): all color math runs in
CIELAB as produced by skimage.color.rgb2lab on float RGB in [0, 1] — i.e.
true CIELAB ranges (L 0-100, a/b roughly -128..127). cv2's 8-bit Lab
(scaled 0-255) is never mixed in; anything arriving as cv2 Lab must be
converted back to RGB first.

Two different distances, deliberately:
  * **Spool snapping uses CIEDE2000** — the perceptual standard. Measured
    during step-1 development: plain CIE76 matched a dark navy (20,40,90) to
    a GREY thread ("Concord Fog"), because Euclidean Lab distance is a poor
    perceptual model in dark saturated regions. CIEDE2000 picks "Midnight
    Blue". The operator buys the cone this function names, so this is a
    quality-critical path, and the cost is trivial (a dozen cluster colors
    against ~400 threads).
  * **Cluster merging and the anti-alias blend test use Euclidean Lab**
    (stage 2) — those need a metric geometry to project onto a line between
    two colors, which CIEDE2000 does not provide.

**Which chart** is a parameter, not a constant (build step 8). Kent's Studio
carries a thread-brand preference and the operator buys cones in that brand;
naming an Isacord number to someone standing at a Madeira rack is a defect, not
a rounding error. `chart_for(cfg)` resolves it; `CHART` remains the default
brand's chart so existing call sites and goldens are unaffected.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from skimage.color import deltaE_ciede2000, rgb2lab

_CHART_DIR = Path(__file__).resolve().parent / "chart_data"

# Isacord is the default because it is what the shop runs and what every golden
# test in this package is pinned to. Changing this changes goldens.
DEFAULT_BRAND = "isacord"


@dataclass(frozen=True)
class Thread:
    number: str
    name: str
    rgb: tuple[int, int, int]


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """(N,3) uint8/float RGB (0-255) -> (N,3) float CIELAB."""
    arr = np.asarray(rgb, dtype=np.float64).reshape(1, -1, 3) / 255.0
    return rgb2lab(arr).reshape(-1, 3)


class Chart:
    """One manufacturer's thread line, with its Lab precomputed once.

    Indexable and iterable like the plain list it replaced, so `chart[i].name`
    keeps working everywhere it already did.
    """

    __slots__ = ("id", "label", "threads", "_lab")

    def __init__(self, brand_id: str, label: str, threads: list[Thread]):
        self.id = brand_id
        self.label = label
        self.threads = threads
        self._lab = rgb_to_lab(np.array([t.rgb for t in threads], dtype=np.float64))

    def __len__(self) -> int:
        return len(self.threads)

    def __getitem__(self, i: int) -> Thread:
        return self.threads[i]

    def __iter__(self):
        return iter(self.threads)

    def __repr__(self) -> str:
        return f"<Chart {self.id!r} {len(self.threads)} threads>"

    @property
    def lab(self) -> np.ndarray:
        return self._lab

    def nearest_index(self, lab: np.ndarray) -> int:
        """Index of the perceptually nearest (CIEDE2000) thread.

        Ties resolve to the lower chart index (argmin), which is deterministic
        because a chart is a fixed, ordered list.
        """
        ref = np.repeat(np.asarray(lab, dtype=np.float64).reshape(1, 3), len(self._lab), axis=0)
        return int(np.argmin(deltaE_ciede2000(ref, self._lab)))

    def snap_palette(self, cluster_rgbs: np.ndarray) -> list[int]:
        """Snap each cluster color (N,3 RGB 0-255) to a chart index.

        Returns one chart index per cluster, in cluster order. Merging clusters
        that land on the same spool is the CALLER's job (stage 2) because it
        must also remap the label image.
        """
        return [self.nearest_index(lab) for lab in rgb_to_lab(cluster_rgbs)]


@lru_cache(maxsize=8)
def load_chart(brand_id: str = DEFAULT_BRAND) -> Chart:
    """Load a brand's chart by id. Cached — the Lab precompute is not free.

    Brand ids are the ones the browser uses (`app/src/lib/threadBrandsIndex.js`);
    an unknown id is an error rather than a silent fall back to Isacord, because
    silently substituting a different manufacturer's numbers is exactly the
    defect this parameter exists to prevent.
    """
    path = _CHART_DIR / f"{brand_id}.json"
    if not path.is_file():
        raise KeyError(f"unknown thread brand {brand_id!r} (see chart_data/index.json)")
    data = json.loads(path.read_text(encoding="utf-8"))
    threads = [Thread(num, name, (r, g, b)) for num, name, (r, g, b) in data["threads"]]
    return Chart(data["id"], data["label"], threads)


@lru_cache(maxsize=1)
def brand_index() -> list[dict]:
    """[{id, label, count}] for every shipped brand, sorted by id."""
    return json.loads((_CHART_DIR / "index.json").read_text(encoding="utf-8"))


def chart_for(cfg) -> Chart:
    """The chart a PipelineConfig names. Accepts None for the default."""
    return load_chart(getattr(cfg, "thread_brand", None) or DEFAULT_BRAND)


# The default chart, eagerly resolved: every golden in this package is pinned to
# Isacord, and a module-level name keeps the pre-step-8 call sites honest.
CHART: Chart = load_chart(DEFAULT_BRAND)


def nearest_thread_index(lab: np.ndarray) -> int:
    """Nearest thread in the DEFAULT chart. Brand-aware code calls
    `chart_for(cfg).nearest_index` instead."""
    return CHART.nearest_index(lab)


def snap_palette(cluster_rgbs: np.ndarray) -> list[int]:
    """Snap against the DEFAULT chart. Brand-aware code calls
    `chart_for(cfg).snap_palette` instead."""
    return CHART.snap_palette(cluster_rgbs)
