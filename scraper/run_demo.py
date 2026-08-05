import json
from newsletters import latest_newsletter, issue_number
from diary import parse_events, to_dicts

# --- Part 1: latest-newsletter detection, against the real link texts ---
links = [
    ("Villager 76 - Winter 2025/26", ".../Issue 76.pdf"),
    ("The Villager Issue 77 Spring 2026", ".../Issue 77.pdf"),
    ("Villager 74 - Spring 2025", ".../Issue 74.pdf"),
    ("Villager 75 - Summer 2025", ".../Issue 75.pdf"),
    ("Spring 2024- Issue 71", ".../Issue-71.pdf"),
    ("Summer 2024 - Issue 72", ".../Issue-72.pdf"),
]
print("issue-number extraction:")
for t, _ in links:
    print(f"   {issue_number(t):>3}  <- {t!r}")
latest = latest_newsletter(links)
print(f"\nLATEST -> issue {latest.issue}: {latest.title}\n")

# --- Part 2: diary parsing, against the real Issue 77 text ---
text = open("fixture_issue77.txt").read()
events = parse_events(text, issue_year=2026)
print(f"parsed {len(events)} events:\n")
print(json.dumps(to_dicts(events), indent=2, ensure_ascii=False))
