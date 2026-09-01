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
- **The density story died against measurement, same night.** I explained
  his "fabric shows through" with FILL_ROW_MM=0.40 vs the pro's ~0.19 —
  then measured HIS file: **0.18-0.19 mm pitch** (blend path sews its own
  pitch). Macros show solid interiors. The see-through is seam trenches
  between patches, raw perimeter fill ends (bottom-left has no covering
  border), and late fragments sewn OVER the pre-sewn glyph satin.

## Lessons that must not be re-learned

1. **Decode the sewn file before quoting a constant story.** The 0.40
   explanation was plausible, sourced, and wrong for this design's lane.
2. A sew-out photo grades SEAMS and ORDER as much as density — the two
   queued fixes (borders-last sequencing; patch-quilt cleanup, both issued
   as task cards 2026-09-01, Kent-approved) are sequencing work, gate-clean.
3. Gate 1 still stands: this icon settles no physical constant. The
   controlled instrument is `EMBBOT_SEWOUT_CARD.dst` (buildable on Linux
   since PR #299), block 2 = 0.40 / 0.20 / double-pass on one hooping.
4. Evidence custody: sewn DST + 5 photos exist only in the session upload
   dir and on Kent's machine — deliberately not committed (public repo).
