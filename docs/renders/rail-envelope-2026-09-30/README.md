# The far rail's reach: symmetric | `rails_follow_edge=True` | `"envelope"` (2026-09-30)

Kent's pick after PR #561: the rail model's under-reach on uneven bands. Each
sheet is one shape at 80 mm, rail comp ON, in three panels left to right:
the shipped symmetric-offset rails (`satin_rails_follow_edge=False`), the
parked per-side profile (`True`), and the envelope (`"envelope"`). Artwork
grey, satin blue, underlay grey lines, travel red, the cover's fill green.

- `golden_tee_band_false_true_envelope.png` — the wavy band under GOLF
  (`S1183b1d4`, 40 px/mm): the symmetric rails stop short of the band's far
  edge along its wider stretches; both other modes reach it.
- `golden_tee_T_outline_false_true_envelope.png` — the T's outline.
- `becker_80mm_wordmark_false_true_envelope.png` — the BECKER wordmark
  (24 px/mm). In the middle panel `True` sews the C's bowl with the
  neighbouring arm's 5 mm crosses, the grown polygon's accidental coverage
  back again; the envelope (right) leaves the cover's fill where part C put
  it, because a blob is not a long gap along a band.

Numbers: DOCTRINE 2026-09-30 ("The far rail's under-reach is real…") and
`docs/scope-history.md`. The mode ships OFF; its flip is Kent's.
