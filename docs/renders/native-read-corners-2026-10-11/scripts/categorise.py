import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[4] / "digitizer"))
import pickle
import sys
from collections import Counter
from pathlib import Path

d = pickle.load(open(Path(sys.argv[1]) / f"diag_{sys.argv[2]}.pkl", "rb"))
c = Counter()
for rv in d["revs"]:
    r = rv["rec"]
    at = r["at"]
    if at["d"] > 0.01:
        k = "at: not a read point (refine insert)"
    elif at["fitted"]:
        k = "at: fitted corner"
    elif at["corner"] and not at["acc"]:
        k = "at: unread corner kept at pixel centre"
    elif at["corner"]:
        k = "at: profile-placed corner"
    elif not at["acc"]:
        k = "at: rejected vertex"
    else:
        nb = [r["prev"], r["nxt"]]
        if any(x["fitted"] for x in nb):
            k = "at: plain, neighbour fitted corner"
        elif any(x["corner"] and not x["acc"] for x in nb):
            k = "at: plain, neighbour unread corner"
        elif any(x["corner"] for x in nb):
            k = "at: plain, neighbour profile corner"
        else:
            k = "at: plain, plain neighbours"
    c[k] += 1
    rv["cat"] = k
for k, v in c.most_common():
    print(f"{v:4d}  {k}")
anyfit = sum(any(x["fitted"] for x in rv["rec"].values()) for rv in d["revs"])
anycor = sum(any(x["corner"] for x in rv["rec"].values()) for rv in d["revs"])
print("any of 3 fitted:", anyfit, " any of 3 corner-flagged:", anycor, " of", len(d["revs"]))
pickle.dump(d, open(Path(sys.argv[1]) / f"diag_{sys.argv[2]}.pkl", "wb"))
