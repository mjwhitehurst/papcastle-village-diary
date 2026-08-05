"""
Entry point run by CI: find the latest Villager, parse its diary dates, and
write site/data/events.json. On a normal run this opens a PR (see the workflow),
so a human approves the parsed dates before they reach the calendar.

    python main.py            # live: hits the parish council site
    python main.py FIXTURE    # offline: parse a local text file instead
"""

import sys
import json
import datetime as dt
from pathlib import Path

from newsletters import latest_newsletter
from diary import parse_events, to_dicts
from fetch import fetch_html, newsletter_links, issue_year, pdf_text

OUT = Path(__file__).resolve().parents[1] / "site" / "data" / "events.json"


def build(text: str, issue_title: str, source_url: str) -> dict:
    year = issue_year(issue_title, fallback=dt.date.today().year)
    events = parse_events(text, issue_year=year)
    return {
        "source": {
            "issue": issue_title,
            "url": source_url,
            "issue_year": year,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        },
        "events": to_dicts(events),
    }


def main() -> None:
    if len(sys.argv) > 1:  # offline mode: main.py path/to/fixture.txt
        text = Path(sys.argv[1]).read_text()
        data = build(text, "The Villager Issue 77 Spring 2026 (fixture)", "(local fixture)")
    else:
        links = newsletter_links(fetch_html())
        latest = latest_newsletter(links)
        if latest is None:
            raise SystemExit("No newsletters found - has the page structure changed?")
        print(f"Latest: issue {latest.issue} - {latest.title}\n  {latest.url}")
        data = build(pdf_text(latest.url), latest.title, latest.url)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(data['events'])} events -> {OUT}")


if __name__ == "__main__":
    main()
