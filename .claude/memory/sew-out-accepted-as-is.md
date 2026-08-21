---
name: sew-out-accepted-as-is
description: Kent ruled 2026-08-21 that the physical sew-out is accepted as-is — it is NOT a queued to-do, dependent confidence scores are permanently `pending sew-out`, and ROADMAP gate 1 is a standing refusal rather than a temporary one; it does not decide the DST codec fix or split_tonal_regions
metadata:
  type: decision
---

**Do not re-raise the sew-out as "the highest-leverage next action."** Kent
already heard that framing, and on 2026-08-21 he ruled: **accepted as-is.**

This closes an ambiguity that had been carried, deliberately unresolved, for
about a week. An earlier session recorded a batch of three decisions and the
third came through only as "accept as-is" with no item attached — the two
candidates being *sew-out* and *satin density*. Successive sessions refused to
guess it into `MASTER_SCOPE.md` and kept re-flagging it instead. Asked as a
direct multiple-choice question, Kent answered: **the sew-out**.

**What the ruling does:**

- Removes "Schedule a physical sew-out" from `MASTER_SCOPE.md`'s *Waiting on
  Kent* queue (it was item 2; the list renumbered to 1–7) and moves it into
  *Standing rulings — decided, do not re-litigate*.
- Makes the dependent confidence scores permanently `pending sew-out` — that
  is now a settled, honest end state, **not** a placeholder awaiting a date.
  Fabric-preset accuracy and real stitch quality stay there. Do not upgrade
  one because the code changed; do not treat the flag as a task.
- Makes **ROADMAP gate 1** ("no sew-out, no physical constants" — fill row
  spacing, satin width floor, link cover tolerance, fabric presets, DST
  orientation) a *standing* refusal rather than a temporary one. It was always
  a refusal; what changed is that waiting it out is no longer a plan.

**What it explicitly does NOT do** — this is the part most likely to be
over-read. Two queue items were parked *behind* the sew-out, and accepting the
sew-out as-is does not decide either of them. Both stay open and both still
need Kent's own call on their own merits:

- **The DST codec fix** (now queue item 2). Re-orienting the table changes
  every DST EMB-Bot has ever written. See [[dst-codec-axis-discrepancy]].
- **`split_tonal_regions`** (now item 3). Merged but default-OFF; costs +74%
  stitches. Was "parked until the sew-out" (2026-08-12) — that parking is now
  indefinite, which is a different thing from resolved.

Kent's next work item, chosen in the same exchange: **satin border
fragmentation** (live defect 6) — see [[hotel-fremont-pro-parity-findings]] —
taken ahead of satin-vs-fill routing, which stays queued behind it.

See also [[emb-bot-digitizer]] and [[real-artwork-parity]].
