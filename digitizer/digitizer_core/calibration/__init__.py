"""Closed-loop sew-out calibration — the card, the reader, the profile.

`docs/sewout-calibration-brief-2026-09-30.md` is the decision record. The
customer sews a card on their own goods, photographs it, and the reader
turns the photo into a fabric profile that ADJUSTS the garment's shipped
preset, clamped (`fabrics.apply_profile`; DOCTRINE standing ruling,
2026-09-30).

  card      Kent's gate-1 sew-out card, v1 — six questions, one hooping,
            read by eye with the paper key (`docs/sewout-card-2026-07-31.md`).
  card_v2   the CUSTOMER's card: v1's blocks plus corner fiducials and the
            professional's 0.15 mm density arm, fits a 5x7 hoop.
  reader    a photo of either card → per-feature readings, as a DIFFERENCE
            from the engine's own render read by the same code.
  profile   the service's half: build and cache the card, read a photo,
            draft the three-number profile the Studio writes on Accept.

The tools of the same names (`tools/sewout_card.py`, `sewout_card_v2.py`,
`sewout_reader.py`) are the command lines; they import from here.
"""
