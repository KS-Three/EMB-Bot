import json
import sys
from collections import defaultdict

rows = json.load(open(sys.argv[1]))
ARMS = ["M", "A0", "A", "B1", "B2", "B3"]
by = defaultdict(dict)
for r in rows:
    by[(r["fixture"], r["lane"], r["rung"])][r["arm"]] = r


def line(key, f, fmt):
    return " ".join((fmt % f(by[key][a])) if a in by[key] else "     -" for a in ARMS)


for title, f, fmt in [
    ("precision: median mm, arm edge -> truth edge (lower better)", lambda r: r["p_med"], "%6.3f"),
    ("precision: share of arm edge within 0.10 mm of truth (higher better)", lambda r: 100 * r["p_in01"], "%6.1f"),
    ("recall: median mm, truth edge -> arm edge (lower better)", lambda r: r["r_med"], "%6.3f"),
    ("recall: 90th pct mm (lower better)", lambda r: r["r_p90"], "%6.3f"),
    ("turning, deg per mm of boundary (lower = smoother)", lambda r: r["turn"], "%6.1f"),
    ("nodes", lambda r: r["nodes"], "%6d"),
    ("regions", lambda r: r["regions"], "%6d"),
]:
    print("\n" + title)
    print("%-26s %s" % ("", " ".join("%6s" % a for a in ARMS)))
    for key in sorted(by):
        if "p_med" not in by[key]["A"] and "p_" in title[:2] + "_":
            pass
        try:
            print("%-26s %s" % ("%s %s r%g" % key, line(key, f, fmt)))
        except KeyError:
            pass
