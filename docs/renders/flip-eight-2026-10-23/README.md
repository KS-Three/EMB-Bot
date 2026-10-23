# Flip eight 2026-10-23: BEFORE | AFTER | pro

Kent's ruling on the flip sheet (PR #1047): flip the eight ON, hold two. BEFORE is today's engine with the flipped values set back (`tools/flip_eight_proof.py`'s `BEFORE`); AFTER is the engine's plain defaults; pro is the professional's DST for the same job. Counts are pystitch records off the DSTs. Held OFF: `cut_every_jump`, `sew_enclosed_white`.

| fixture | width | engine | BEFORE st / tr | AFTER st / tr | pro st / tr | points moved | pictures |
|---|---|---|---|---|---|---|---|
| hotel_fremont_hat | 92.5 mm | aaab5909 | 18,611 / 51 | 17,485 / 27 | 17,067 / 21 | 11,562 | [whole](hotel_fremont_hat__whole_before_after_pro.jpg) [crop](hotel_fremont_hat__crop_before_after_pro.jpg) [where](hotel_fremont_hat__where.jpg) |
| becker_hat_small | 76.5 mm | bc3de760 | 5,928 / 15 | 5,867 / 15 | 8,694 / 11 | 161 | [whole](becker_hat_small__whole_before_after_pro.jpg) [crop](becker_hat_small__crop_before_after_pro.jpg) [where](becker_hat_small__where.jpg) |
| mfab_hat | 104.9 mm | bc3de760 | 13,721 / 65 | 13,466 / 62 | 17,568 / 19 | 1,041 | [whole](mfab_hat__whole_before_after_pro.jpg) [crop](mfab_hat__crop_before_after_pro.jpg) [where](mfab_hat__where.jpg) |

Regenerate: `python -m tools.flip_eight_proof` from `digitizer/`.
