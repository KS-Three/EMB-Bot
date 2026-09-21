# External sourcing sweep — fonts and digitizing quality, 2026-09-12

Nine lanes across forges, package registries, model hubs and the literature, then
twelve deep dives with the candidate actually installed and run against real
fixtures. **86 candidates found, 12 deep-dived, 8 adversarially checked.**

Verification legend, as `docs/inkstitch-research-2026-08-10.md` uses it:
**[V]** verified this session against the cited primary source ·
**[M]** measured this session · **[U]** not verifiable from a primary source.

## Method limits

- **5 of 35 agents failed on the weekly usage limit**, and they were not evenly
  distributed: the four unchecked dives are **vpype, the Chordal Axis Transform,
  OR-Tools and penkit-optimize** — the entire routing lane, which is also the
  highest-value lane here. Its conclusions are single-source.
- The synthesis stage never ran; this document is written from the journal.
- Every dive **installed and ran** its candidate. No verdict below rests on a README.

---

## 1. The verdict

The font supply question is closed, and this sweep closed it harder than the August
sweeps did — but it also found **one real font they mis-binned**, and it priced the
commissioning route they named but never costed. On the digitizing side the honest
result is a lot of well-evidenced rejections and **two things worth taking**: a
perceptual metric that sees what ARTFID is blind to, and a routing encoding that
maps directly onto defect 4. The most valuable single output may be the licence
hazards in §5 — two candidates the sweep itself labelled "safe to depend" are not.

## 2. The font answer

### The closure is confirmed, by a fingerprint the prior sweep did not use

The 2026-08-21 hunt searched on `horiz_adv_x_space` (16 files). This sweep used
`horiz_adv_x_default` (128 files) and `GlyphLayer-` in SVG (61 files), paging every
result of all three. **[M] The only repositories on earth carrying Ink/Stitch glyph
data are:** `inkstitch/embroidery-fonts`, `inkstitch/inkstitch` (test fixtures),
`UncleJey/inkstitchFonts`, `Godan/japanese-fonts-for-stitch`, `MaticsLab/Threads`,
and `KS-Three/EMB-Bot` itself. Three fingerprints, three censuses, same six repos.

**[M] Net new satin glyph data found anywhere since 2026-08-21: zero.** The one
repository created since (`MaticsLab/Threads`, 2026-08-22 — the day after) is a
verbatim repack of seven fonts EMB-Bot already ships.

### The structural reason, which is worth more than the census

**Every non-Ink/Stitch format fails on gate 1, not on licensing.** An Ink/Stitch
`font.json` carries `size` — how large the face is meant to sew. No other format
does. A TTF, a Hershey face, a METAFONT source, a TurtleStitch program, a CNC
single-line font: all can give geometry, none can state `sizeMm` or stitch length,
so importing any of them means inventing a physical constant. **That is a one-field
screening test that disposes of whole ecosystems before you read a licence** — and
it is why Hershey died. The other open ecosystems do not store lettering as assets
at all: PEmbroider's built-in faces are a port of p5-hershey-js and everything else
comes from a Processing `PFont`; p5.embroider ships five files, none of them font
data; TurtleStitch's turtle path *is* the running stitch. There is no second corpus
to mine because no second tool keeps one on disk.

### One real find: `honoka` — ADOPT

**[M]** A complete hand-authored satin-column **Japanese** font sitting in the
upstream repo EMB-Bot already mines: **512 glyph layers, 5 775 `inkstitch:satin_column`
attributes** across five SVGs; 335 CJK Han, 84 hiragana, 83 katakana, 7 CJK
punctuation, zero Latin. **[V] OFL-1.1 verified at all three links** of the chain
(Corinne Renaud's adaptation → named parent → original publisher), with commercial
use explicitly granted and the only Reserved Font Name in the chain ("Source")
unused — which matters given what PR #473 just found.

It was **mis-binned by the 2026-08-21 sweep**, which put it in a table headed *"Why
the rest fail — they are not satin fonts"* under "no Latin glyphs". That is true and
was the wrong test: the library's gap is *non-Latin coverage*, which
`MASTER_SCOPE` records as **none of 85 fonts covering Japanese, Korean or Arabic**.

**[M] The entire import was run with unmodified EMB-Bot tooling** — build, QC, three
stitched strings, satin-width census, rendered proof, unsupported-character
behaviour, `.embf` size and preview-tile selection all completed. Data asset only,
no product code changes, cost: **hours**.

### The commissioning route, finally priced — ADOPT as the route

**[M] 44 of EMB-Bot's 85 shipping fonts (52%) are the work of one francophone
adapter pool**, 15 named individuals, and their output *is* the artifact
`build-font.mjs` consumes. This is not a forecast about a labour pool; it is the
library. **[V] Upstream licensing is not uniform** — of 142 fonts: 102 OFL-1.1,
33 CC-BY-SA, 8 NonCommercial, 3 GPL, 1 NoDerivatives, 2 CC0, 1 CC-BY-4.0, so
**37 of 142 touch a barred term** and any commission must specify OFL-1.1 up front.

The dive corrected its own sweep's first step: **you cannot email three of the
people it named — they have no email and no GitHub account.** The corrected first
action is one message, in French, to Claudine Peyrat. 2–4 hours, a writing task.

### Rejected on the font side

- **`fontTools`** — [V] MIT, zero transitive dependencies, ships in a paid closed
  product on a bare attribution notice, and it does exactly what was claimed.
  Rejected because the only lane it serves is **auto-tracing outline fonts, which
  Kent rejected on quality 2026-07-24**, recorded in four primary sources under
  "Rejected alternatives". The dive did not stop at the ruling — it built the bake
  and **reproduced the ruling independently**: auto-baked Poppins glyphs carry satin
  columns whose rails sit on opposite sides of the whole letter, against **0 of 223
  on the hand-authored control**. Its exact statistics did not replicate on re-run
  (20/62 vs 31/62 — the dive never recorded its bake scale, so those numbers are
  **[U]**), but the finding is **[M]** confirmed on both runs.
  **Keep the by-product:** `tools/qc-font.mjs` **passes a structurally unsewable
  font with zero findings**. One assertion bounding rung length against the font's
  own em would have caught it, and it hardens the gate every *new* font passes —
  hand-authored included. That is worth doing on its own merits.
- **Relief SingleLine** — [V] OFL-1.1, no Reserved Font Name, `fsType` 0. Rejected
  on capability: too thin to sew at lettering sizes, and both integration lanes are
  closed for reasons a font cannot fix (`app/src/lib/emb.js` deliberately excludes
  `fonts.js` from the Studio).

## 3. The digitizing answer, ranked by the defect it serves

**1. NVIDIA ꟻLIP (`flip-evaluator` 1.7) — ADOPT, hours.** [V] BSD-3-Clause, whole
chain fetched including the `libgomp` bundled in the manylinux wheel — the one item
that looks like a trap and is clear. **[M] Zero runtime Python dependencies.**
Serves the instrument-trust gap: a full-reference *perceptual* metric with spatial
contrast-sensitivity filtering and a HyAB colour difference, which is a different
quantity from `artfidelity_self`'s unweighted-octave MS-SSIM mean. **Add a column;
do not replace the composite.** It stays a CI/dev dependency — `pyproject.toml`
packages only `digitizer_core` and `digitizer_service`, so a metric used by `tools/`
never enters a customer wheel. The engineering experiment is already run and
positive; what remains is **one blind ranking session from Kent**, without which the
column is just another number that agrees with nothing.

**2. `penkit-optimize` — PROTOTYPE-FIRST, a session.** ~200 lines of MIT Python that
encode exactly the right problem for defect 4: *visit every path once, in whichever
of its two directions is cheaper, minimising pen-up travel*, as an OR-Tools
`RoutingModel` with two nodes per path in a disjunction. Maps onto
`stage6_fill.py:833 _reorder_for_fewer_cuts`. **Prototype-first, not adopt,
deliberately: nothing has been re-digitized end to end, every number is
`_order_cost`'s view of an order, and `MASTER_SCOPE:144` already records that
`_order_cost` and the sewn result disagree.** Carries the OR-Tools licence hazard
below.

**3. `skia-pathops` — PROTOTYPE-FIRST on merit, but its lane is closed.** [V]
BSD-3-Clause re-verified byte-identical inside the shipped wheel, zero runtime
dependencies, and the 65 MB sdist's vendored `third_party/` (including the
FTL/GPL-2 FreeType trap) is closed by construction — `build_skia.py` pins every
third-party lib to `=false`. **[M] 9.74% → 0.00%** on real product code, and the
one substitute nobody had tried — a proper NONZERO shapely emulation — scored a
perfect 0.00% **and still failed visibly when rendered**, filling counters solid.
So "no substitute in the current dependency set" holds for a better reason than
first given. It maps to **no live defect number**, and the lane it serves is the
same 2026-07-24 auto-tracing rejection. **Do not re-evaluate the library** — the
evaluation is finished and doubly verified. The trigger for revisiting is Kent
reopening outline-font import, and the question that would gate it (rail and
junction quality) is the exact stage pathops does not touch.

### Rejected, with the reason worth keeping

- **Google OR-Tools as a dependency** — rejected on merit, *not* on licence: **[M]
  a ~60-line dependency-free 2-opt beat it on the same cost matrix at the same 3 s
  budget, −38.5% vs −31.0%.** The lane is real; the library is not needed to walk it.
- **`vpype` `linesort`** — [M] rejected on merit. It minimises total pen-up
  *distance*; defect 4 is scored on trim *break count*, and at `TRIM_AT_MM = 3.0`
  against a ~16 mm median needle-up move the two are nearly unrelated.
- **Chordal Axis Transform on `shapely.constrained_delaunay_triangles`** — [M] the
  primitive works, the premise is factually wrong, and the slot is already occupied
  by a more mature implementation of the same idea (`classify_ribbon`'s raster
  skeleton + exact DT).
- **`scikit-image` phase correlation as extra registration seeds** — [M] **the gap
  closed the day of the sweep**: the exact proposed fix shipped as `_corr_seeds` in
  commit `61d46c1` / PR #463.
- **`cv2.xphoto.dctDenoising`** — the most instructive rejection here. Its entire
  measured case was **an OpenCV bug artefact**: [V] the shipped wheel zeroes the
  last row and column of its output via an off-by-one in
  `npixels = (rows-psize)*(cols-psize)`. Once the bug is accounted for the candidate
  is a uniform negative.

## 4. Verdict table

| Candidate | Licence [V] | Verdict | Serves |
|---|---|---|---|
| `honoka` (Ink/Stitch) | OFL-1.1 | **ADOPT** | Non-Latin coverage gap |
| Ink/Stitch adapter pool | OFL-1.1 (specify up front) | **ADOPT as the route** | Font supply ceiling |
| NVIDIA ꟻLIP | BSD-3-Clause | **ADOPT** | Instrument trust |
| `penkit-optimize` | MIT over Apache-2.0 + **EPL-2.0** | **PROTOTYPE** | Defect 4 |
| `skia-pathops` | BSD-3-Clause | Prototype on merit, **lane closed** | — |
| `fontTools` | MIT | **REJECT** (lane closed 2026-07-24) | — |
| Relief SingleLine | OFL-1.1 | **REJECT** (too thin) | — |
| OR-Tools | Apache-2.0 + **EPL-2.0** + MIT | **REJECT** (beaten by 60 lines) | — |
| `vpype` | MIT + **LGPL/GPL deps** | **REJECT** (wrong objective) | — |
| CAT / shapely CDT | BSD-3 over LGPL-2.1 | **REJECT** (premise wrong) | — |
| skimage phase correlation | BSD-3-Clause | **REJECT** (already shipped) | — |
| `cv2.xphoto.dctDenoising` | Apache-2.0 / BSD-3 | **REJECT** (OpenCV bug) | — |

## 5. Licence hazards — where the obvious reading was wrong

1. **OR-Tools is not "Apache-2.0, safe to depend".** [V] The shipped wheel is a
   **mixed binary**: Apache-2.0 + **EPL-2.0** (COIN-OR Cbc/Clp/Cgl/Osi/CoinUtils) +
   MIT. **EPL-2.0 is not in this project's allowed set**, so adopting it is a policy
   change request, not a routine dependency add. **`penkit-optimize` inherits this
   through its own dependency on OR-Tools** — which is why the one prototype-first
   routing candidate carries a licence question, not just an engineering one.
2. **`vpype`'s mandatory install chain is not all-permissive.** [V] vpype itself is
   MIT, but `pnoise` is LGPL-2.1+ and `pyphen` is GPL-2.0+/LGPL-2.1+/MPL-1.1.
3. **`svgpathtools`** — [M] licence read from the PyPI classifier only; its raw
   LICENSE 404s on master, so the file itself is **[U]**.
4. **FLIP's clean chain has a packaging gap, not a licence one** — it needs numpy
   and does not declare it.

## 6. Confirmed empty — do not repeat these

Named specifically, with what was actually queried. These are additions to the
2026-08-21 list, not a repeat of it.

- **Zenodo** — `api/records?q=embroidery`, 414 records: entirely humanities and
  materials science (Uzbek/Chaozhou/Phulkari history, conductive-thread wearables,
  textile pedagogy). **There is no academic embroidery-lettering corpus.**
- **Hugging Face** — `api/datasets?search=embroidery` returns exactly 4, all
  image/style data; `api/models?search=embroidery` returns 15, all Stable-Diffusion
  or Flux style LoRAs. Nothing in this hub is font or stitch data.
- **archive.org** — `embroidery AND font`: 6 items, none relevant.
- **npm** — three query vocabularies; libraries and converters only
  (`ricuci`, `tsembroidery`, `needlescript`, `jef2img`, `p5.embroider`), plus SEO
  spam. **[M] `p5.embroider` was opened and ships no glyph data.**
- **GitLab.com** — `api/v4/projects?search=embroidery`, 42 projects: machine
  firmware (Teathimble, embroiderino), Embroidermodder mirrors, format converters.
- **OSF** — API returned non-JSON; **attempted, not completed**. Given Zenodo,
  expected yield is near zero.
- **Kaggle** — JS-rendered, unparseable here. **Untested**, low expected yield.
- **crates.io / Maven / NuGet / CRAN / CPAN / RubyGems / Packagist** — not searched.
  PyPI and npm returned only repacks and libraries, so expected yield is nil.

**One cheap standing check is defensible and nothing more:** re-run the
`horiz_adv_x_default` census once or twice a year — about four API calls — and diff
the repo list against the six above.

## 7. Kent's decision queue

1. **`honoka`** — import the Japanese font? Hours, already run end to end, licence
   clean at three links. The question is whether Japanese coverage is wanted at all,
   which `PRODUCT.md` is silent about in both directions.
2. **Commission from the adapter pool?** The route is validated — 52% of the current
   library is already their work. First action is one message in French; the cost
   and rights terms come back from that.
3. **FLIP as a second yardstick column** — cheap to add, worthless without one blind
   ranking session from Kent to anchor it.
4. **EPL-2.0 policy** — needed before the routing prototype can use OR-Tools at all.
   The alternative is the 60-line 2-opt, which measured *better* and carries no
   licence question.
5. **`qc-font.mjs` has no satin-width or degenerate-rung check.** Independent of
   every candidate above, and cheap.
