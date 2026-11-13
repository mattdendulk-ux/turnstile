"""
Match ESPN venue names to arena capacities and write data/arenas.json.

Capacity source: Wikipedia, "List of NCAA Division I basketball arenas"
(saved in scraper/sources/wiki_arenas.txt). Re-run after the season's data grows:
    python scraper/build_arenas.py
Venues it can't match are printed; add them to MANUAL below.
"""
import json, re, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STOP = {"the", "at", "of", "and", "arena", "center", "centre", "coliseum", "gym", "gymnasium",
        "pavilion", "fieldhouse", "field", "house", "events", "event", "sports", "complex",
        "athletic", "athletics", "hall", "court", "memorial", "convocation", "university", "home",
        "screaming", "eagles", "tn", "in", "va", "oh", "mi", "de", "dallas", "abilene", "navy"}
ALIAS = {"miami fl": "miami", "virginia commonwealth": "vcu", "hawaii": "hawai'i", "iu indy": "iu indianapolis",
         "tennessee-martin": "ut martin", "usc upstate": "south carolina upstate", "louisiana–monroe": "ul monroe",
         "gardner–webb": "gardner-webb", "loyola maryland": "loyola maryland", "miami ohio": "miami (oh)",
         "penn": "pennsylvania", "liu": "long island university", "appalachian state": "app state",
         "seattle": "seattle u", "san jose state": "san josé state", "texas a&m-corpus christi": "texas a&m-corpus christi",
         "utrgv": "ut rio grande valley", "new orleans": "lsu new orleans", "fiu": "florida international",
         "albany": "ualbany", "southeastern louisiana": "se louisiana", "north carolina": "north carolina",
         "nc state": "nc state", "umass lowell": "umass lowell"}
# ESPN venue name -> capacity, for venues the matcher can't link on its own
MANUAL = {
    "McDonough Arena": 2500,                       # Georgetown's on-campus gym (Wikipedia: McDonough Gymnasium)
    "M&T Bank Center at Gampel Pavilion": 10167,   # UConn; sponsor name collides with Quinnipiac's M&T Bank Arena
    "ICCU Arena": 4200,                            # Idaho (Moscow); name collides with Idaho State's ICCU Dome
}
# Venues whose home-team match would point at the wrong building; left blank until confirmed
SKIP = {"Skip Chappelle Court in Memorial Gymnasium", "Bodford Arena", "Lawler Arena", "Canastra Hammer Arena",
        "Hilliard Center", "Hornet Pavilion", "Sanford Pentagon"}

def norm(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9& ]", " ", s)

def toks(s):
    return {t for t in norm(s).split() if t not in STOP and len(t) > 1}

def team_key(s):
    s = re.sub(r"\b(men|women)\b", "", s.lower()).replace("(", "").replace(")", "").strip(" ,")
    return ALIAS.get(s, s)

wiki = []
for line in (ROOT / "scraper/sources/wiki_arenas.txt").read_text().splitlines():
    name, city, state, teams, cap = line.split("|")
    wiki.append({"name": name, "city": norm(city).strip(), "state": state, "cap": int(cap.replace(",", "")),
                 "teams": [team_key(t) for t in teams.split(",")]})

games = json.loads((ROOT / "data/games.json").read_text())["games"]
venues = {}
for g in games:
    v = venues.setdefault(g["venue"], {"city": g["city"], "homes": set()})
    if not g["neutral"]:
        v["homes"].add(g["home"]["name"].lower())

out, unmatched = {}, []
for vname, info in sorted(venues.items()):
    if vname in SKIP:
        unmatched.append((vname, info["city"], "skipped")); continue
    if vname in MANUAL:
        out[vname] = {"cap": MANUAL[vname], "src": "manual"}; continue
    state = info["city"].rsplit(", ", 1)[-1] if ", " in info["city"] else ""
    vt = toks(vname)
    best, score = None, 0
    for w in wiki:
        if state and w["state"] != state:
            continue
        wt = toks(w["name"])
        s = len(vt & wt) / max(1, len(vt | wt))
        if any(t in w["teams"] for t in info["homes"]):
            s += 0.35  # home team plays here
        if s > score:
            best, score = w, s
    if best and score >= 0.35:  # strong name match, or the home team plays there
        out[vname] = {"cap": best["cap"], "match": best["name"]}
    else:
        unmatched.append((vname, info["city"], sorted(info["homes"]), best["name"] if best else None, round(score, 2)))

(ROOT / "data/arenas.json").write_text(json.dumps({k: v["cap"] for k, v in out.items()}, indent=0, ensure_ascii=False))
print(f"matched {len(out)} of {len(venues)} venues")
for u in unmatched:
    print("UNMATCHED", u)
