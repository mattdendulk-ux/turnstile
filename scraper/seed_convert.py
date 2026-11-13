"""One-time: convert the compact Nov 1-11 browser export into data/games.json."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from scrape import CONFERENCES

raw = Path(sys.argv[1]).read_text()
sec = {}
cur = None
for line in raw.splitlines():
    if line.startswith("##"):
        cur = line[2:]; continue
    sec[cur] = line
teams = {}
for t in sec["TEAMS"].split(";"):
    tid, name, conf = t.split(",")
    teams[tid] = (name, CONFERENCES.get(conf, ""))
venues = [v.split("~") for v in sec["VENUES"].split(";")]
notes = sec["NOTES"].split(";")
rows = [r for r in sec["GAMES"].split(";") if r]
counts = [2,182,29,26,65,72,61,36,50,69,67]  # games per scoreboard day, Nov 1..11
assert sum(counts) == len(rows), (sum(counts), len(rows))
days = [d for i, n in enumerate(counts) for d in [f"2026-11-{i+1:02d}"] * n]
games = []
for i, (r, day) in enumerate(zip(rows, days)):
    _, h, hs, a, as_, att, flags, vi, ni = r.split(",")
    vname, city = venues[int(vi)]
    city = city.rsplit(" ", 1); city = ", ".join(city) if len(city) == 2 else city[0]
    def tm(tid, s):
        n, c = teams[tid]; return {"id": tid, "name": n, "conf": c, "score": int(s)}
    games.append({"id": f"seed{i}", "date": day, "home": tm(h, hs), "away": tm(a, as_),
        "att": int(att), "neutral": flags[0] == "1", "confGame": flags[1] == "1",
        "venue": vname, "city": city, "event": notes[int(ni)] if ni else ""})
out = Path(__file__).resolve().parent.parent / "data" / "games.json"
out.write_text(json.dumps({"updated": "2026-11-12T06:00-05:00", "games": games}, separators=(",", ":")))
print(len(games), "games;", sum(1 for g in games if g["att"] > 0), "with attendance")
