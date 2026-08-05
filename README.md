# Papcastle Village Diary

A small static site that reads the latest **Villager** newsletter from the
[Papcastle Parish Council site](https://www.papcastleparishcouncil.gov.uk/other-documents/),
pulls out the diary dates, and shows them as a calendar.

## How it works

```
weekly cron / manual run
   -> scraper finds the newsletter with the highest issue number
   -> downloads that PDF, extracts the diary dates
   -> writes site/data/events.json
   -> opens a pull request
   -> editor reviews the dates and merges
   -> static site rebuilds with the new dates
```

Nothing runs live when a visitor loads the page — the site just reads the
reviewed `events.json`. If the council site is down or changes, the calendar
keeps serving the last approved dates.

## Layout

| Path | What it is |
|------|------------|
| `scraper/newsletters.py` | Find the latest issue by number (tested). |
| `scraper/diary.py` | Turn the messy PDF text into structured events (tested). |
| `scraper/fetch.py` | The only networked part: page + PDF fetching. |
| `scraper/main.py` | Orchestrates a run, writes `events.json`. |
| `site/index.html` | The calendar (vanilla JS, no build step). |
| `site/data/events.json` | The reviewed, published dates. |
| `.github/workflows/update.yml` | Weekly + manual scrape that opens a PR. |

## Running it yourself

```bash
pip install -r scraper/requirements.txt
cd scraper
python main.py                    # live: hits the parish council site
python main.py fixture_issue77.txt  # offline: parse the bundled sample
```

Then open `site/index.html` (any static host works — GitHub Pages, Netlify,
Cloudflare Pages).

## Known rough edges

The parser is best-effort by design, which is why every run goes through a
review PR. Things to eyeball:

- **Titles** with decoration, e.g. `SAVE THE DATE - Village BBQ` parses the
  first clause. Fix in the PR or extend `_find_title` in `diary.py`.
- **Status notes** like "suspended until autumn" or "no classes on…" are
  surfaced from the raw text but not fully structured.
- **Year roll-over**: a Winter issue listing January events uses the issue's
  printed year; adjust in review if an event belongs to the following year.

The `refine_with_llm` hook in `diary.py` is where an LLM extraction pass would
slot in to clean these up automatically.
