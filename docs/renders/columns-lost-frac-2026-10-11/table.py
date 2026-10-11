import json
import os

FX = ['becker', 'bridge', 'drone', 'enthusiast', 'fremont', 'golden_tee']
src = {'off': 'm2/{f}-off{s}.json', 'on': 'm2/{f}-on{s}.json'}


def capsrc(f, s):
    return f'm3/{f}-on{s}.json' if f in ('becker', 'enthusiast') else f'm4/{f}-on{s}.json'


def get(path):
    return json.load(open(path))['summary'] if os.path.exists(path) else None


print('## instrument as the test reads it (grid registration, art at stitch width)')
print('| fixture | arm | lost_frac | unsewn | wrong colour | overshoot | uncovered ink | stitches | trims | shift |')
print('|---|---|---|---|---|---|---|---|---|---|')
for f in FX:
    for arm, p in (('shipped', src['off'].format(f=f, s='')), ('lane', src['on'].format(f=f, s='')), ('lane+cap', capsrc(f, ''))):
        r = get(p)
        if r:
            print(f"| {f} | {arm} | {r['lost_frac']:.4f} | {r['unsewn_frac']:.4f} | {r['wrong_colour_frac']:.4f} | {r['overshoot_frac']:.4f} | {100*r['uncovered_ink_frac']:.2f}% | {r['stitches']:,} | {r['trims']} | ({r['shift_x_mm']:+.1f}, {r['shift_y_mm']:+.1f}) |")
print()
print('## one-pixel registration (each design its own best)')
print('| fixture | shipped | lane | lane+cap |')
print('|---|---|---|---|')
for f in FX:
    vals = [get(src['off'].format(f=f, s='-fine')), get(src['on'].format(f=f, s='-fine')), get(capsrc(f, '-fine'))]
    print(f'| {f} | ' + ' | '.join(f"{v['lost_frac']:.4f} (u {v['unsewn_frac']:.4f} w {v['wrong_colour_frac']:.4f} o {v['overshoot_frac']:.4f})" if v else '-' for v in vals) + ' |')
print()
print('## matched: ONE physical alignment (shipped design\'s best 0.1 mm fit), artwork at its own width, mm2')
print('| fixture | arm | lost_frac | unsewn | wrong colour | overshoot | letters overshoot | letters unsewn | spill >0.5 mm |')
print('|---|---|---|---|---|---|---|---|---|')
for f in FX:
    A = json.load(open('m2/matched-off-on.json'))[f]
    B = json.load(open('m2/matched-off-cap.json'))[f]
    for arm, r in (('shipped', A['off']), ('lane', A['on']), ('lane+cap', B['on'])):
        print(f"| {f} | {arm} | {r['lost_frac']:.4f} | {r['unsewn_mm2']} | {r['wrong_colour_mm2']} | {r['overshoot_mm2']} | {r['letters_overshoot_mm2']} | {r['letters_unsewn_mm2']} | {r['spill_gt_0.5mm_mm2']} |")
print()
print('## becker with coverage_edges, matched, MARINE row (y > 12 mm) and whole design, mm2')
print('| arm | lost_frac | unsewn | overshoot | MARINE unsewn | MARINE overshoot | MARINE bare (unfiltered) |')
print('|---|---|---|---|---|---|---|')
rows = [('shipped', 'off-on', 'off'), ('lane', 'off-on', 'on'), ('lane+cap', 'off-cap', 'on'),
        ('coverage_edges', 'off-covoff', 'on'), ('coverage_edges + lane', 'off-cov', 'on'),
        ('coverage_edges + lane+cap', 'off-covcap', 'on')]
for name, fn, k in rows:
    r = json.load(open(f'm2/matched-{fn}.json'))['becker'][k]
    print(f"| {name} | {r['lost_frac']:.4f} | {r['unsewn_mm2']} | {r['overshoot_mm2']} | {r['band_unsewn_mm2']} | {r['band_overshoot_mm2']} | {r['band_bare_mm2']} |")
print()
for arm in ('covoff', 'cov', 'covcap'):
    r = get(f'm5/becker-{arm}.json')
    print(arm, 'grid', r['lost_frac'], r['unsewn_frac'], r['overshoot_frac'], 'stitches', r['stitches'], 'trims', r['trims'])
