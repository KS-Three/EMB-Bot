"""Python 3.12 venv, vtracer only. Three variants per run dir:
  b1  masks/        vtracer defaults (binary, spline)
  b2  masks/        tuned to smooth: corner_threshold 120
  b3  masks_native/ defaults, on the source's own pixel grid
Probes the keyword-argument call in a child process first, because the
2026-08-17 evaluation saw it segfault on 3.14 and never tried 3.12."""
import subprocess
import sys
import time
from pathlib import Path

import vtracer

BASE = dict(colormode="binary", hierarchical="stacked", mode="spline", filter_speckle=4,
            color_precision=6, layer_difference=16, corner_threshold=60,
            length_threshold=4.0, max_iterations=10, splice_threshold=45, path_precision=3)
VARIANTS = {
    "m": ("masks", {**BASE, "mode": "none", "filter_speckle": 0}),
    "b1": ("masks", BASE),
    "b2": ("masks", {**BASE, "corner_threshold": 120}),
    "b3": ("masks_native", {**BASE, "filter_speckle": 1}),
}


def probe(png):
    code = ("import vtracer,sys;"
            f"vtracer.convert_image_to_svg_py(sys.argv[1], sys.argv[1]+'.probe.svg', **{BASE!r})")
    r = subprocess.run([sys.executable, "-c", code, str(png)], capture_output=True)
    Path(str(png) + ".probe.svg").unlink(missing_ok=True)
    return r.returncode


def main(dirs):
    first = next(Path(dirs[0], "masks").glob("m*.png"))
    print(f"python {sys.version.split()[0]} keyword-arg call exit code: {probe(first)}")
    for name, (sub, kw) in VARIANTS.items():
        t, n = time.time(), 0
        for d in dirs:
            for p in sorted(Path(d, sub).glob("m*.png")):
                vtracer.convert_image_to_svg_py(str(p), str(p.with_suffix(f".{name}.svg")), **kw)
                n += 1
        print(f"{name}: traced {n} masks in {time.time() - t:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1:])
