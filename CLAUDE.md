# Papcastle Village Diary — project context

A small static site that scrapes the latest *Villager* newsletter from the
Papcastle Parish Council site, parses the diary dates, and shows them as a
calendar. Built in a chat session; this file hands off the context.

## Architecture (and why)

```
weekly cron / manual run
  -> scraper finds the newsletter with the highest issue number
  -> downloads that PDF, extracts diary dates
  -> writes site/data/events.json
  -> opens a PR  (human reviews the parsed dates)
  -> merge -> GitHub Pages redeploys the site
```

Deliberate choices, please preserve them:
- **Nothing parses at page-load.** The source changes ~4×/year, so the site
  only reads a reviewed `events.json`. If the council site breaks, the calendar
  keeps serving the last approved dates.
- **Networked code is isolated in `scraper/fetch.py`.** The parsing logic
  (`newsletters.py`, `diary.py`) is pure and unit-testable and must stay that
  way — don't add HTTP calls into them.
- **Every parse goes through a review PR.** Events default to
  `needs_review: true`. The parser is best-effort by design, not a source of
  truth; the human PR review is the safety net.

## Layout

| Path | What it is |
|------|------------|
| `scraper/newsletters.py` | Find latest issue by number. Tested. |
| `scraper/diary.py` | PDF text → structured events. Tested. |
| `scraper/fetch.py` | The ONLY networked module: page + PDF fetch. |
| `scraper/main.py` | Orchestrates a run, writes `events.json`. |
| `scraper/run_demo.py` | Runs parser against the bundled fixture. |
| `scraper/fixture_issue77.txt` | Real Issue 77 diary text, for offline tests. |
| `site/index.html` | The calendar. Vanilla JS, no build step. |
| `site/data/events.json` | The reviewed, published dates. |
| `.github/workflows/update.yml` | Weekly + manual scrape that opens a PR. |
| `.github/workflows/deploy.yml` | Publishes `site/` to GitHub Pages on push to main. |

## Commands

```bash
pip install -r scraper/requirements.txt
cd scraper
python main.py                     # LIVE: hits the parish council site
python main.py fixture_issue77.txt # OFFLINE: parse the bundled sample
python run_demo.py                 # show parser output + latest-issue detection
```

## State — what's done vs. not

- LIVE as of 2026-08-05: https://mjwhitehurst.github.io/papcastle-village-diary/
  (repo `mjwhitehurst/papcastle-village-diary`, Pages source = GitHub Actions).
- DONE & verified end-to-end against the live site on 2026-08-05:
  `newsletter_links` found Issue 77 in the real markup unchanged, and the
  full run wrote all 7 events with correct dates, times and titles.
- What the first live run broke, and how it was fixed (worth knowing, because
  the same trap applies to any future format change):
  - **The old fixture was a lie.** It had been reflowed by hand to one field
    per line. Real `pdfplumber` output is a two-column table with the anchor
    and title on ONE line (`Every Monday   Keep Fit in the Village Hall`).
    `fixture_issue77.txt` is now genuine extractor output — don't tidy it up.
  - **Parsing the whole newsletter invents events.** A Villager is a magazine
    and articles open with dates, which produced six phantom entries.
    `_diary_section` in `diary.py` now scopes to the "Diary Dates" table.

## Known rough edges (all handled by the review PR for now)

- The end of the diary table is found heuristically (`_CONT_CUE`): real table
  rows carry a time, price, phone or email and the prose after them doesn't.
  If a future issue ends the table with a plain-text row, its trailing text
  lands in the last event's `raw`.
- Status notes ("suspended until autumn", "no classes on…") are surfaced from
  raw text but not fully structured. `site/index.html` greps `raw` for them.
- Year roll-over: a Winter issue listing January events uses the issue's
  printed year; may need adjusting in review.
- `refine_with_llm` in `diary.py` is a stub — the intended home for an LLM
  extraction pass that would clean up the above automatically.

## Remaining tasks

1. Optional custom domain: apex A records to 185.199.108.153 / .109.153 /
   .110.153 / .111.153, `www` CNAME to `<user>.github.io`, then set the domain
   in Settings → Pages. `.app` TLDs are HTTPS-only (Pages issues the cert).
2. Optional: implement `refine_with_llm`.
3. No test suite exists despite `newsletters.py`/`diary.py` being called
   "tested" below — `run_demo.py` prints, it doesn't assert. Its known-good
   output would make a decent pytest baseline.

## Conventions

- Keep `fetch.py` the only module that touches the network.
- Don't lower the review gate — parsed data is reviewed before it publishes.
- `main.py` leaves `events.json` untouched when a run would only change
  `generated_at`, so the weekly CI run opens a PR only when the dates actually
  moved. Keep any new provenance fields out of the comparison in `_comparable`
  if they change every run, or the no-op PRs come back.
- No build step for the site; keep `index.html` self-contained and its asset
  paths relative (it may be served from a repo subpath on Pages).
- **Never use `toISOString()` on a calendar date in `index.html`.** The grid
  builds local-midnight `Date`s; `toISOString()` converts them to UTC, which
  through BST lands on the previous day and shifts every event a day late.
  `iso()` formats from local components — keep it that way.
