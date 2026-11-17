# Turnstile

A college basketball attendance tracker. Every morning a scraper pulls the previous day's NCAA Division I men's box scores from ESPN's public scoreboard feed, saves each game's reported attendance to `data/games.json`, and the site rebuilds its rankings from that file.

```
turnstile/
├── index.html                  the whole website (no build step)
├── data/games.json             every game: teams, score, venue, attendance
├── data/arenas.json            venue name -> seating capacity
├── scraper/scrape.py           daily scraper
├── scraper/build_arenas.py     matches venues to capacities (runs after the scraper)
├── scraper/sources/            arena capacity list from Wikipedia
├── scraper/seed_convert.py     one-time loader for the Nov 1–11 starter data
└── .github/workflows/daily.yml runs the scraper every morning and commits new data
```

## Put it online (about 10 minutes, free)

1. Create a new public repository on GitHub (for example `turnstile`) and upload everything in this folder, keeping the folder structure. The `.github` folder is hidden on Mac; press Cmd+Shift+. in Finder to see it.
2. In the repo, go to **Settings → Pages**. Under "Build and deployment," pick **Deploy from a branch**, branch `main`, folder `/ (root)`. Save.
3. Go to **Settings → Actions → General → Workflow permissions** and choose **Read and write permissions**. This lets the daily job commit new data.
4. Go to the **Actions** tab, open **Daily attendance update**, and click **Run workflow** once to confirm it works.

Your site will be live at `https://<your-username>.github.io/turnstile/`. You can point a custom domain at it from the same Pages settings screen.

## Replace the starter data with full ESPN records

The included Nov 1–11 data was pulled through a browser, so its games carry placeholder ids. Run one backfill so every game has ESPN's real id: in the **Actions** tab, open **Daily attendance update**, click **Run workflow**, enter a start date (`20261101`) and an end date (yesterday, e.g. `20261112`), and run it. The scraper replaces placeholder games for any date it re-scans.

To run it on your own computer instead: `pip install requests`, then `python scraper/scrape.py 20261101 20261112`.

## Daily schedule

The workflow runs at 13:17 UTC (8:17am Eastern, 5:17am Pacific) and scrapes yesterday and today. Re-scraping yesterday picks up attendance figures that schools post late. Change the time in `.github/workflows/daily.yml`.

## Arena capacity

Capacities come from Wikipedia's "List of NCAA Division I basketball arenas," saved in `scraper/sources/wiki_arenas.txt`. `build_arenas.py` matches each venue in the box scores to that list by name, city and home team, then writes `data/arenas.json`. It prints any venue it can't match. Most are neutral-site NBA and NHL arenas; add a capacity for any of them in the `MANUAL` list at the top of the script.

A few venues are deliberately left blank because the match would point at the wrong building (renamed or secondary gyms). They are listed in `SKIP`. Add a confirmed capacity to `MANUAL` to fill one in.

## Editing the site

- **About blurb and email:** edit the `<aside class="hire">` block near the bottom of `index.html`.
- **Baseline:** `BASELINE_2425` is the NCAA's 2024-25 D1 home average (4,373), from the NCAA's men's basketball attendance records PDF. Update it when the NCAA publishes 2025-26 totals.

## Infographics

The header (a season snapshot of the four headline stats plus the most recent or selected day) and every ranked list (Team rankings, Conferences, By day and the four Biggest & smallest lists) has a **Save as image** button. It draws a 1080 × 1350 PNG, sized for Instagram and LinkedIn, of the list as currently sorted and filtered: top 10 for teams and games, top 14 days, and all conferences in two columns. The image is drawn in the browser, so it works on GitHub Pages or Netlify with no extra setup.

## How the numbers are counted

- Team and conference averages use home games at the team's own venue with a reported figure. Neutral-site games count in the game list and the largest-crowds table only.
- % of capacity is attendance divided by the arena's listed capacity. Team and conference % of capacity is total home attendance divided by total seats available across those games. Venues with no confirmed capacity are left out.
- A game with no attendance in the box score shows as "Not reported" and is excluded from every average.
- Opponents outside Division I appear in the game list with no conference.

## D2 and D3 watch

`scraper/small_college.py` tracks a short list of Division II schools (Fort Hays State, Northern State, Pittsburg State, Minnesota State, Drury, Black Hills State, Missouri Western) and Division III schools (Hope, Trine, Illinois Wesleyan, Calvin, Mount Union) from each school's own athletics site: the schedule page gives home/away and the result, and each box score gives the attendance. It writes `data/d2.json` and `data/d3.json`, separate files the D1 rankings, averages and charts never read. It runs in the daily job after the D1 scrape; if a school's site is down, the D1 update still goes through. To track another school that uses a SIDEARM athletics site, add it to its division in `DIVISIONS` at the top of the script.

## Adding D2, D3 and NAIA later

ESPN's feed only covers D1 reliably. The next step is a second scraper per source (stats.ncaa.org for D2 and D3, school SIDEARM and PrestoSports box scores, and PrestoSports for NAIA) writing to the same `games.json` format with a `division` field added. The site's filters then extend to a division selector.
