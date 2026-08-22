---
name: real-artwork-trim-truth
description: 2026-08-22 overnight — on Kent's REAL client logos the only large trim lever is chain_links (−33%, and FEWER stitches), gate-1 frozen; the fill-ordering work shipped in PR #205 is byte-identical there, and every gate-clear alternative measures ≤9%. Real logos are satin-dominated with 1–3 fill shapes that essentially never cut.
metadata:
  type: reference
---

**Start here before proposing any trim work.** An overnight run measured all
four of Kent's queued items against the six real-artwork fixtures in the repo
(`testdata/reference/becker_*.jpg`, `becker_marine_logo.png`,
`logo_script_tires.png`) rather than the photo corpus. Full evidence:
`docs/scope/1-auto-digitizing-quality.md`, twelve entries dated 2026-08-21/22.

| lever | real-artwork trim effect | status |
|---|---|---|
| **`chain_links`** | **−33% (−35% on the 6 real fixtures) AND fewer stitches** | built, measured, **gate-1 frozen** |
| exit choice | ~9% | unbuilt, huge blast radius |
| cursor placement | ≤34% of *satin travel failures* only | unbuilt |
| fill ordering (PR #205) | **0%, byte-identical** | shipped; helps photo-lane only |

**`chain_links` is the decision Kent owes himself.** Verified stable at
`max_colors` 4/6/8: 35% every time, stitch count DOWN every time, **zero
designs worse on either axis in any run** — the only measurement of the night
that did not weaken under scrutiny. He accepted the sew-out as-is on 2026-08-21
(see [[sew-out-accepted-as-is]]) *without this number*. **Gate 1 still refuses
it** — `LINK_COVER_TOL_MM` is a thread spec — so present it as evidence, NEVER
as a request to flip the flag.

**Why fill-side work cannot help real logos.** They carry **1–3 fill shapes
each with essentially no cutting fills** — predominantly satin, lettering and
borders. Across all six designs exactly one shape had any cutting fill, and
there the shipped order was already cheaper. Trims on real artwork are
**shape-ENTRY** trims: first-of-shape counts track shape count almost exactly
(10/10, 11/12, 14/16, 8/8, 7/8, 4/4), and they surface as `underlay` trims
because underlay is what enters a shape. `logo_hotel_fremont`'s 46-hole
perforated field is the **exception, not the type** — do not size future work
from it (see [[hotel-fremont-pro-parity-findings]]).

**Corrections this run made to earlier beliefs — all four were mine:**

- **Stage 5 is NOT producing invalid geometry.** Repeatedly called "the
  highest-value open thread"; false. The producer is clean; float ROTATION in
  `best_fill_angle_deg`'s sweep creates it transiently (11 of 17 candidate
  angles). PR #202's consumer-side guard is therefore *correct*, and the angle
  search is not degraded (0 of 8 shapes change when repaired first).
- **Exit-choice: 58% → 28%.** The bound assumed any point can be a shape's exit.
  Tested with run endpoints only, it halved. Recommended as "next build", then
  reversed within the hour.
- **"Satin travel fails at the cursor" covers 34%, not all.** That was the
  `sewn==0` subset (31 of 37) generalised to all 97 failures; two thirds have
  the cursor comfortably in range.
- **`_graph_travel` does NOT "never return a path"** (attribution doc §2 is
  stale) — it succeeds 18–30% over 124 measured calls.

**The habit that caught every one of them:** re-derive the number, and test the
assumption a bound rests on. Eleven claims fell to measurement in one session,
including two headline results. `tools/trim_exchange_sweep.py --diff` exits
non-zero if any design regresses — use it rather than trusting a remembered
figure.

See also [[sew-out-accepted-as-is]], [[hotel-fremont-pro-parity-findings]],
[[emb-bot-digitizer]].
