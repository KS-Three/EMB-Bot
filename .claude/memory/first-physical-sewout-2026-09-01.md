# The first physical stitch-out — 2026-09-01

Kent sewed his Instagram-style icon (80.5 mm, pique + cutaway, random
operator threading — DST carries no palette, never grade colour from a
stitch-out) and rated it **6/10**. Thread has met cloth for the first time.
Full measured record: `docs/scope-history.md` 2026-09-01 entry.

## What the file + photos established

- **Service encoder confirmed in the sewn path** — pystitch reads all 7
  colour changes (standard 0xC3), orientation sewed correct. The browser
  codec's axis bug was never in play.
- **His four findings all mapped to code mechanisms**: glyph sewn as block 0
  before every background cone (no borders-last rule exists); background =
  7-cone shade-patch quilt with a 229-st cone re-entering the lens at 76%
  and a 104-st final cone; tail jump-chains stepping 8-11.5 mm. Defects 6
  and 16 observed on cloth.
- **The density story is UNSETTLED — two measurements disagree.** Read both
  before quoting either; this is the one claim in this entry with no
  agreed number behind it.
  - *Reading A, the same night:* I explained his "fabric shows through"
    with FILL_ROW_MM=0.40 vs the pro's ~0.19, then measured HIS file and
    got **0.18-0.19 mm pitch** (blend path sews its own pitch) — which
    retired the density story as a cause.
  - *Reading B, later the same night (the "Bare Edge" artifact session,
    since lost):* a purpose-built pitch estimator — autocorrelation of the
    cross-row projection profile, **calibrated against a known answer
    first** — recovered 0.400 mm where 0.400 is the truth (the engine
    plan), then read **0.400 mm median on design.dst, the file he sewed,
    with 0% of passes anywhere near 0.19**. On that reading the
    0.18-0.19 figure does not reproduce, and Law 19's "0.40 is half
    professional coverage" stands as the explanation after all.
  - *Its own stated limit:* only **16 of roughly 1,700** needle-down
    passes are wide enough for that estimator to read, so it speaks for
    the substantial fills, not every small patch.
  - **The instrument now EXISTS** — `digitizer/tools/fill_pitch.py`
    (PR #310), rebuilt to Reading B's method and calibrated by recovering
    TWO different configured row spacings, not one (a stopped clock
    recovers 0.40). 14 tests pass.
  - **FIRST MEASUREMENT OF THE PROFESSIONAL FILES, 2026-09-01** — nobody
    had pointed an instrument at them before. The five commissioned
    `testdata/reference/becker_*.dst` files read **0.380 / 0.370 / 0.400 /
    0.380 / 0.535 mm** median row pitch. Four of five sit at 0.37-0.40,
    which is exactly where `FILL_ROW_MM = 0.40` already is. On the passes
    this instrument can read, **these professional files do NOT support
    "0.40 is half professional coverage"** — the claim that reopened the
    density story.
    *Its limit, stated because the tool states it:* only 3-4 of 14-15
    passes per file are wide enough to read, so this is a first datum, not
    a population assignment. Their p10s (0.21-0.33) do show some passes
    near 0.20 — consistent with `FILL_ROW_MM`'s own note that the corpus
    splits at ~0.20 into a genuine dense population and a SATIN-CROSSING
    HALF-STEP ARTIFACT. Reading A's 0.18-0.19 is exactly where that
    artifact lives, which is the most likely explanation of the whole
    disagreement.
    Gate 1 is untouched: this measures, it does not set the constant.
  - What is NOT in dispute: macros show patch interiors solid, and the
    see-through is at least partly seam trenches between patches, raw
    perimeter fill ends (bottom-left has no covering border), and late
    fragments sewn OVER the pre-sewn glyph satin. Those are geometry and
    order, and they are fixed as geometry and order — `cfg.edge_cap`
    (2026-09-01) closes the bare perimeter half.

## Lessons that must not be re-learned

1. **Decode the sewn file before quoting a constant story** — and then
   check the decode itself. The 0.40 explanation was plausible and
   sourced; the 0.18-0.19 decode that overturned it was plausible and
   measured; a calibrated estimator later put it back at 0.400. Two
   measurements of one file disagree by a factor of two, so the real
   lesson is that a pitch number quoted without a re-runnable instrument
   is not evidence, whichever direction it points.
2. A sew-out photo grades SEAMS and ORDER as much as density — the two
   queued fixes (borders-last sequencing; patch-quilt cleanup, both issued
   as task cards 2026-09-01, Kent-approved) are sequencing work, gate-clean.
3. Gate 1 still stands: this icon settles no physical constant. The
   controlled instrument is `EMBBOT_SEWOUT_CARD.dst` (buildable on Linux
   since PR #299), block 2 = 0.40 / 0.20 / double-pass on one hooping.
4. Evidence custody: sewn DST + 5 photos exist only in the session upload
   dir and on Kent's machine — deliberately not committed (public repo).
