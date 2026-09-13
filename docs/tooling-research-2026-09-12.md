# External tooling for digitizing quality — two research passes, 2026-09-12

Kent's question: *are there repos, MCPs, Connectors or plugins that would improve
EMB-Bot's digitizing quality?* — with a hard **"nothing paid"** constraint added
partway through.

Two independent passes ran. Both are recorded here because they failed in
**different** places, and the overlap is where the confidence is.

- **Pass A — verified web research.** 102 agents, 20 sources fetched, 100 claims
  extracted, 25 taken to a 3-vote adversarial review (2-of-3 refutes kills),
  11 confirmed / 14 killed / 9 dropped on budget, 7 findings after synthesis.
  ~113 minutes. Primary sources only; the sessions could not reach the GitHub
  API or code search (proxy 403/405), so every fact came from unauthenticated
  `raw.githubusercontent.com` fetches and PyPI JSON/wheel inspection.
- **Pass B — hand sweep of indexes Pass A does not query.** The Hugging Face Hub
  API (via the `huggingface` MCP server added the same day), the PyPI JSON API,
  and the arXiv API.

**Nothing here was measured against EMB-Bot's corpus.** No claim below
establishes a quality gain. The strongest positive result is a *portable
algorithm*; everything else is licensing triage or a closed dead end.

---

## The one-line answer

**There is no repo, model, MCP server, Connector or plugin that measurably
improves digitizing quality today.** The field is thin: no maintained
open-source digitizing engine exists besides Ink/Stitch (GPL-3.0) and the I/O
libraries, and auto-digitizing has essentially no academic literature. What does
exist is *components* — offsetting, skeleton graphs, solvers, vectorizers — plus
one reimplementable routing algorithm. The leverage is in **picking the
permissively-licensed component and porting the algorithm**, not in adopting a
product.

---

## 1. The one genuinely actionable finding

**Ink/Stitch's travel router is not a TSP solve, and it is reimplementable on
what EMB-Bot already pins.** Confirmed 3-0, line-by-line against the 302-line
`lib/stitches/utils/autoroute.py` fetched from `main` on 2026-09-12.

Two mechanisms, both pure `networkx` (BSD) + `shapely`, both already
dependencies:

1. **Jump minimization** — one call:
   `nx.k_edge_augmentation(graph, 1, avail=possible_jumps(graph))`, over
   nearest-point candidate edges between connected components, weighted by jump
   length. Provably optimal at k=1 (it reduces to an MST over the component
   meta-graph). `possible_jumps()` iterates `combinations(nx.connected_components(graph), 2)`.
2. **Traversal order with underpathing** — `nx.shortest_path(start, end)`, those
   edges deleted, then a DFS from each node on that path where edges are
   appended a **second time on backtrack**, specifically to create underpath.
   Dead-ends are sewn down-and-back.

The underpath *semantics* are confirmed in the caller (`auto_satin.py`
`path_to_operations()`): a section appearing twice in the path is sewn first as
running stitch and later covered by the satin, tagged
`inkstitch:path_type = 'satin-underpath'`.

**What it will NOT do — bill it honestly.** It minimizes jump *length* and hides
travel under later stitching. It touches **neither** the jump-vs-trim threshold
**nor** defect 4's anomaly (542 pro cuts at min 1.9 mm overlapping 368 uncut
floats to 16.1 mm). **Porting autoroute alone will not close the 3.1x trim-break
gap.** It is an underpathing mechanism, not a trim policy.

**Licence route:** GPL protects expression, not algorithms, so
description-level reimplementation is the accepted path — but see §2, because
this repo's licence posture makes the bar higher than usual.

---

## 2. Licensing triage — the part that would have cost real money

### Ink/Stitch is DESCRIPTION-ONLY. Confirmed 3-0.

Per-file headers, fetched verbatim from `main`, on exactly the modules EMB-Bot
would want — `auto_satin.py`, `running_stitch.py`, `autoroute.py`, `fill.py`,
`tatami_fill.py`:

> `# Copyright (c) 2010 Authors`
> `# Licensed under the GNU GPL version 3.0 or later.  See the file LICENSE for details.`

Root `LICENSE` is the plain 674-line GPLv3 with **no linking exception**. A
commercial blog's claim of ACSL dual-licensing was checked at the primary source
and **disproven** (`grep -c -i 'anti-capitalist'` returns 0; no ACSL file
exists). Not stale — Ink/Stitch shipped v3.3.0 on 2026-07-31.

**Sub-finding that cuts toward MORE caution:** `contour_fill.py`,
`meander_fill.py`, `circular_fill.py`, `guided_fill.py` and `ripple_stitch.py`
carry **no per-file header at all** — and these are stitch types EMB-Bot already
implements. A session could plausibly read "no header" as "no licence". It is
not; the root LICENSE covers them.

**Practical barrier independent of licence:** `autoroute.py` imports `inkex`
plus three-package-levels-up internals (`...elements import SatinColumn`,
`...svg import get_correction_transform`, `...svg.tags import INKSCAPE_LABEL`,
`...utils.threading import check_stop_flag`). It is not importable or
pip-installable. Reuse means porting ~114 lines of graph logic, never copying.
*(Expiry: Ink/Stitch says real PyPI packaging is in progress — the
"not pip-installable" fact will lapse; the GPL fact will not.)*

### Our own licence posture is the sharper end of this

Verified locally: `digitizer/pyproject.toml` line 6 is
`license = { text = "Proprietary" }`, and `ls -a` at the repo root returns **no
LICENSE, COPYING or NOTICE of any kind** — in a world-readable repo.

The report's recommendation, which is Kent's call and not a session's: for a
public repo with this licence history, a **genuine two-person clean-room split**
(one person reads and describes, a different person implements) is meaningfully
stronger than read-then-write. *This is not legal advice.*

### The three traps in Pass B — each is the FIRST thing you would reach for

| Need | Obvious choice — contaminated | Clean alternative |
|---|---|---|
| Raster→vector tracing (problem 4) | `pypotrace` **GPL** · `potracer` **GPLv2+** | **`vtracer`** MIT, 0.6.15, 2026-03-23 |
| Triangulation | `triangle` **LGPL-3.0** (Shewchuk's own terms are non-commercial) | **`mapbox-earcut`** ISC, 2.1.0, 2026-09-08 |
| Travel/trim sequencing (problem 3) | `elkai` — licence field literally reads "elkai License"; LKH is academic-only | **`ortools`** Apache-2.0, 9.15, 2026-01-14 |

### RMBG-2.0 is a HARD commercial blocker — worse than GPL. Confirmed 3-0.

Model card verbatim: *"released under a CC BY-NC 4.0 license for non-commercial
use. Commercial use is subject to a commercial agreement with BRIA."* The
self-hosted purchase link resolves to a **HubSpot lead-capture form** — a
contact-sales funnel, no checkout; `bria.ai/pricing` lists self-hosted only in
Enterprise at "Custom pricing". The repo is gated (`raw` README returns *"Access
to model briaai/RMBG-2.0 is restricted… Please log in"*; LICENSE returns 401).

The GPL contrast is technically sound, not rhetoric: **GPL-3.0 permits
commercial sale subject to copyleft; CC BY-NC forbids commercial use outright
absent a paid agreement.** Non-commercial benchmarking is permitted.

Pass B reached the same conclusion independently from the Hub tag
(`briaai/RMBG-2.0` and `RMBG-1.4` both `license:other`, 691K and 381K
downloads) — two methods, same answer.

### pystitch is clean, and the incumbent choice is validated

MIT at the repo, in PyPI metadata, **and in the pinned 1.0.1 wheel**: METADATA
says `License-Expression: MIT`, it ships `dist-info/licenses/LICENSE`, a byte
scan of all 98 files found **zero** occurrences of `GPL` / `GNU General Public` /
`copyleft`, and there are **no `Requires-Dist` lines at all** — no transitive
copyleft either. Lineage checked for a covert relicence: upstream
`EmbroidePy/pyembroidery`'s LICENSE is byte-identical MIT, so pystitch inherited
MIT rather than changing it.

Pass B corroborates the maintenance half: **`pyembroidery` last shipped
2024-03-27; `pystitch` 2026-06-19.** The fork swap was right and needs no
revisiting.

Two nits: the legacy PyPI `info.license` field is **null** (MIT lives in the PEP
639 `License-Expression` field), so a session grepping only the old field could
misread it as unlicensed. And MIT still requires the notice ship in
distributions.

**But:** pystitch's READ-format breadth was **refuted 0-3** — the claim that it
reads 40 formats including `.jef`/`.vp3` did not survive. **Problem 5's ingest
half is NOT confirmed solved by the incumbent.**

### `manthrax/dst-format` is unusable

No licence of any kind. Every plausible path 404s on `master`. Cannot be
vendored or adapted.

---

## 3. Segmentation — no verified improvement on the binding constraint

This is the disappointing half, and it matters most: **problem 1 is the binding
constraint** (pipeline 55.4% vs a 76.6% oracle on satin-vs-fill routing), and
this pass found **no verified gain on it**.

### BiRefNet — best scores, zero graphic-art evidence. Confirmed 3-0 (medium).

Flagship general-use model posts **0.927 S-measure / 0.894 weighted-F / 881 HCE**
on DIS-VD — the best DIS-VD row in its own zoo (vs 0.911/0.907/0.882 S; 881 vs
1069/1059/1175 HCE). Self-reported by the authors, not independently reproduced.

The zoo was enumerated exhaustively (README lines 164-187) and **every training
corpus is photographic**: DIS5K (Flickr photos), COD10K/CAMO (camouflaged
photos), DUTS/HRSOD/UHRSD/HRS10K (salient-object photos),
P3M-10k/PPM-100/HIM2K/AM-2k/Distinctions-646/AIM-500 (human or natural-image
matting). A keyword sweep for
`logo|graphic|cartoon|anime|toon|illustrat|vector|clipart|line art|comic|sketch|typograph`
across the whole 467-line README returns only shields.io badge URLs. The paper
(arXiv 2401.03407) evaluates only DIS, HRSOD and COD.

The strongest counter-evidence found actually **corroborates**: the README links
a third-party fine-tune (`MatteoKartoon/BiRefNet` "ToonOut", arXiv 2509.06839)
on custom anime data, whose comparison image shows improvement on stylized
content — i.e. the maintainers themselves surface evidence that base BiRefNet
underperforms off photographs.

> **State this correctly.** This is an **absence of evidence**, NOT a measurement
> that BiRefNet performs badly on logo art. The stronger version is unsupported.
> It means: **cannot be recommended for problem 1 without an in-house
> measurement.**

**Licence, settled here rather than in Pass A.** The claim *"BiRefNet is MIT for
BOTH code and published weights"* was **refuted 0-3**, and Pass B found why:
`ZhengPeng7/BiRefNet` (the weights repo) declares `license: mit` **in its model
card's YAML front matter** and ships **no LICENSE file at all** — 9 files, none a
licence (verified via `hf_fs find --name *LICENSE*` → zero entries, 2026-09-12).
A card tag is a publisher declaration, not a licence grant, and the code repo
(`github.com/ZhengPeng7/BiRefNet`) was **not** licence-verified in either pass.

This matters beyond BiRefNet: it is the standard escape hatch cited for RMBG's
CC BY-NC blocker (RMBG-2.0 is BiRefNet retrained on Bria's private data — though
note that claim was itself refuted 0-3 and is unconfirmed). **Until the weights
licence is settled, EMB-Bot has no verified commercially-clean high-accuracy
matting model.**

### HQ-SAM 2 is a dormant beta. Confirmed 3-0.

Still self-described *"beta-version"* in both READMEs. **No formal release has
ever been cut** ("There aren't any releases here"). Newest commit is 2025-09-12
but it is README-only; **last functional commit 2024-12-05** — ~21 months of code
dormancy. The June 2025 Transformers support covers **HQ-SAM v1 only**
(`SamHQModel` exposes SAM-1 ViT config fields, not the Hiera-based
`sam2.1_hq_hiera_large.pt`). Apache-2.0, so no GPL risk — but adoption needs
torch ≥2.3.1 into an otherwise CPU OpenCV pipeline, against an unmeasured gain.

Two companion claims were **refuted 0-3**: SAM-HQ's architecture description,
and its `pip install segment-anything-hq` / Apache-2.0 packaging. Only sam-hq2's
own README-stated Apache-2.0 stands.

### Pass B's Hub sweep, for completeness

Top `mask-generation` by downloads: `facebook/sam3` (gated, `license:other`,
arch `sam3_video`, updated 2025-11-20), SAM 2.1 hiera family (Apache-2.0 — the
**incumbent**, `sam2_worker.py` pins `sam2.1_hiera_{tiny,small,base_plus}`),
`PramaLLC/BEN2` (MIT), BiRefNet family. `rembg_worker.py` defaults to
`isnet-general-use`, i.e. the DIS lane — so BiRefNet is the *same task's* next
generation, which is what made it the obvious candidate before the training-data
finding landed.

**SAM 3 is unevaluated.** It is gated and its licence is unread. Being newer than
the incumbent is not a reason to adopt it.

---

## 4. Dead ends — closed, so nobody repeats them

- **Hugging Face has no embroidery tooling.** All 14 hits for "embroidery" are
  **style LoRAs that generate images which look like embroidery** — the inverse
  of what a digitizer needs. Max 90 downloads. "cross stitch" returns 3, all
  LoRAs.
- **arXiv has essentially nothing on digitizing quality.** The embroidery
  literature is HCI and textile engineering: actuators, smocking, self-folding
  textiles, conductive thread on seams. The one promising title —
  *Generating Embroidery Patterns Using Image-to-Image Translation* (2003.02909)
  — states its goal is to *"generate a preview image which looks similar to an
  embroidered image"*. **A renderer, not a digitizer.** Same inverse problem as
  the LoRAs.
- **The Claude plugin catalogue is irrelevant.** Searched on computer vision,
  image processing, geometry, ML, benchmarking. Every hit is business tooling
  (data/SQL, marketing, HR, CockroachDB, Carta, prospecting). **No plugin moves
  digitizing quality.**
- **No embroidery-domain MCP server or Connector exists** in the directory.
  Searched embroidery, image annotation/segmentation, SVG/vector editing, file
  conversion, GPU inference, model training, photogrammetry.
- `embroidermodder`, `stitchcode`, `scikit-geometry`: **not on PyPI** at all.

---

## 5. Components worth having, with nothing bought

Both from Pass B's PyPI sweep; neither is a digitizing engine, both are
permissive and current.

- **`pyclipper`** — MIT, 1.4.0, 2025-12-01. Cython wrapper over Clipper, the
  CAM-industry standard for **polygon offsetting**. The right instrument for
  problem 6 (underlay, pull compensation, seam underlap — defect 6's 0.24 mm
  mean over 1,549 mm). Sharper point: DOCTRINE's 2026-09-12 ruling *"Never
  `unary_union` a stitch path before buffering it"* came from shapely's buffer
  eating 5,189 of `hotel_fremont_hat`'s 5,203.9-second prep and exhausting a
  39 GB box. That is a polygon-offsetting performance failure, and offsetting is
  Clipper's core competence. The fire is already out (buffer-the-runs-then-union,
  14.5 s) — but deliberate offsetting for underlay now has a purpose-built
  library behind it.
- **`skan`** — BSD-3, 0.13.1, 2026-02-06. Skeleton **analysis**: converts a
  skeleton image into a graph with per-branch geometry. The missing middle
  between scikit-image's `skeletonize` (already installed) and satin rails —
  problem 2's rail-extraction half, which the Ink/Stitch finding does **not**
  address. Same ecosystem as scikit-image, so it composes.

---

## 6. What neither pass evaluated — read as UNEVALUATED, not absent

Pass A's own finding 7 is a coverage gap, stated at high confidence: all 11
confirmed and 14 refuted claims concentrate on eight subjects only (Ink/Stitch
`lib/stitches`, pystitch, libembroidery, PEmbroider, `dst-format`, BiRefNet,
RMBG-2.0, SAM-HQ). **Nothing was verified, for or against, on:**

- Vectorization quality (problem 4) — VTracer, potrace, Kopf-Lischinski, Diffvg,
  Im2Vec, LIVE. *(Pass B licence-checked these; quality is still unmeasured.)*
- Centerline / medial-axis / ribbon decomposition — problem 2's rail half.
  *(Pass B found `skan`; unmeasured.)*
- Path/sequence optimizers — OR-Tools, LKH/Concorde. *(Pass B licence-checked.)*
- Underlay / pull-comp / density modeling (problem 6).
- Photograph-to-thread-painting (problem 7).
- Academic digitizing code releases.

**No verdict reached** on two ground-truth readers — treat as **open, not
rejected**:

- **libembroidery** — zlib licence split 1-2, format-count claim 0-3,
  v1.0-alpha instability 0-3.
- **PEmbroider** — the GPLv3 + Anti-Capitalist Software License commercial-blocker
  claim split 1-2, its modified-TSP hatching optimizer 1-2.

**Fetched but dropped on budget — the best leads for a next pass**, in rough
value order:

1. **`desmondlzy/embroidery-streamlines`** — an academic embroidery code release,
   fetched and never evaluated. EMB-Bot already has `stage6_streamline.py` and
   `directionfield.py`, so this is direct prior art on code we ship.
2. `fablabnbg/inkscape-centerline-trace` — problem 2's rail half.
3. `hustvl/Matte-Anything` — boundary-accurate matting, problem 1.
4. `visioncortex/vtracer`, `jni/skan` — licence-cleared in Pass B, quality unmeasured.
5. `facebookresearch/sam3`.

---

## 7. Open questions, in priority order

1. **What is BiRefNet's actual licence for its published weights?** Pass B
   narrowed it to "a model-card tag with no LICENSE file"; the code repo is
   still unverified. Until settled, there is **no verified commercially-clean
   high-accuracy matting model** for EMB-Bot — and problem 1 is the binding
   constraint.
2. **What decides a TRIM in a professionally digitized file?** Ink/Stitch's
   router answers neither half of this. Is the pro's rule about colour-change
   boundaries, density transitions, or machine/operator settings rather than
   distance at all? `.claude/memory/pro-trim-threshold.md` already says no single
   threshold reproduces this pro.
3. **Does description-level reimplementation clear Kent's risk bar** for a public
   repo declaring proprietary licensing, or does autoroute's ~114 lines need a
   real two-person clean-room split? Related and cheap: **should this repo carry
   a root LICENSE file at all**, given `pyproject.toml` declares Proprietary
   while the repo is world-readable and ships no grant?
4. **Which unevaluated class deserves the next pass** — §6's list.

---

## Sources

Pass A fetched 20 primaries on 2026-09-12. Load-bearing ones:

- `raw.githubusercontent.com/inkstitch/inkstitch/main/lib/stitches/utils/autoroute.py`
  (and `auto_satin.py`, `running_stitch.py`, `auto_run.py`, `LICENSE`)
- `github.com/inkstitch/pystitch` · `pypi.org/pypi/pystitch/json` · the pinned 1.0.1 wheel
- `raw.githubusercontent.com/ZhengPeng7/BiRefNet/main/README.md` · arXiv 2401.03407 · 2509.06839
- `huggingface.co/briaai/RMBG-2.0` · `github.com/Bria-AI/RMBG-2.0` · `bria.ai/pricing`
- `github.com/SysCV/sam-hq` (+ `/releases`, `sam-hq2/README.md`) · HF Transformers `sam_hq` docs
- `github.com/manthrax/dst-format` · `github.com/Embroidermodder/libembroidery` · `github.com/CreativeInquiry/PEmbroider`
- `networkx` `k_edge_augmentation` reference
- Local, this session: `digitizer/pyproject.toml`, `digitizer/requirements.txt`

Pass B, same date: Hugging Face Hub API via the `huggingface` MCP server
(`hub_repo_search`, `hub_repo_details`, `hf_fs`); PyPI JSON API for 20 packages;
arXiv API.

**Every fetch is dated 2026-09-12.** BRIA's licensing is vendor-controlled and
can change without notice; HQ-SAM 2's dormancy verdict flips if the project ever
cuts a release; Ink/Stitch's PyPI packaging is in progress.
