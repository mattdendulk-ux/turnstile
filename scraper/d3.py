"""
Turnstile — D3 men's basketball attendance for a short list of tracked schools.

Kept completely separate from the D1 data: results go to data/d3.json, which the
D1 rankings, averages and charts never read.

Each school's athletics site (SIDEARM) lists every game on its schedule page,
tagged home / away / neutral with the result; each game's box score has the
attendance, date and site. Box scores already saved are not fetched again.

Usage:  python scraper/d3.py
Add a school: append (name, athletics site) to SCHOOLS.
"""
import html
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "d3.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Turnstile attendance tracker)"}
PAUSE = 1.5  # seconds between requests

SCHOOLS = [
    ("Hope", "https://athletics.hope.edu"),
    ("Trine", "https://trinethunder.com"),
    ("Illinois Wesleyan", "https://www.iwusports.com"),
    ("Calvin", "https://calvinknights.com"),
    ("Mount Union", "https://athletics.mountunion.edu"),
]


def season_now():
    now = datetime.now(ZoneInfo("America/New_York"))
    y = now.year if now.month >= 7 else now.year - 1
    return f"{y}-{(y + 1) % 100:02d}"


def text(fragment):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def parse_schedule(page, season):
    """Completed games on a SIDEARM schedule page."""
    starts = [m.start() for m in re.finditer(r'<li[^>]*class="[^"]*sidearm-schedule-game [^"]*"', page)]
    games = []
    for i, start in enumerate(starts):
        block = page[start: starts[i + 1] if i + 1 < len(starts) else start + 20000]
        cls = re.search(r'class="([^"]*)"', block).group(1)
        box = re.search(rf'href="([^"]*/stats/{season}/[^"]*/boxscore/\d+)"', block)
        res = re.search(r"\b([WLT]),\s*(\d+)-(\d+)", text(block))
        if not box or not res:
            continue  # not played yet, or no box score posted
        opp = re.search(r'sidearm-schedule-game-opponent-name[^>]*>(.*?)</(?:span|div)>', block, re.S)
        where = "home" if "home-game" in cls else "away" if "away-game" in cls else "neutral"
        hi, lo = sorted((int(res.group(2)), int(res.group(3))), reverse=True)
        games.append({
            "id": re.search(r"/boxscore/(\d+)", box.group(1)).group(1),
            "box": box.group(1),
            # rank prefixes ("#13", "No. 12", "RV") are stripped; the box score title usually replaces this anyway
            "opp": re.sub(r"^(#\d+|No\. ?\d+|RV)\s*", "", text(opp.group(1))) if opp else "",
            "where": where,
            "result": res.group(1),
            "us": hi if res.group(1) == "W" else lo,
            "them": lo if res.group(1) == "W" else hi,
        })
    return games


def parse_box(page):
    """Date, attendance and site from a SIDEARM box score."""
    info = {text(k): text(v) for k, v in re.findall(r"<dt>(.*?)</dt>\s*<dd>(.*?)</dd>", page, re.S)}
    att = re.sub(r"\D", "", info.get("Attendance", ""))
    d = info.get("Date", "")
    try:
        iso = datetime.strptime(d, "%m/%d/%y").strftime("%Y-%m-%d")
    except ValueError:
        iso = ""
    out = {"date": iso, "att": int(att) if att else 0, "site": info.get("Site", "")}
    title = re.search(r"<title>(.*?)</title>", page, re.S)
    opp = re.search(r"Basketball (?:vs\.?|at) (.*?) on \d", text(title.group(1))) if title else None
    if opp:
        out["opp"] = opp.group(1)
    return out


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    time.sleep(PAUSE)
    return r.text


def main():
    season = season_now()
    store = json.loads(DATA.read_text()) if DATA.exists() else {"games": []}
    have = {(g["team"], g["id"]): g for g in store["games"]}
    added = 0
    for name, site in SCHOOLS:
        try:
            sched = parse_schedule(get(f"{site}/sports/mens-basketball/schedule/{season}"), season)
        except requests.RequestException as e:
            print(f"[warn] {name} schedule: {e}", file=sys.stderr)
            continue
        for g in sched:
            key = (name, g["id"])
            # Re-check a saved game only if it had no attendance yet (schools sometimes post it late)
            if key in have and have[key]["att"]:
                continue
            url = g.pop("box")
            try:
                box = parse_box(get(url if url.startswith("http") else site + url))
            except requests.RequestException as e:
                print(f"[warn] {name} {url}: {e}", file=sys.stderr)
                continue
            if key not in have:
                added += 1
            have[key] = {"team": name, "season": season, **g, **box}  # box score's opponent name wins
        print(f"{name}: {len(sched)} completed games on schedule")
    store = {
        "updated": datetime.now(ZoneInfo("America/New_York")).isoformat(timespec="minutes"),
        "schools": [n for n, _ in SCHOOLS],
        "games": sorted(have.values(), key=lambda g: (g["date"], g["team"])),
    }
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(store, indent=0, ensure_ascii=False))
    print(f"{added} new D3 game(s), {len(have)} total")


if __name__ == "__main__":
    main()
