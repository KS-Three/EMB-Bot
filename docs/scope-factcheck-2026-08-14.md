# MASTER_SCOPE fact-check — 2026-08-14

**What this is:** an automated fact-check of `MASTER_SCOPE.md` against the
code, run because three of its claims were found false by accident in a
single session (it said node editing did not exist when it had shipped eight
days earlier; it implied a defect in the streamline tier that measurement
disproved; it called an export-routing fix "not yet acted on" after it
merged). Three in one session is a defect rate, not bad luck.

**Method:** 8 agents extracted the most load-bearing *falsifiable* claims
from their slice of the 5,090-line document; a verifier checked each against
the code and had to quote the deciding lines; every FALSE/STALE verdict then
went to an adversarial refuter whose job was to defend the document.

**Headline:** 56 claims checked — **9 TRUE, 30 STALE, 17 FALSE**.

Do not read that as "84% of the document is wrong." See the caveats.

---

## Two caveats that matter more than the headline

**1. Most "STALE" verdicts are dated history, not live lies.** MASTER_SCOPE
is reverse-chronological: an entry from 2026-08-07 saying "Studio vitest
426/426" was *accurate on 2026-08-07*. Flagging it against today's 738 is
technically correct and practically unfair.

But it points at the real, systemic defect, which the 2026-08-11 audit also
named: **the document interleaves live status with dated history in one
stream, so every historical measurement reads as a current claim.** A reader
cannot tell "this is true now" from "this was true then" without checking the
date on a heading that may be several screens up. That is the thing worth
fixing — not 30 individual numbers.

**2. The adversarial refuter upheld 11 of 11 and rejected nothing.** A filter
that never rejects is not filtering, and one case proves it missed nuance:

> **Claim:** per-shape overrides are "carried across a re-digitize via
> `match_shape_ids`."
> **Agent verdict:** FALSE — `match_shape_ids` has zero production callers.
> **Verified true:** it is defined at `regions.py:106` and referenced only in
> comments and docstrings.
> **But the refuter should have caught:** `assign_shape_ids` derives every id
> deterministically from bucketed centroid + thread number
> (`_raw_id`, blake2s), so a re-digitize of unchanged art produces the same
> ids and edits carry forward by plain id matching — *without* that function.

So the document is **wrong about the mechanism and right about the
behaviour**. "Carry-forward does not happen" would have been the wrong
conclusion to act on. Treat every finding below as a lead to verify, not a
verdict — the panel did not earn more trust than that.

---

## Verified against current `main` (spot-checked by hand, 2026-08-14)

Each of these reproduces today. These are live claims, not dated history.

| # | The document says | The code says |
|---|---|---|
| 1 | overrides ride `match_shape_ids`' carry-forward | `match_shape_ids` has **no production caller**; ids are deterministic instead (see above) |
| 2 | meander/stipple fill is a capability "confirmed absent" | `digitizer_core/stage6_meander.py` is a full implementation |
| 3 | streamline fill is "not exposed" as a per-shape choice | `DigitizePanel.svelte` has `<option value="streamline">` in the per-shape Stitch type select |
| 4 | format writers depend on upstream `pyembroidery` | `digitizer_service/formats.py` line 29 is `import pystitch` — the swap shipped |
| 5 | the corpus scorecard runs 14 committed fixtures | `tools/corpus_scorecard.py`'s `FIXTURES` has **19** |
| 6 | "no dedicated test file" for the scorecard | `digitizer/tests/test_corpus_scorecard.py` exists and is tracked |
| 7 | "zero raw Unicode/emoji affordances left anywhere in the app" | `ColorRangesEditor.svelte` still renders a literal `×` as a button's whole content |
| 8 | `_speckle_ratio` "looks scale-broken" (returns 39-78 against a 0.35 max) | It is an **unnormalised Laplacian-gain ratio** and discriminates correctly at the shipped threshold |

**Item 8 is mine.** It came from PR #125's write-up, where I flagged it as
"flagged to confirm, not assumed" — and it then propagated into
MASTER_SCOPE as a suspected defect without ever being confirmed. It is not a
defect. This is the same failure mode as the streamline suspicion: a hedged
observation hardening into a stated fact as it is copied forward.

---

## Recommended, in order

1. **Separate live status from dated history.** The single change that would
   have prevented most of this. Either move history to a CHANGELOG and keep
   MASTER_SCOPE to current state, or mark every historical measurement
   inline as *"measured then, not a current baseline"*. The `At a glance`
   table plus `Waiting on Kent` already work this way and are the parts that
   have stayed reliable.
2. **Stop putting test counts in prose.** They are stale within a day.
   Nothing reads them; every one of them checked here was wrong.
3. **Decide `match_shape_ids`' fate** — wire it, or delete it and correct the
   several comments in `config.py` and `regions.py` that describe it as
   running. Dead code that documentation describes as load-bearing is worse
   than no code.
4. **Fix items 2-7 individually.** Each is a one-line correction.

## Not done here

The 5 bug-hunting agents' findings were not recovered — the workflow's
container was reclaimed before the judging phase wrote its results, so those
findings never survived to a verdict. Only the fact-check lane's results were
recoverable from the journal.
