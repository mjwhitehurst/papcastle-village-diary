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

- DONE & verified against real Issue 77 data: diary-date parsing and
  latest-issue detection (all 7 events, correct dates).
- NOT yet run against the live site: the HTML link-scraping in `fetch.py`
  (`newsletter_links`). The sandbox it was built in couldn't reach the council
  domain. **The first `python main.py` run is the real test of that function.**
  It scopes to the "Newsletters" heading and keeps only links that parse to an
  issue number as a backstop — but if the page's heading tags differ from the
  assumption, that's the thing to fix.

## Known rough edges (all handled by the review PR for now)

- Titles with decoration, e.g. `SAVE THE DATE - Village BBQ` parses to the
  first clause. Extend `_find_title` in `diary.py` to fix properly.
- Status notes ("suspended until autumn", "no classes on…") are surfaced from
  raw text but not fully structured.
- Year roll-over: a Winter issue listing January events uses the issue's
  printed year; may need adjusting in review.
- `refine_with_llm` in `diary.py` is a stub — the intended home for an LLM
  extraction pass that would clean up the above automatically.

## Remaining tasks

1. Run `python main.py` live once; fix `fetch.py`'s scraping if the real page
   markup differs from the assumption.
2. Hosting on GitHub Pages: Settings → Pages → Source = "GitHub Actions"; and
   Settings → Actions → General → enable "Allow GitHub Actions to create and
   approve pull requests" (so `update.yml` can open its PR).
3. Optional custom domain: apex A records to 185.199.108.153 / .109.153 /
   .110.153 / .111.153, `www` CNAME to `<user>.github.io`, then set the domain
   in Settings → Pages. `.app` TLDs are HTTPS-only (Pages issues the cert).
4. Optional: implement `refine_with_llm`.

## Conventions

- Keep `fetch.py` the only module that touches the network.
- Don't lower the review gate — parsed data is reviewed before it publishes.
- No build step for the site; keep `index.html` self-contained and its asset
  paths relative (it may be served from a repo subpath on Pages).
