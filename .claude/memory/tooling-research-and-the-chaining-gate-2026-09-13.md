# Tooling research, and the chaining gate that was already met

**2026-09-12/13, four merged PRs** (`2a71a48` #470, `8a94bfe` #474, `d2b222c`
#480, `038d424` #482). Re-verified against `main` on 2026-09-18.

Kent asked whether any repo, MCP server, Connector or plugin would improve
digitizing quality. Two verified research passes (106 and 102 agents; 44 primary
sources; 33 of 50 voted claims **refuted**).

## The answer is no, and the reason is worth keeping

**The field is thin.** No maintained open-source digitizing engine exists
besides Ink/Stitch (GPL-3.0) and the I/O libraries. Auto-digitizing has
essentially no academic literature — arXiv's embroidery corpus is HCI and
textile engineering, and the one image-to-image paper generates *"a preview
image which looks similar to an embroidered image"*: a renderer, not a
digitizer. Hugging Face's entire embroidery lane is style LoRAs that draw
pictures of embroidery. **No embroidery-domain MCP server or Connector exists**
in the directory, and the plugin catalogue is all business tooling.

Do not re-run this search. Full trails: `docs/tooling-research-2026-09-12.md`,
`docs/trade-knowledge-2026-09-13.md`.

## What it did buy — the parts that change decisions

- **Vendors publish NO distance rule for trim.** Hatch: *"if the connecting run
  is hidden beneath another object, it is more efficient to use a connecting run
  rather than a trim and tie-off"* (corroborated in a second Wilcom tree); a
  three-state per-object override whose Off/Always states bypass the millimetre
  value entirely; Embird publishes no threshold at all, only sew ORDER plus
  same-colour and visibility. **So defect 4's "no single threshold reproduces
  this pro" is the expected shape of the published model, not an anomaly** — and
  `chain_links` routing for cover rather than distance is what three vendor doc
  families describe. Scope guard: those rules govern needle-DOWN connecting
  runs; the 910-move corpus is needle-UP moves.
- **A published number contradicts `LINK_COVER_INSET_MM` 3–4x.** Embird: *"place
  connection at least 2~3 mm inside of the upper object"*, sized explicitly
  against *"loose hooping of fabric or pull effect of the thread"*. Ours is 0.75,
  and its derivation (`machine.py`) is pure THREAD-REACH — fill 0.223, satin
  0.501, run inradius 0.539, +0.2 — every term asking where thread stops
  relative to a polygon. **It budgets zero for the cloth moving afterwards.**
  Theirs is a routing target where ours is a permissive floor, and no second
  source corroborates 2–3 mm: enough to reopen the question, not to settle it.
- **Three licence traps, each the first thing you would reach for:**
  `pypotrace`/`potracer` **GPL** → **`vtracer`** MIT; `triangle` **LGPL** →
  **`mapbox-earcut`** ISC; `elkai` (LKH, academic-only) → **`ortools`**
  Apache-2.0. Also **RMBG-2.0's weights are CC BY-NC 4.0** with a contact-sales
  commercial path — categorically worse than GPL, which permits commercial sale
  under copyleft.
- **`pystitch` is clean, verified in the pinned 1.0.1 wheel itself** (zero
  GPL strings across 98 files, no `Requires-Dist`). `pyembroidery` last shipped
  2024-03; the fork swap needs no revisiting. But its 40-format READ claim was
  refuted 0-3 — problem 5's ingest half is NOT confirmed solved.
- **Three honest nulls.** No published float-visibility tolerance anywhere (a
  candidate reading of Wilcom's 3 mm was voted down 1-2 then 0-3 — do not cite
  it); underlay essentially unsourced (and `chord gap` is a curve-fidelity
  tolerance ALONG the path, not a perpendicular inset — do not launder it into a
  prior); and **nothing at all survived on satin column limits**, so the 1.0 mm
  floor has no published value to check against.

## Chaining: gate 3 was already satisfied, and MASTER_SCOPE already said so

I went looking for whether gate 3 still blocks `chain_links`. It does not, and
the finding was already written down — MASTER_SCOPE's Latent entry 1 records the
instrument rebuild and that gate 1's cover tolerance is the blocker. The
archaeology only added dates: preconditions closed `c8ab7ad` (08-03, cover
rebuilt from real emitted centrelines), `11ceecc` (08-04, `covered_by` eroded),
`f8e8968` (08-11, tier blindness). The shelving lasted **one day**.

**The remaining blocker is gate 1 and the gate is RIGHT this time** — the
question is where a human eye catches a float on cloth, which no reference
implementation can answer. Not another DST-orientation error.

**Sew-out card block 7 is drafted and NOT BUILT.** `docs/sewout-card-2026-07-31.md`
carries cases A–F plus a stretch step; `digitizer/tools/sewout_card.py` emits
blocks 1–6 only (`BLOCKS`, `block1_lock`…`block6_seam_b`, zero mentions of
clearance/chain/link_cover — checked 2026-09-18). **The card cannot sew the
measurement that gates the largest lever on defects 4 and 6 until someone adds
the geometry.**

## Two corrections I had to make to my own work, same shape

- **BiRefNet.** Recommended as the fix for defect 5's logo-art segmentation off
  a Hub `license:mit` tag and a DIS-VD score. Its training corpora are **all
  photographic, zero logo/vector/clipart**, and the weights repo **ships no
  LICENSE file** — MIT is a model-card tag, and "MIT for both code and weights"
  was refuted 0-3. A tag is a publisher declaration, not a grant.
- **Block 7.** First drafted testing only static gaps, when the published
  rationale for the inset is *displacement*. A float judged at rest on a flat
  hooped panel is not judged at all. Case F and the stretch step were added the
  next day.

## The lesson worth more than any of it: three stale sources in one session

Each produced a confident, authoritative-looking wrong answer.

1. **`git log -S` on a SHALLOW clone** dated all three chaining preconditions to
   the graft commit — real hash, real date, a month wrong. **DOCTRINE already
   had this entry** (2026-09-02, from the scorecard baseline incident, naming
   `git rev-parse --is-shallow-repository` as the check). I had not read it.
2. **A stale working tree** gave MEMORY.md as 48,872 characters — nearly 2x its
   24,986 ceiling — and I nearly reported the memory index as broken. On `main`
   it is 13,393. The overflow had been fixed three days earlier.
3. **A loose grep** (`float|block7`) returned 13 hits in `sewout_card.py` and I
   read it as "block 7 was built". `float` is a Python type hint.

**Check that the source is current before quoting it, and read DOCTRINE before
doing archaeology** — the trap you are about to fall into may already be in it.
