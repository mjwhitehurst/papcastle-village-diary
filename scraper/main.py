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


def _comparable(data: dict) -> dict:
    """The parts of events.json that mean something, i.e. everything but the
    run timestamp."""
    trimmed = json.loads(json.dumps(data))
    trimmed.get("source", {}).pop("generated_at", None)
    return trimmed


def unchanged(data: dict, path: Path) -> bool:
    """True if writing `data` would only bump generated_at.

    Without this the weekly CI run rewrites events.json every Monday purely
    because the timestamp moved, and opens a review PR that has nothing in it
    for a human to review. The Villager comes out ~4x/year; the other ~48 runs
    should be silent.
    """
    if not path.exists():
        return False
    try:
        old = json.loads(path.read_text())
    except json.JSONDecodeError:
        return False                      # unreadable: rewrite it
    return _comparable(old) == _comparable(data)


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

    if unchanged(data, OUT):
        print(f"No change: {len(data['events'])} events, same as {OUT.name} "
              f"already on disk. Leaving it alone so CI opens no PR.")
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(data['events'])} events -> {OUT}")


if __name__ == "__main__":
    main()
