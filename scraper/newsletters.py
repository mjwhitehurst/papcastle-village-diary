"""
Find the latest newsletter on the Papcastle 'Other Documents' page.

Strategy: parse the links under the 'Newsletters' heading and pick the one
with the highest ISSUE NUMBER. We key off the link *text* (which is fairly
consistent) rather than the PDF filename (which is chaotic), and we never
trust the position on the page or the year heading -- issue 77 currently sits
*below* issue 76 in the markup, so ordering is not reliable.
"""

import re
from dataclasses import dataclass

# A year-looking number we must NOT mistake for an issue number.
_YEAR = re.compile(r"^(19|20)\d{2}$")
# Explicit "Issue 77" / "Villager 76" / "No. 45" -- the reliable signal.
_EXPLICIT = re.compile(r"(?:issue|villager|no\.?)\s*[-#]?\s*(\d{1,3})", re.I)
_ANY_INT = re.compile(r"\d{1,4}")


@dataclass
class Newsletter:
    issue: int
    title: str
    url: str


def issue_number(link_text: str) -> int | None:
    """Extract the issue number from a newsletter link's text.

    'The Villager Issue 77 Spring 2026' -> 77
    'Villager 76 - Winter 2025/26'      -> 76
    'Spring 2024- Issue 71'             -> 71   (NOT 2024)
    """
    m = _EXPLICIT.search(link_text)
    if m:
        return int(m.group(1))
    # Fallback: largest integer that isn't a year.
    candidates = [int(n) for n in _ANY_INT.findall(link_text) if not _YEAR.match(n)]
    return max(candidates) if candidates else None


def latest_newsletter(links: list[tuple[str, str]]) -> Newsletter | None:
    """links: list of (link_text, url) scraped from the Newsletters section."""
    found: list[Newsletter] = []
    for text, url in links:
        n = issue_number(text)
        if n is not None:
            found.append(Newsletter(issue=n, title=text.strip(), url=url))
    return max(found, key=lambda n: n.issue) if found else None
