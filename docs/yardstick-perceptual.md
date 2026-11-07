# Perceptual yardstick: FLIP, LPIPS, DreamSim against Kent's eye

`tools/yardstick_perceptual.py` scores three off-the-shelf perceptual
distances (NVIDIA FLIP; LPIPS on AlexNet and VGG; DreamSim) between a
rendered "ours" stitch file and a rendered reference, for a list of pairs,
and — when Kent's picks are attached — reads each metric's agreement with
him as Cohen's kappa with a bootstrap 95% interval. **No raw agreement
share is computed anywhere** (ROADMAP gate 4). It is phase 1's open
question in instrument form: `docs/lagging-areas-2026-11-06/1-yardstick.md`
recommends trying these three because no instrument the repo owns clears
chance against his 115 labelled pairs except the trim family, and the
blind Claude judge cleared only on ties and plain damage
(`.claude/memory/vlm-judge-2026-11-04.md`, kappa +0.36 [+0.16, +0.55]).

**Status (2026-11-07): the kappa against Kent is NOT measured.** His labels'
renders and the pro files exist only on his laptop, so a cloud session built
and validated the instrument (determinism, the two sanity oracles, 18
committed tripwire pairs) and stops there. The one command he runs is in
"Kent's run" below.

## What a pair is, and what gets rendered

Each row of the pair list is two machine files. Both are drawn through the
repo's own stitch renderer (`digitizer_core.stitchviz.render_design`, the
pro-parity overlay's frame and clipping) on ONE canvas: the reference's sewn
extent plus `--pad-mm` (3 mm), at `--ppm` px/mm (12, the pair pages' scale),
the long side capped at `--max-px` (1024). Ours is registered onto the
reference first — scale, y-flip and translation from
`pairframe.register_pair`, the same alignment the pro-pair figures use — so
a metric reads construction, not where the file sat in its hoop
(`--no-register` to see it as the file lies). Both sides render monochrome:
a PES carries thread colours, a DST none, and colour order is not what is
being judged (`--colour` keeps them). The `reg_iou` and `reg_scale` columns
say how well the two aligned; a low IoU means the metric is reading two
files that share little thread.

Every metric is a **distance**: 0 for identical renders, larger is worse.

| column | what | package |
|---|---|---|
| `mse` | pixel control: mean squared difference in [0, 1]. A perceptual metric that cannot beat this has earned nothing. | none (always scores) |
| `flip` | NVIDIA FLIP, LDR, 67 pixels per degree, mean over the error map | `flip-evaluator` |
| `lpips_alex`, `lpips_vgg` | Learned Perceptual Image Patch Similarity, both backbones | `lpips`, `torch` (CPU) |
| `dreamsim` | DreamSim, 1 − cosine of the ensemble embedding (224 px, the package's own preprocessing) | `dreamsim`, `torch`; weights fetched once to `~/.cache/dreamsim` (or `YARDSTICK_DREAMSIM_CACHE`) |

A metric whose package is missing is a column of `n/a`; `report.json`
carries the reason per metric, and `python tools/yardstick_perceptual.py
metrics` prints the same before anything is rendered.

## Install — a separate venv, never the digitizer's

The heavy packages live in `tools/requirements-yardstick.txt`, deliberately
apart from `digitizer/requirements.txt` (which CI and the service install):

```bash
python3.12 -m venv .venv-yardstick
.venv-yardstick/bin/pip install -r digitizer/requirements.txt -r tools/requirements-yardstick.txt
```

On Windows the second line is `.venv-yardstick\Scripts\pip install ...`.
The requirements file asks the PyTorch CPU index for torch; where that index
is unreachable (the cloud containers, proxy 403) pip falls back to the PyPI
wheel, which works but pulls CUDA libraries it never uses.

## Pair list

CSV with a header row, or a JSON list of objects:

| column | meaning |
|---|---|
| `ours_path` | the engine's machine file (DST, PES, ...) |
| `ref_path` | what it is measured against — the pro's file, or the other arm |
| `id` | optional; defaults to the two stems |
| `label` | optional: Kent's pick on an A/B pair — `before`, `after`, `same`, `both_bad` (or `tie`) |
| `pair_id` | with `label`: the two rows of one A/B pair share it |
| `arm` | with `label`: `before` or `after`, which side this row is |
| `design` | optional cluster for the second bootstrap (defaults to the reference's stem) |

Relative paths resolve against the list's own folder. A labelled pair is two
rows — before arm vs the pro, after arm vs the pro — and the instrument's
pick is the arm whose render is closer to the pro (equal within
`--tie-band`, default exactly equal, is a tie). That is the shape of the
10-11 and 11-01 pooled readings, so the kappa here is comparable to those.

Two builders write the list for you:

- `from-pro-pooled --runs DIR --out pairs.csv`: Kent's labelled pairs with
  a pro file (`docs/eye-pairs-2026-11-01/pro-pair-inputs.json`, 100 pairs,
  41 decided), each arm's `ours.dst` under the `pro_pooled_build.py render`
  layout `DIR/<tree>/<fixture>/<side>/`, labels and `design` (the fixture)
  filled in. Pairs whose render is missing are listed to stderr and skipped.
- `from-tripwire --runs DIR --out pairs.csv`: the 18 committed tripwire
  jobs, unlabelled, from a `pro_baseline.py digitize --runs DIR` directory.

## Kent's run

The 100 labelled pro pairs' renders are the `pro_pooled_build.py render`
directory from 2026-11-01 (`RUNS` below; if it is gone, re-render per the
vlm-judge memory's "one next step", ~3 h under the CPU lock). Then:

```bash
.venv-yardstick/bin/python tools/yardstick_perceptual.py from-pro-pooled --runs RUNS --out out/yardstick/pairs.csv
```

```bash
.venv-yardstick/bin/python tools/yardstick_perceptual.py score out/yardstick/pairs.csv --labels --oracles --out out/yardstick
```

`out/yardstick/report.md` has the kappa table (`report.json` the same with
the 3×3 tables and intervals); `scores.csv` is the per-pair table and its
md5 is printed, so a second run can be checked byte-for-byte. The
`pro-lettering-1102` sitting (54 live pairs, the one whose renders survive
at `digitizer/eye_pairs_out/pro-lettering-1102/`) is not covered by the
builder: its arms are the picker page's JPEGs, not machine files, and would
need a hand-written pair list from its `arms.json`.

`--labels` on its own reads the pair list's `label` column; `--labels
PATH` takes a separate CSV or JSON of `pair_id,label[,design]` so the picks
can live apart from the paths.

## Reading the result

The report gives, per metric, over the pairs it could score:

- the 3-way linear-weighted kappa with ties in, its percentile bootstrap
  interval over pairs and over designs (B = 10,000, seed fixed), and the
  `pooled.reading` verdict: **`above chance` only when BOTH intervals sit
  above zero**, `no evidence either way` otherwise, nothing read under 10
  pairs;
- the plain 2×2 kappa on the pairs both Kent and the metric decided, same
  intervals;
- `worse pairs`: pairs Kent decided where the metric chose the other side —
  the exit's second clause ("nothing he judges better ever scores worse")
  needs this at 0;
- how often the metric called a tie on a pair Kent decided.

What would count as clearing chance: a metric whose 3-way interval over
pairs AND over designs both exclude zero on the 100 pairs, and whose 2×2
interval on the ~41 decided pairs does too. For scale: the best instrument
so far, needle-up hops, reads +0.24 [+0.10, +0.39] over pairs and [+0.11,
+0.34] over designs on those 100 (`docs/yardstick-pro-pair-vs-kents-eye-2026-11-01.md`),
and the blind Claude judge +0.36 [+0.16, +0.55] on a different 54. Quote
the kappa with both intervals and n; never a share. Kent's own repeat
agreement on the 11-02 sitting was 1 of 4, so a metric that tracks him at
+0.4 is tracking a noisy target, not a ceiling.

## Validation that is done (2026-11-07, cloud, python 3.12, torch 2.15)

Over the 18 committed tripwire pairs (`from-tripwire` on a fresh
`pro_baseline.py digitize`, ours vs the pro's DST):

| metric | self reads 0 | blank is worst | how it was run |
|---|---|---|---|
| `mse` | yes | yes | digitizer venv and yardstick venv |
| `flip` | yes | yes | `flip-evaluator` 1.7 |
| `dreamsim` | yes | yes | `dreamsim` 0.2.1, ensemble; see the proxy note below |
| `lpips_alex`, `lpips_vgg` | not measured | not measured | the ImageNet backbones could not be downloaded |

- **Determinism**: two runs give one `scores.csv` md5 with `mse`, `flip`
  and `dreamsim` (every score to 6 decimals, fixed column order; a
  rounded −0 is written as 0 so the md5 does not hang on the sign of noise).
- **A near-identical pair scores near zero**: the pro's own PES and DST of
  one design read `mse` 0.0011 against a blank of 0.49.
- **The pytest** (`digitizer/tests/test_yardstick_perceptual.py`) runs the
  oracles over whatever is installed: on CI and in the digitizer venv only
  the control; in the yardstick venv every metric that loads.

**Proxy note.** A first DreamSim run fetches from `github.com` (its
checkpoints), `api.github.com` and `codeload.github.com` (`torch.hub` for the
DINO code), and `dl.fbaipublicfiles.com` (DINO's backbone); LPIPS fetches
its AlexNet / VGG backbones from `download.pytorch.org`. The cloud container
allowed only the first. DreamSim was run there by cloning the DINO repo into
the hub cache with git and rebuilding DINO's published backbone file from
the teacher weights in DreamSim's own checkpoint, a strict state-dict load
that would have failed on any mismatch. That workaround lives in the
session's scratch folder, not in the tool. LPIPS's code path was checked
with a random backbone and the package's real linear layers: self 0, blank
highest. That says nothing about LPIPS as a metric. On a laptop with open
network none of this applies: the first run downloads everything once.

Not done: the kappa against Kent (his renders and labels are on his
laptop), and LPIPS with its real weights.
