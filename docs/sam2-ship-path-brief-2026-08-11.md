# SAM2 ship path — how photo segmentation reaches customers

**Date:** 2026-08-11 · **Scope:** decision brief for Kent on shipping the
`photo_segment_sam2` lane. Grounded in `MASTER_SCOPE.md` (SAM2 sections),
`docs/sam-alternatives-research-2026-08-11.md`, `digitizer/sam2_isolated/README.md`,
and `digitizer_core/stage2_sam2_segment.py`. **No product code changed.**
Kent decides; this brief takes a position (§Recommendation).

## Where the lane stands today

- **Works, and Kent liked it:** verified on one real photo (the snowy owl) —
  "drastically better at the photo recognition portion." That is the entire
  quality evidence base: n=1. The committed corpus cannot measure it — SAM2 only
  engages for `photo_subject`/`photo_scene`, and the only two such fixtures are
  synthetic stubs that produce near-identical output with it on or off.
- **Cost on a customer-class CPU box:** ~1.03 GB footprint (875 MB venv, of which
  torch is ~635 MB, + 156 MB checkpoint) and roughly **+15–30s per photo** at
  `points_per_side=12`.
- **Not a product feature yet, deliberately:** a `localStorage` dev seam
  (`embstudio:sam2` = `"1"` → `sam2Enabled()` in `app/src/lib/digitizer.js`), no
  UI. The venv is a 4-step hand build (`sam2_isolated/README.md`): CPU-torch from
  PyTorch's own wheel index, `sam2` from Meta's GitHub (never PyPI), pinned extras,
  then a **required** `--prewarm` checkpoint download — job mode refuses to
  download because the 90s timeout can't win against a 156 MB fetch + cold torch.
- **Fails soft, quietly:** the seam never raises; without the venv it falls back
  to classical SLIC+RAG with `PHOTO_SAM2_SEGMENTATION_UNAVAILABLE` in `warnings`.
  Honest in the payload, invisible in the UI today.

## The options

### A. Bundled bootstrap — app downloads venv + checkpoint on first photo use
- **What it costs the user:** ~1 GB disk, a large first-use download on their
  connection, then +15–30s per photo forever (CPU-only).
- **Effort/risk:** the hand build must become bulletproof automation: pip against
  an external index, a GitHub source install (needs git or pre-staged wheels), a
  checkpoint host (`dl.fbaipublicfiles.com`) we don't control, plus progress /
  resume / failure UX. The venv move already broke pip's `.exe` shims once
  (absolute embedded paths) — this machinery is brittle in exactly the ways
  customer machines punish. Real support burden, pre-revenue.
- **Promise:** keeps local-first/no-account fully intact. Photos never leave.

### B. Server-side segmentation service
- **What it buys:** zero client footprint, server hardware makes the +15–30s
  shrink or vanish, one environment we control instead of N customer machines.
- **What it costs:** **photos leave the machine** — the local-first no-account
  promise breaks, or at minimum needs an explicit carve-out and a privacy story.
  Requires a backend that does not exist; billing is also undecided, so if a
  backend ever gets built for payments the marginal cost drops — but that is a
  dependency on a decision not yet made, not a plan.
- **Effort:** new service, hosting, upload path, quotas, abuse handling. Largest
  total effort of the four; ongoing cost per photo.

### C. Ship v1 without SAM2; keep the dev seam; revisit post-revenue
- **What it costs:** photo customers get SLIC+RAG, which the one real test says
  is visibly worse at region formation. The photo lane is the flat-art pipeline's
  weakest area anyway (see the stage-1 owl question below), so v1 photo output
  underwhelms with or without SAM2.
- **What it buys:** zero engineering now, zero support surface, promise intact,
  and the seam + isolated-venv architecture is already merged, so nothing is
  thrown away. The A/B harness (`digitizer/tools/sam2_points_per_side_ab.py`)
  exists and waits only on real photo files.
- **Risk:** "revisit post-revenue" becomes never; the differentiation Kent
  actually observed sits unused.

### D. Hybrid — ship v1 without it, but build the in-app opt-in download as the
committed follow-up
Option A's machinery behind an explicit "Enhanced photo mode (~1 GB download,
runs on your machine)" toggle in Studio, not in the installer. Photo users who
want it pay the disk and the download knowingly; everyone else ships light. Same
engineering as A minus installer integration, and it can land after v1 without
blocking launch. Promise intact.

## Recommendation

**D, sequenced as C now.** Ship v1 without SAM2; do not build B. Commit to the
opt-in download as the first post-launch photo investment, gated on three cheap
validations that should happen regardless:

1. **Re-measure `points_per_side=12` on the real photo** — the shipped default
   was tuned only on the synthetic stub; the harness is built and waiting.
2. **Confirm or refute the owl stage-1 hypothesis** — if the white-body-floods-
   as-background failure is `stage1_prep`, SAM2 ships behind a bug it cannot fix,
   and fixing stage 1 raises SLIC+RAG's floor too.
3. **Commit 2–3 real photo fixtures** so the corpus can finally say whether SAM2
   helps sewn output, not just region formation.

Reasoning: the quality signal is real but n=1, and the two things we'd be
hardening (bootstrap automation) and paying for (support of a 1 GB install) are
expensive precisely where the evidence is thinnest. B is rejected for v1 on the
promise alone — "local-first, no account" is a differentiator against Ember's
cloud posture, and the first exception shouldn't be the feature whose input data
(customer photos) is the most sensitive thing the app touches. A-as-installer
forces the GB on everyone; D charges it only to the users who benefit. C alone
risks shelving the one capability a real user called drastically better — hence
D with named gates instead of an open-ended "revisit."

One prerequisite for whichever path wins: the fallback must stop being silent in
the product. If SAM2 is advertised and unavailable, `PHOTO_SAM2_SEGMENTATION_
UNAVAILABLE` needs surfacing in the UI, or users will believe they got the
enhanced result when they didn't.

## Open questions (unresolved as of this date)

- `points_per_side=12` has **never been re-measured on the real photo** that
  justified keeping SAM2 — only on `photo_scene_stub.png` (26 regions, −29%
  wall time). The default is not yet validated against content that matters.
- The owl white-background failure is **hypothesized to be stage 1**
  (`_dominant_border_color` flooding the white body as background before any
  segmenter runs) — mechanism identified, confirmed against `owl_kent.jpg`
  (committed PR #126).
