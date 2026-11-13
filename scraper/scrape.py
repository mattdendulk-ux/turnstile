"""
Turnstile — daily D1 men's basketball attendance scraper.

Pulls final games from ESPN's public scoreboard feed and merges them into
data/games.json. Safe to run repeatedly: games are keyed by ESPN event id.

Usage:
    python scraper/scrape.py                 # yesterday + today (Eastern)
    python scraper/scrape.py 20261101 20261111   # backfill a date range
"""
import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "games.json"
BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
HEADERS = {"User-Agent": "Turnstile attendance tracker (personal project)"}
PAUSE = 1.5  # seconds between requests — be polite

# ESPN conference group ids -> short names (Division I = 50)
CONFERENCES = {
    "1": "America East", "2": "ACC", "3": "A-10", "4": "Big East", "5": "Big Sky",
    "6": "Big South", "7": "Big Ten", "8": "Big 12", "9": "Big West", "10": "CAA",
    "11": "CUSA", "12": "Ivy", "13": "MAAC", "14": "MAC", "16": "MEAC", "18": "MVC",
    "19": "NEC", "20": "OVC", "21": "Pac-12", "22": "Patriot", "23": "SEC",
    "24": "SoCon", "25": "Southland", "26": "SWAC", "27": "Sun Belt", "29": "WCC",
    "30": "UAC", "44": "Mountain West", "45": "Horizon", "46": "ASUN", "49": "Summit",
    "62": "American",
}


def fetch_day(day: str) -> list[dict]:
    """Return normalized final games for one scoreboard day (YYYYMMDD)."""
    r = requests.get(
        f"{BASE}/scoreboard",
        params={"dates": day, "groups": "50", "limit": "500"},
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    games = []
    for ev in r.json().get("events", []):
        if ev["status"]["type"]["name"] != "STATUS_FINAL":
            continue
        c = ev["competitions"][0]
        home = next(t for t in c["competitors"] if t["homeAway"] == "home")
        away = next(t for t in c["competitors"] if t["homeAway"] == "away")
        venue = c.get("venue") or {}
        addr = venue.get("address") or {}
        notes = c.get("notes") or []

        def team(t):
            conf_id = t["team"].get("conferenceId") or ""
            return {
                "id": t["team"]["id"],
                "name": t["team"].get("location") or t["team"]["displayName"],
                "conf": CONFERENCES.get(conf_id, ""),  # blank = non-D1 opponent
                "score": int(t.get("score") or 0),
            }

        games.append({
            "id": ev["id"],
            "date": f"{day[:4]}-{day[4:6]}-{day[6:]}",
            "home": team(home),
            "away": team(away),
            "att": int(c.get("attendance") or 0),  # 0 = not reported
            "neutral": bool(c.get("neutralSite")),
            "confGame": bool(c.get("conferenceCompetition")),
            "venue": venue.get("fullName", ""),
            "city": ", ".join(x for x in (addr.get("city"), addr.get("state")) if x),
            "event": notes[0].get("headline", "") if notes else "",
        })
    return games


def daterange(start: str, end: str):
    d = datetime.strptime(start, "%Y%m%d").date()
    e = datetime.strptime(end, "%Y%m%d").date()
    while d <= e:
        yield d.strftime("%Y%m%d")
        d += timedelta(days=1)


def main(argv):
    if len(argv) == 3:
        days = list(daterange(argv[1], argv[2]))
    else:
        today = datetime.now(ZoneInfo("America/New_York")).date()
        days = [(today - timedelta(days=1)).strftime("%Y%m%d"), today.strftime("%Y%m%d")]

    store = {"updated": "", "games": []}
    if DATA.exists():
        store = json.loads(DATA.read_text())
    scanned = {f"{d[:4]}-{d[4:6]}-{d[6:]}" for d in days}
    # Starter data uses placeholder ids; real ESPN pulls for the same day replace it.
    by_id = {g["id"]: g for g in store["games"]
             if not (g["id"].startswith("seed") and g["date"] in scanned)}

    added = 0
    for day in days:
        try:
            for g in fetch_day(day):
                if g["id"] not in by_id:
                    added += 1
                by_id[g["id"]] = g  # newer pull wins (attendance sometimes posts late)
        except requests.RequestException as e:
            print(f"[warn] {day}: {e}", file=sys.stderr)
        time.sleep(PAUSE)

    store["games"] = sorted(by_id.values(), key=lambda g: (g["date"], g["id"]))
    store["updated"] = datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="minutes")
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(store, separators=(",", ":")))
    print(f"{len(days)} day(s) scanned, {added} new game(s), {len(by_id)} total")


if __name__ == "__main__":
    main(sys.argv)
