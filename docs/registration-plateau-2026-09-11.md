# The registration search had no way out of a flat zero — 2026-09-11

`scorecard.register` could return a wrong alignment with `iou=0.0` and say
nothing. Reported from a synthetic fixture; investigated against the real
corpus; fixed; **no real pair hits it, and that is a measurement, not a
guess.**

## What was broken

`pairframe.register_pair` pre-shifts ours by the bbox-centre delta and then
calls `scorecard.register`, which seeds at `(0, 0)` **and** at the bbox-centre
delta *of what it was handed*. By then that is already centred, so
**both of its seeds are the same point** — the two-seed search is a one-seed
search in the one caller that matters.

A bbox centre is dragged by half the excursion of any element **one** side
sews. When the shared geometry is narrower than the resulting error, the two
solid masks touch **nowhere**: all eight 1 mm probes read zero, there is no
gradient in any direction, and the climb returns the bad seed.

Measured on the reported fixture (one shared satin bar, plus extra bars at
different distances on each side):

```
register_pair -> Reg(scale=1.0, flip_y=False, dx=0.0, dy=-4.0, iou=0.0)
truth         -> dy=0.0, iou=0.404
```

The IoU landscape, probed at 0.5 mm — a flat zero across the whole
neighbourhood the search can see, with a **decoy** peak on the far side:

| dy | −6 | −5 | −4 | −3 | −2 | 0 | +2 | +3 | +4 | +5 | +6 |
|----|----|----|----|----|----|---|----|----|----|----|----|
| IoU | 0.000 | 0.046 | **0.165** | 0.046 | 0.000 | **0.000 ← seed** | 0.000 | 0.102 | **0.404** | 0.102 | 0.000 |

## Does any REAL pair hit it? Not as prepped — but the mechanism is real

The prepped customer corpus, and then the scenario the report named ("the pro
sews a large extra element the digitizer completely missed, or vice versa"),
built out of **real** stitch geometry rather than fixtures.

*Coverage: 17 of the 23 `prep_all.DESIGNS`, ~130 registrations. Not yet
measured: `gaulke_plowing_lc`, `gaulke_jb`, `proseal_hat`, `proseal_beanie`,
`hotel_fremont_hat`, `hotel_fremont_patch` — each needs a 3–20 min engine run
and none had finished when this was written. Both gaulke roofing designs and
`gaulke_plowing_hat` ARE included, which is the family that matters here.*

- **Every real pair as prepped**: the greedy search already sat exactly on the
  exhaustive optimum of its own objective (gap `+0.0000` on every one). Seed
  error under 0.5 mm everywhere except `gaulke_plowing_hat` (3.4 mm) and
  `machine_beanie`, whose famous −26.65 mm offset the centroid seed handles
  correctly.
- **Losing a whole spatial extremity** on `becker` (real independent artwork,
  not art reconstructed from the pro file): dropping 75% of one side pulls the
  centroid **23.8 mm** — and the search *still* lands on the exhaustive
  optimum at every step of the ladder.
- **But under the element-drop stress, one real arm DOES miss.** Delete colour
  block 0 from our `gaulke_roofing_hat` and the old search returns
  `iou 0.0036 @ (+2.00, −0.50)` where the exhaustive optimum — which the new
  search finds — is `iou 0.0068 @ (−15.00, +4.75)`. That is **17.79 mm** of
  wrong alignment, on real thread, in the very design `pairframe.py` singles
  out as the re-composed one.

**And it is bounded by sparsity, measured.** Ranking every element-drop arm by
fill ratio (solid thread area / bbox area of the thinner side — the quantity
deciding whether a few mm of seed error still overlaps anything):

| fill ratio | arms | old vs new |
|---|---|---|
| 0.000 – 0.003 | 3 | **1 miss** (`gaulke_roofing_hat` blk 0, 17.79 mm apart) |
| 0.222 – 0.916 | 45 | 45/45 identical alignment |

Nothing in between: the corpus jumps from 0.003 to 0.222. So the old search is
exact wherever thread actually fills its frame, and fails only where what is
left is **scraps** — 0.99 m of our thread against the pro's 13.02 m. You do not
reach that regime by digitizing badly; you reach it by deleting most of one
side. No as-prepped pair is close to it.

**Why normal real data is immune:** a real logo is a dense blob. Slide it 30 mm
and it still overlaps itself — on `becker`, IoU is non-zero across the entire
±30 mm sweep in both axes and smoothly unimodal. The plateau needs the two
masks to be **disjoint at the seed**, which needs *sparse, thin* geometry with
large empty gaps. That is what synthetic fixtures are made of and what customer
logos are not.

Two caveats that keep this honest:

- `prep_all.reconstruct` builds `art.png` **from the pro file's own stitches**,
  so the corpus systematically understates the mismatch (IoU ~0.91–0.99). The
  one pair digitized from Kent's real artwork, `becker_smoke`, scores 0.64.
  The extremity ladder above was run on that pair for exactly this reason.
- Two `tires_hat_3d` arms register at IoU ≈ 0.001. That is **not** a collapse:
  verified exhaustively, the search is at the optimum — dropping that block
  leaves 1.58 m of our thread against 23 m of the pro's, so the union is
  genuinely dominated.

## The fix, and why not a grid

A coarse grid was the obvious suggestion and it is the wrong tool **twice
over**:

- **Unaffordable.** 2 mm steps = 1,257 legal points ≈ **73 s**, against
  **4.9 s** for the entire present search.
- **Still unsafe.** A basin can be one thread wide. This fixture's is 2 mm, so
  a 4 mm grid steps clean over it. Making the grid fine enough to guarantee
  capture costs ~5,000 evaluations.

What works instead is one FFT. IoU = `inter / (|A| + |B| − inter)` rises
strictly with `inter` whenever `|A|` and `|B|` are fixed — which under a
translation of a **zero-padded** mask they are. So the cross-correlation peak
**is** the IoU optimum, scanned at 0.5 mm over every offset inside `REG_MAX`,
for 7–85 ms. Those peaks are added as *seeds*; the exact objective still
scores and polishes them, and the original seeds are still climbed.

## The second defect, which only appeared once the search got stronger

`bounds()` pads 8 mm. The search may move ours **40**. A shift that carried
thread off the raster had it silently dropped from the union — **which raises
IoU**. The search was being paid to slide ours out of frame.

The old local climb rarely reached far enough to collect that bonus. A search
that actually explores does: on this fixture the y-flipped arm scored **0.494**
against the correct **0.404**, purely because 15 of its 44 mm² had left the
frame — and it *won*, so `register_pair` returned a spurious flip. Fixed by
padding the search frame by `REG_MAX`, which also makes `|ours|`
translation-invariant — the assumption the correlation argument rests on.

**The lesson worth keeping: strengthening a search against a flawed objective
finds the flaw.** The clipping bug was years-old and harmless only because
nothing was strong enough to exploit it. Anywhere we sharpen an optimiser, the
next thing to check is whether its objective deserves the sharpening.

## Cost

+9% on `becker` (4.9 s → 5.3 s); 1.6× on a worst-case 380 mm, 48k-segment slab
(4.7 s → 7.7 s). The FFT itself is 0.3 s of that; the rest is the extra seed
earning its own hill-climb.

## Still open

`register` returns `iou=0.0` **without complaining**. The smoke test asserts
`reg.iou > 0.5`, but `overlay.py` / `diff.py` consume the `Reg` unchecked, so a
future sparse pair would again be scored off a wrong alignment silently. A
floor-with-a-warning in `register_pair` is not written.
