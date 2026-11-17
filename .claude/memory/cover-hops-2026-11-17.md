---
name: cover-hops-2026-11-17
description: "Kent 2026-11-17 'Flip ON anyway': lettering_columns_cover_hops (cuts a travel on no satin: Toat c-mouth bars) flipped ON OVER ROADMAP gate 1; its 0.3/0.1/0.2 mm tolerances are untested on cloth"
metadata:
  type: project
---

**Kent, 2026-11-17, "Flip ON anyway"** — answering "What should happen to it?" after he was shown the Toat beanie
c-mouth ORIGINAL | BEFORE | AFTER and told: 11 of 35 runs move (beanie and Bridge better, the rest no visible
change, none worse), 15 extra trims, and the rule needs three new exposure tolerances that ROADMAP gate 1 ("link
cover tolerance") treats as sew-out-only numbers, with the director's advice to keep it OFF until a sew-out.
**This is Kent overruling gate 1 for this one flag, knowingly.** Do not cite it as a precedent for other gate-1 numbers.

**The tolerances:** `columns._BARE_MAX_MM` 0.3 (bare when more than this much of a travel segment lies off the
sewn satin), `_BARE_GROUND_MM` 0.1 (thread reach past a rail polygon), 0.2 on the script path (half the 0.4 mm
thread). None swept, none seen on cloth.

**Tried, dropped:** a no-tolerance rule (cut any travel off the artwork) keeps the cure but cuts hops that end on
a pull-pushed rail: 9 of 9 pro jobs move, trims 302 -> 323 against 310 for the 0.3 rule.

**Cause of the fault:** the link rule's `poly_hop` (outline grown by the pull) closes a notch the satin leaves
open, so a travel across a c's mouth counted as inside the letter.

**How to apply:** if a sew-out shows a cut hop leaving a float or a trim tail where the old walk was clean,
the first suspect is these three numbers. Evidence: `docs/renders/cover-hops-2026-11-17/README.md`; PR #1636.
